from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class Invoice(Base):
    """发票模型"""

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_no = Column(String(50), index=True, nullable=True)
    invoice_date = Column(String(20), nullable=True)
    seller_name = Column(String(200), nullable=True)
    buyer_name = Column(String(200), nullable=True)
    amount = Column(Float, nullable=True)  # 金额
    tax = Column(Float, nullable=True)  # 税额
    total = Column(Float, nullable=True)  # 价税合计
    items = Column(Text, nullable=True)  # 发票明细(JSON格式)
    category = Column(String(50), nullable=True)  # 发票分类
    source_type = Column(String(20), nullable=False, default="pdf")  # pdf / paper
    file_path = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)  # SHA256哈希，用于去重
    recognized_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, recognized, verified, error
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
