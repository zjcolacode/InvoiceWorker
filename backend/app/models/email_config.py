from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class EmailConfig(Base):
    """邮箱配置模型"""

    __tablename__ = "email_configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_address = Column(String(100), nullable=False)
    imap_server = Column(String(200), nullable=False)
    port = Column(Integer, default=993, nullable=False)
    password_encrypted = Column(String(500), nullable=False)
    check_interval_minutes = Column(Integer, default=30, nullable=False)
    use_ssl = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_check_at = Column(DateTime(timezone=True), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
