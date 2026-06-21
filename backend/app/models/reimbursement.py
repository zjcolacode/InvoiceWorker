from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class ReimbursementRecord(Base):
    """报销单核销记录"""

    __tablename__ = "reimbursement_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    original_filename = Column(String(255), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_count = Column(Integer, nullable=False, default=0)
    matched_count = Column(Integer, nullable=False, default=0)
    unmatched_count = Column(Integer, nullable=False, default=0)
    unmatched_details = Column(Text, nullable=True)  # JSON: 未匹配的发票号码列表
    created_at = Column(DateTime(timezone=True), server_default=func.now())
