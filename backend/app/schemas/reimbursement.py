from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class InvoiceDetailResponse(BaseModel):
    """全量发票明细响应"""
    id: int
    upload_batch_id: int
    serial_no: Optional[str] = None
    invoice_code: Optional[str] = None
    invoice_no: Optional[str] = None
    digital_invoice_no: Optional[str] = None
    seller_tax_no: Optional[str] = None
    seller_name: Optional[str] = None
    buyer_tax_no: Optional[str] = None
    buyer_name: Optional[str] = None
    invoice_date: Optional[str] = None
    amount: Optional[str] = None
    tax_amount: Optional[str] = None
    total_amount: Optional[str] = None
    invoice_source: Optional[str] = None
    invoice_type: Optional[str] = None
    invoice_status: Optional[str] = None
    is_positive: Optional[str] = None
    risk_level: Optional[str] = None
    issuer: Optional[str] = None
    remark: Optional[str] = None
    verify_status: Optional[str] = None
    verified_at: Optional[str] = None
    match_method: Optional[str] = None
    reimburse_status: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class InvoiceDetailListResponse(BaseModel):
    """全量发票明细列表响应"""
    total: int
    page: int
    page_size: int
    items: List[InvoiceDetailResponse]


class UploadDetailResult(BaseModel):
    """上传全量发票明细结果"""
    batch_id: int
    filename: str
    total_count: int
    skipped_count: int = 0


class VerifyResult(BaseModel):
    """核销结果"""
    total_count: int
    matched_count: int
    unmatched_count: int
    unmatched_details: List[str] = Field(default_factory=list)


class UploadLogResponse(BaseModel):
    """上传记录响应"""
    id: int
    original_filename: str
    total_count: int
    uploaded_by: Optional[int] = None
    uploader_username: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class UploadLogListResponse(BaseModel):
    """上传记录列表响应"""
    total: int
    page: int
    page_size: int
    items: List[UploadLogResponse]


class ReimbursementResult(BaseModel):
    """核销结果"""
    total_count: int = Field(..., description="上传的发票总数")
    matched_count: int = Field(..., description="成功核销的数量")
    unmatched_count: int = Field(..., description="未匹配的数量")
    unmatched_details: List[str] = Field(default_factory=list, description="未匹配的发票号码列表")


class ReimbursementRecordResponse(BaseModel):
    """核销记录响应"""
    id: int
    original_filename: str
    uploaded_by: Optional[int] = None
    uploader_username: Optional[str] = None
    total_count: int
    matched_count: int
    unmatched_count: int
    unmatched_details: Optional[List[str]] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# 报销单管理 - 独立邮箱相关 Schema
# ============================================================

class ReimbEmailConfigCreate(BaseModel):
    email_address: str
    imap_server: str
    port: int = 993
    password: str
    use_ssl: bool = True


class ReimbEmailConfigUpdate(BaseModel):
    email_address: Optional[str] = None
    imap_server: Optional[str] = None
    port: Optional[int] = None
    password: Optional[str] = None
    use_ssl: Optional[bool] = None
    is_active: Optional[bool] = None


class ReimbEmailConfigResponse(BaseModel):
    id: int
    email_address: str
    imap_server: str
    port: int
    use_ssl: bool
    is_active: bool
    last_check_at: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ReimbEmailMessageResponse(BaseModel):
    id: int
    config_id: int
    message_uid: Optional[str] = None
    subject: Optional[str] = None
    sender: Optional[str] = None
    received_at: Optional[str] = None
    attachment_name: Optional[str] = None
    attachment_path: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ReimbEmailFetchLogResponse(BaseModel):
    id: int
    config_id: int
    email_address: Optional[str] = None
    fetch_time: Optional[str] = None
    total_emails_checked: int = 0
    new_emails_count: int = 0
    status: str = "success"
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class ReimbEmailTestResult(BaseModel):
    success: bool
    message: str


class ReimbEmailFetchRequest(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    keyword: Optional[str] = None
    has_attachment: bool = True


# ============================================================
# 手工匹配 - Schema
# ============================================================

class ManualMatchRecognizeResult(BaseModel):
    success: bool
    recognized_invoice_no: Optional[str] = None
    recognized_data: Optional[dict] = None
    match_result: str  # matched / not_matched / recognition_failed
    message: str


class ManualMatchRecordResponse(BaseModel):
    id: int
    invoice_detail_id: int
    original_filename: str
    recognized_invoice_no: Optional[str] = None
    match_status: str
    operated_by: Optional[int] = None
    created_at: Optional[str] = None


# ============================================================
# 报销申请单 - Schema
# ============================================================

class ReimbursementApplicationCreate(BaseModel):
    """创建报销申请的请求体"""
    reimburse_date: str  # YYYY-MM-DD
    department: str
    category: str
    reason: str
    remark: Optional[str] = None
    invoice_ids: list[int]


class ReimbursementApplicationResponse(BaseModel):
    """报销申请响应"""
    id: int
    reimburse_no: str
    applicant_name: str
    applicant_position: Optional[str] = None
    reimburse_date: str
    department: str
    category: str
    reason: str
    remark: Optional[str] = None
    total_amount: float
    invoice_ids: list[int]
    status: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
