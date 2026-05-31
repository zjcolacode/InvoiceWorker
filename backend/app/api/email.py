"""
邮箱配置API路由
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.email_config import EmailConfig
from app.models.email_fetch_log import EmailFetchLog as EmailFetchLogModel
from app.models.user import User
from app.schemas.email_config import (
    EmailConfigCreate,
    EmailConfigResponse,
    EmailConfigUpdate,
    EmailFetchLog as EmailFetchLogSchema,
    EmailFetchLogPage,
    EmailFetchResult,
    EmailTestRequest,
    EmailTestResponse,
)
from app.services.email_fetcher import (
    EmailFetcherService,
    encrypt_password,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------- 邮箱配置 CRUD ----------
@router.post(
    "/configs",
    response_model=EmailConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_email_config(
    payload: EmailConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """创建邮箱配置(admin)"""
    existing = (
        db.query(EmailConfig)
        .filter(EmailConfig.email_address == payload.email_address)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"邮箱[{payload.email_address}]已配置",
        )

    new_config = EmailConfig(
        email_address=payload.email_address,
        imap_server=payload.imap_server,
        port=payload.port,
        password_encrypted=encrypt_password(payload.password),
        check_interval_minutes=payload.check_interval_minutes,
        use_ssl=payload.use_ssl,
        is_active=True,
        user_id=current_user.id,
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    logger.info(f"创建邮箱配置: {new_config.email_address} by {current_user.username}")
    return new_config


@router.get("/configs", response_model=list[EmailConfigResponse])
async def list_email_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """获取所有邮箱配置(admin)"""
    configs = db.query(EmailConfig).order_by(EmailConfig.created_at.desc()).all()
    return configs


@router.put("/configs/{config_id}", response_model=EmailConfigResponse)
async def update_email_config(
    config_id: int,
    payload: EmailConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """更新邮箱配置(admin)"""
    config = db.query(EmailConfig).filter(EmailConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"邮箱配置不存在: id={config_id}",
        )

    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        config.password_encrypted = encrypt_password(data.pop("password"))
    elif "password" in data:
        data.pop("password")

    for field, value in data.items():
        setattr(config, field, value)

    db.commit()
    db.refresh(config)
    logger.info(f"更新邮箱配置 id={config_id} by {current_user.username}")
    return config


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """删除邮箱配置(admin)"""
    config = db.query(EmailConfig).filter(EmailConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"邮箱配置不存在: id={config_id}",
        )
    # 同步删除日志，避免外键约束
    db.query(EmailFetchLogModel).filter(
        EmailFetchLogModel.config_id == config_id
    ).delete()
    db.delete(config)
    db.commit()
    logger.info(f"删除邮箱配置 id={config_id} by {current_user.username}")
    return None


# ---------- 测试连接 ----------
@router.post("/test-connection", response_model=EmailTestResponse)
async def test_connection(
    payload: EmailTestRequest,
    current_user: User = Depends(require_role(["admin"])),
):
    """测试邮箱连接(admin)"""
    success, message = await EmailFetcherService.test_connection(payload)
    return EmailTestResponse(success=success, message=message)


# ---------- 手动触发拉取 ----------
@router.post("/fetch/{config_id}", response_model=EmailFetchResult)
async def manual_fetch(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"])),
):
    """手动触发邮件拉取(admin/operator)"""
    config = db.query(EmailConfig).filter(EmailConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"邮箱配置不存在: id={config_id}",
        )
    logger.info(
        f"手动触发邮箱拉取 id={config_id} by {current_user.username}"
    )
    result = await EmailFetcherService.fetch_invoices(config_id)
    return EmailFetchResult(**result)


# ---------- 拉取日志 ----------
@router.get("/fetch-logs", response_model=EmailFetchLogPage)
async def list_fetch_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    config_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """获取拉取日志(分页, admin)"""
    query = db.query(EmailFetchLogModel)
    if config_id is not None:
        query = query.filter(EmailFetchLogModel.config_id == config_id)
    total = query.count()
    items = (
        query.order_by(EmailFetchLogModel.fetch_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return EmailFetchLogPage(
        total=total,
        page=page,
        page_size=page_size,
        items=[EmailFetchLogSchema.model_validate(item) for item in items],
    )
