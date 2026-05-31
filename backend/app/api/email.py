"""
邮箱配置API路由
"""
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.email_config import EmailConfig
from app.models.email_fetch_log import EmailFetchLog as EmailFetchLogModel
from app.models.email_message import EmailMessage
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.email_config import (
    EmailConfigCreate,
    EmailConfigResponse,
    EmailConfigUpdate,
    EmailFetchFilter,
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
    payload: Optional[EmailFetchFilter] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator"])),
):
    """手动触发邮件拉取(admin/operator)

    可选过滤条件：keyword / date_from / date_to / sender / has_attachment
    """
    config = db.query(EmailConfig).filter(EmailConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"邮箱配置不存在: id={config_id}",
        )
    filters = payload.model_dump() if payload else {}
    logger.info(
        f"手动触发邮箱拉取 id={config_id} by {current_user.username} filters={filters}"
    )
    result = await EmailFetcherService.fetch_invoices(config_id, filters)
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


# ---------- 邮件列表（待导入 / 已导入） ----------
def _serialize_email_message(m: EmailMessage) -> dict:
    return {
        "id": m.id,
        "config_id": m.config_id,
        "subject": m.subject,
        "sender": m.sender,
        "received_at": m.received_at.isoformat() if m.received_at else None,
        "attachment_name": m.attachment_name,
        "file_size": m.file_size or 0,
        "is_imported": bool(m.is_imported),
        "imported_at": m.imported_at.isoformat() if m.imported_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/messages")
async def list_email_messages(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    is_imported: Optional[bool] = Query(default=None),
    config_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator", "user"])),
):
    """获取拉取到的邮件列表（分页）

    - admin 可查看全部
    - 其他角色仅可查看自己邮箱拉取的邮件
    """
    query = db.query(EmailMessage)
    # 排除无主题的历史UID占位记录，保留有主题的正常邮件（含“无附件正文邮件”）
    query = query.filter(EmailMessage.subject.isnot(None))
    # 双保险：排除早期历史UID占位标记，避免迁移未清理时脱漏
    query = query.filter(EmailMessage.subject != '[历史邮件-旧系统已处理]')
    if (current_user.role or "").lower() != "admin":
        query = query.filter(EmailMessage.user_id == current_user.id)
    if is_imported is not None:
        query = query.filter(EmailMessage.is_imported == is_imported)
    if config_id is not None:
        query = query.filter(EmailMessage.config_id == config_id)
    total = query.count()
    # 按 received_at 倒序（最新在前），received_at 为空时用 created_at 兑底
    items = (
        query.order_by(
            desc(func.coalesce(EmailMessage.received_at, EmailMessage.created_at))
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize_email_message(m) for m in items],
    }


@router.post("/messages/import")
async def import_email_messages(
    payload: dict = Body(..., description="{'message_ids': [int, ...]}"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator", "user"])),
):
    """将选中的邮件附件导入发票管理"""
    raw_ids = payload.get("message_ids") if isinstance(payload, dict) else None
    if not isinstance(raw_ids, list) or not raw_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_ids 不能为空",
        )
    try:
        message_ids = [int(x) for x in raw_ids]
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="message_ids 必须为整数数组",
        )

    query = (
        db.query(EmailMessage)
        .filter(EmailMessage.id.in_(message_ids))
        .filter(EmailMessage.is_imported == False)  # noqa: E712
    )
    if (current_user.role or "").lower() != "admin":
        query = query.filter(EmailMessage.user_id == current_user.id)
    messages = query.all()

    imported_count = 0
    skipped_count = 0
    now = datetime.utcnow()
    for msg in messages:
        if not msg.attachment_path or not os.path.exists(msg.attachment_path):
            skipped_count += 1
            continue
        invoice = Invoice(
            source_type="email",
            file_path=msg.attachment_path,
            original_filename=msg.attachment_name or os.path.basename(msg.attachment_path),
            status="pending",
            user_id=msg.user_id,
        )
        db.add(invoice)
        msg.is_imported = True
        msg.imported_at = now
        imported_count += 1

    db.commit()
    logger.info(
        f"邮件附件导入 by {current_user.username}: 请求={len(message_ids)} 成功={imported_count} 跳过={skipped_count}"
    )
    return {
        "success": True,
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "requested": len(message_ids),
    }


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "operator", "user"])),
):
    """删除邮件记录（未导入时同步删除临时附件文件）"""
    msg = db.query(EmailMessage).filter(EmailMessage.id == message_id).first()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"邮件记录不存在: id={message_id}",
        )
    if (current_user.role or "").lower() != "admin" and msg.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权删除他人拉取的邮件",
        )
    # 未导入时可以安全删除临时文件；已导入的记录不动附件（发票记录在用）
    if not msg.is_imported and msg.attachment_path:
        try:
            if os.path.exists(msg.attachment_path):
                os.remove(msg.attachment_path)
        except OSError as e:
            logger.warning(f"删除临时附件失败 {msg.attachment_path}: {e}")
    db.delete(msg)
    db.commit()
    return None
