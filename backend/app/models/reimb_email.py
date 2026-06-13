"""报销单管理模块 - 独立邮箱数据模型（与系统邮箱配置完全分离）。"""
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey
from app.core.database import Base


class ReimbEmailConfig(Base):
    """报销单管理专用邮箱配置。"""
    __tablename__ = "reimb_email_configs"

    id = Column(Integer, primary_key=True, index=True)
    email_address = Column(String(100), unique=True, nullable=False)
    imap_server = Column(String(200), nullable=False)
    port = Column(Integer, default=993)
    password_encrypted = Column(String(500), nullable=False)
    use_ssl = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    last_check_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReimbEmailMessage(Base):
    """报销单管理专用邮件暂存。"""
    __tablename__ = "reimb_email_messages"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("reimb_email_configs.id"), nullable=False)
    message_uid = Column(String(100), nullable=True)
    subject = Column(String(500), nullable=True)
    sender = Column(String(200), nullable=True)
    received_at = Column(DateTime, nullable=True)
    attachment_name = Column(String(300), nullable=True)
    attachment_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ReimbEmailFetchLog(Base):
    """报销单管理专用邮件拉取日志。"""
    __tablename__ = "reimb_email_fetch_logs"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("reimb_email_configs.id"), nullable=False)
    email_address = Column(String(100), nullable=True)
    fetch_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    total_emails_checked = Column(Integer, default=0)
    new_emails_count = Column(Integer, default=0)
    status = Column(String(20), default="success")  # success/failed/partial
    error_message = Column(Text, nullable=True)
