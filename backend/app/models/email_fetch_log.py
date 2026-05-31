"""
邮箱拉取日志模型
记录每次邮箱拉取任务的执行情况
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class EmailFetchLog(Base):
    """邮箱拉取日志"""

    __tablename__ = "email_fetch_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    config_id = Column(Integer, ForeignKey("email_configs.id"), nullable=False, index=True)
    email_address = Column(String(100), nullable=True)
    fetch_time = Column(DateTime(timezone=True), server_default=func.now())
    total_emails_checked = Column(Integer, default=0, nullable=False)
    new_invoices_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="success", nullable=False)  # success / failed / partial
    error_message = Column(Text, nullable=True)
