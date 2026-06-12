"""用户管理 API：CRUD + 菜单权限分配。所有接口仅 admin 角色可调用。"""
import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_role
from app.models.user import User
from app.schemas.user import (
    MenuItem,
    UserCreate,
    UserListResponse,
    UserPermissionsUpdate,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


# ============================================================
# 系统所有可分配菜单（与前端路由一一对应）
# ============================================================
SYSTEM_MENUS: List[dict] = [
    {"path": "/dashboard", "title": "仪表盘", "roles": None},
    {"path": "/invoice", "title": "发票管理", "roles": None},
    {"path": "/email-config", "title": "邮箱配置", "roles": ["admin"]},
    {"path": "/export", "title": "数据导出", "roles": None},
    {"path": "/print", "title": "打印管理", "roles": None},
    {"path": "/users", "title": "用户管理", "roles": ["admin"]},
    {"path": "/categories", "title": "分类管理", "roles": ["admin", "operator"]},
    {"path": "/reimbursement", "title": "报销单管理", "roles": None},
]


# ============================================================
# 菜单列表
# ============================================================
@router.get("/menus", response_model=List[MenuItem])
async def get_menu_list(
    current_user: User = Depends(require_role(["admin"])),
):
    """获取所有可分配的系统菜单列表（仅 admin）。"""
    return [MenuItem(**m) for m in SYSTEM_MENUS]


# ============================================================
# 用户列表（分页）
# ============================================================
@router.get("/", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """分页获取用户列表（仅 admin）。"""
    query = db.query(User).order_by(User.id.asc())
    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


# ============================================================
# 创建用户
# ============================================================
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """创建用户（仅 admin）。"""
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if user_data.email:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(status_code=400, detail="邮箱已被使用")

    menu_permissions_str = None
    if user_data.menu_permissions is not None:
        menu_permissions_str = json.dumps(user_data.menu_permissions, ensure_ascii=False)

    new_user = User(
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        email=user_data.email,
        role=user_data.role,
        is_active=True,
        menu_permissions=menu_permissions_str,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)


# ============================================================
# 用户详情
# ============================================================
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse.model_validate(user)


# ============================================================
# 更新用户
# ============================================================
@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """更新用户信息（仅 admin），支持重置密码。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user_data.username is not None and user_data.username != user.username:
        if db.query(User).filter(User.username == user_data.username, User.id != user_id).first():
            raise HTTPException(status_code=400, detail="用户名已存在")
        user.username = user_data.username

    if user_data.email is not None:
        if user_data.email == "":
            user.email = None
        else:
            if (
                db.query(User)
                .filter(User.email == user_data.email, User.id != user_id)
                .first()
            ):
                raise HTTPException(status_code=400, detail="邮箱已被使用")
            user.email = user_data.email

    if user_data.role is not None:
        # 不允许将自己降级（避免误操作锁死管理权限）
        if user.id == current_user.id and user_data.role != "admin":
            raise HTTPException(status_code=400, detail="不能修改自己的管理员角色")
        user.role = user_data.role

    if user_data.is_active is not None:
        if user.id == current_user.id and user_data.is_active is False:
            raise HTTPException(status_code=400, detail="不能禁用自己")
        user.is_active = user_data.is_active

    if user_data.password is not None and user_data.password != "":
        user.password_hash = hash_password(user_data.password)

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


# ============================================================
# 删除用户
# ============================================================
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """删除用户（仅 admin）。不能删除自己。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")
    db.delete(user)
    db.commit()
    return None


# ============================================================
# 更新用户菜单权限
# ============================================================
@router.put("/{user_id}/permissions", response_model=UserResponse)
async def update_user_permissions(
    user_id: int,
    payload: UserPermissionsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """为用户分配菜单权限（仅 admin）。"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    valid_paths = {m["path"] for m in SYSTEM_MENUS}
    cleaned = [p for p in payload.permissions if p in valid_paths]
    user.menu_permissions = json.dumps(cleaned, ensure_ascii=False)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)
