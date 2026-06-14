from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.core.database import Base


class InvoiceDetailUploadLog(Base):
    """全量发票明细上传记录"""

    __tablename__ = "invoice_detail_upload_logs"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)  # 上传文件名
    total_count = Column(Integer, default=0)                 # 上传记录总数
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # 上传人
    created_at = Column(DateTime, server_default=func.now())


class InvoiceDetail(Base):
    """全量发票明细"""

    __tablename__ = "invoice_details"

    id = Column(Integer, primary_key=True, index=True)
    upload_batch_id = Column(Integer, ForeignKey("invoice_detail_upload_logs.id"), nullable=False)
    serial_no = Column(String(50), nullable=True)           # 序号
    invoice_code = Column(String(50), nullable=True)        # 发票代码
    invoice_no = Column(String(50), nullable=True)          # 发票号码
    digital_invoice_no = Column(String(50), nullable=True)  # 数电发票号码（核销匹配键）
    seller_tax_no = Column(String(50), nullable=True)       # 销方识别号
    seller_name = Column(String(200), nullable=True)        # 销方名称
    buyer_tax_no = Column(String(50), nullable=True)        # 购方识别号
    buyer_name = Column(String(200), nullable=True)         # 购买方名称
    invoice_date = Column(String(50), nullable=True)        # 开票日期
    amount = Column(String(50), nullable=True)              # 金额
    tax_amount = Column(String(50), nullable=True)          # 税额
    total_amount = Column(String(50), nullable=True)        # 价税合计
    invoice_source = Column(String(100), nullable=True)     # 发票来源
    invoice_type = Column(String(100), nullable=True)       # 发票票种
    invoice_status = Column(String(50), nullable=True)      # 发票状态
    is_positive = Column(String(10), nullable=True)         # 是否正数发票
    risk_level = Column(String(50), nullable=True)          # 发票风险等级
    issuer = Column(String(100), nullable=True)             # 开票人
    remark = Column(String(500), nullable=True)             # 备注
    goods_or_service_name = Column(String(500), nullable=True)  # 货物或应税劳务名称
    verify_status = Column(String(20), default="待核销")    # 核销状态：待核销/已核销/未匹配
    verified_at = Column(DateTime, nullable=True)           # 核销时间
    match_method = Column(String(20), nullable=True)        # 邮箱匹配 / 手工匹配
    reimburse_status = Column(String(20), default="待报销")  # 报销状态：待报销/已报销
    created_at = Column(DateTime, server_default=func.now())
