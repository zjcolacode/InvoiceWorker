from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class ManualMatchRecord(Base):
    """手工匹配记录"""

    __tablename__ = "manual_match_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_detail_id = Column(Integer, ForeignKey("invoice_details.id"), nullable=False)
    original_filename = Column(String(255), nullable=False)  # 上传文件名
    file_path = Column(String(500), nullable=True)  # 保存路径
    recognized_invoice_no = Column(String(50), nullable=True)  # AI识别的发票号码
    recognized_data = Column(Text, nullable=True)  # AI识别完整结果JSON
    match_status = Column(String(20), nullable=False, default="失败")  # 成功/失败
    operated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
