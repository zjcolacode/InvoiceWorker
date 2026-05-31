"""
邮件暂存模型
拉取邮件后先存到该表，由用户手动确认后再导入到 invoices。
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class EmailMessage(Base):
    """邮件附件暂存（一封邮件多附件按附件粒度存储多条）"""

    __tablename__ = "email_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_id = Column(Integer, ForeignKey("email_configs.id"), nullable=False, index=True)
    message_uid = Column(String(100), nullable=True, index=True)  # IMAP UID，用于去重
    subject = Column(String(500), nullable=True)        # 邮件主题
    sender = Column(String(200), nullable=True)         # 发件人
    received_at = Column(DateTime(timezone=True), nullable=True)  # 邮件接收时间
    attachment_name = Column(String(300), nullable=True)  # 附件文件名
    attachment_path = Column(String(500), nullable=True)  # 附件临时存储路径
    file_size = Column(Integer, default=0)                # 文件大小(bytes)
    is_imported = Column(Boolean, default=False, nullable=False, index=True)  # 是否已导入
    imported_at = Column(DateTime(timezone=True), nullable=True)  # 导入时间
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
