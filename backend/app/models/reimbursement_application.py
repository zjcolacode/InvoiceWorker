from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func

from app.core.database import Base


class ReimbursementApplication(Base):
    """报销申请单"""

    __tablename__ = "reimbursement_applications"

    id = Column(Integer, primary_key=True, index=True)
    reimburse_no = Column(String(50), unique=True, nullable=False)  # 报销单编号 RBS-YYYYMMDD-NNN
    applicant_name = Column(String(100), nullable=False)  # 报销人姓名
    applicant_position = Column(String(100), nullable=True)  # 报销人岗位
    reimburse_date = Column(String(20), nullable=False)  # 报销日期
    department = Column(String(50), nullable=False)  # 报销部门
    category = Column(String(50), nullable=False)  # 报销类别
    reason = Column(Text, nullable=False)  # 报销事由
    remark = Column(Text, nullable=True)  # 备注信息
    total_amount = Column(Float, default=0.0)  # 报销总金额
    invoice_ids = Column(Text, nullable=False)  # 关联发票ID列表，JSON格式 [1,2,3]
    attachment_paths = Column(Text, nullable=True)  # 附件文件路径，JSON格式
    status = Column(String(20), default="已提交")  # 状态：已提交/审批中/已通过/已拒绝
    submitted_by = Column(Integer, nullable=True)  # 提交人用户ID
    created_at = Column(DateTime, server_default=func.now())
