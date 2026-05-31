"""
分类管理API路由

- GET    /api/categories/             获取所有分类
- POST   /api/categories/             创建分类(admin)
- PUT    /api/categories/{id}         更新分类(admin)
- DELETE /api/categories/{id}         删除分类(admin)
- POST   /api/categories/init-defaults 初始化默认分类(admin)
- POST   /api/categories/reclassify   对未分类发票重新分类(admin/operator)
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.category import Category
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    ReclassifyResponse,
)
from app.services.invoice_classifier import (
    batch_classify,
    init_default_categories,
)

logger = logging.getLogger(__name__)

router = APIRouter()

ADMIN_ONLY = ["admin"]
RECLASSIFY_ROLES = ["admin", "operator", "manager"]
READ_ROLES = ["admin", "user", "operator", "manager"]


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(READ_ROLES)),
):
    """获取所有分类列表(按id升序)"""
    return db.query(Category).order_by(Category.id.asc()).all()


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ONLY)),
):
    """创建分类(仅admin)"""
    exists = db.query(Category).filter(Category.name == payload.name).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"分类已存在: {payload.name}",
        )
    entity = Category(
        name=payload.name,
        keywords=payload.keywords,
        description=payload.description,
        color=payload.color or "#409EFF",
        is_active=True,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    logger.info(f"用户 {current_user.username} 创建分类: {entity.name}")
    return entity


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ONLY)),
):
    """更新分类(仅admin)"""
    entity = db.query(Category).filter(Category.id == category_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分类不存在: id={category_id}",
        )
    if payload.name is not None and payload.name != entity.name:
        # 名称唯一性检查
        dup = (
            db.query(Category)
            .filter(Category.name == payload.name, Category.id != category_id)
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分类名称已被使用: {payload.name}",
            )
        entity.name = payload.name
    if payload.keywords is not None:
        entity.keywords = payload.keywords
    if payload.description is not None:
        entity.description = payload.description
    if payload.color is not None:
        entity.color = payload.color
    if payload.is_active is not None:
        entity.is_active = payload.is_active
    db.commit()
    db.refresh(entity)
    return entity


@router.delete("/{category_id}", response_model=dict)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ONLY)),
):
    """删除分类(仅admin，物理删除)"""
    entity = db.query(Category).filter(Category.id == category_id).first()
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分类不存在: id={category_id}",
        )
    name = entity.name
    db.delete(entity)
    db.commit()
    logger.info(f"用户 {current_user.username} 删除分类: {name}")
    return {"success": True, "id": category_id, "name": name}


@router.post("/init-defaults", response_model=dict)
async def init_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ONLY)),
):
    """初始化默认分类(已存在则跳过)"""
    created = init_default_categories(db)
    return {"success": True, "created": created}


@router.post("/reclassify", response_model=ReclassifyResponse)
async def reclassify_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(RECLASSIFY_ROLES)),
):
    """
    对所有未分类(category为空)的发票重新分类。
    """
    result = batch_classify(db, invoice_ids=None)
    logger.info(
        f"用户 {current_user.username} 触发重新分类: {result}"
    )
    return ReclassifyResponse(**result)
