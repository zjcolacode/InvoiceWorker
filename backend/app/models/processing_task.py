from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class ProcessingTask(Base):
    """处理任务模型"""

    __tablename__ = "processing_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_type = Column(String(50), nullable=False)  # email_fetch, ocr_recognize, batch_import
    status = Column(String(20), default="pending", nullable=False)  # pending, processing, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    invoice_count = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
