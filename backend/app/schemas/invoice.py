from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InvoiceCreate(BaseModel):
    """创建发票请求"""
    source_type: str = Field(..., description="来源类型: pdf / paper")
    file_path: str = Field(..., description="文件存储路径")
    original_filename: Optional[str] = Field(None, description="原始文件名")


class SkippedFile(BaseModel):
    """跳过的重复文件信息"""
    filename: str
    reason: str
    existing_id: Optional[int] = None


class InvoiceUploadResult(BaseModel):
    """发票上传结果（含去重信息）"""
    uploaded: list["InvoiceResponse"] = Field(default_factory=list, description="成功上传的发票列表")
    skipped: list[SkippedFile] = Field(default_factory=list, description="跳过的重复文件列表")
    message: str = Field("", description="汇总提示")


class InvoiceUpdate(BaseModel):
    """更新发票请求"""
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    seller_name: Optional[str] = None
    buyer_name: Optional[str] = None
    amount: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    items: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None


class InvoiceResponse(BaseModel):
    """发票响应"""
    id: int
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    seller_name: Optional[str] = None
    buyer_name: Optional[str] = None
    amount: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    items: Optional[str] = None
    category: Optional[str] = None
    source_type: str
    file_path: Optional[str] = None
    original_filename: Optional[str] = None
    recognized_at: Optional[datetime] = None
    status: str
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


InvoiceUploadResult.model_rebuild()


class RecognitionResult(BaseModel):
    """识别结果"""
    success: bool = Field(..., description="识别是否成功")
    data: Optional[dict] = Field(None, description="识别数据")
    error: Optional[str] = Field(None, description="错误信息")


class BatchRecognitionRequest(BaseModel):
    """批量识别请求"""
    invoice_ids: list[int] = Field(..., description="发票ID列表")


class BatchRecognitionResponse(BaseModel):
    """批量识别响应"""
    total: int = Field(..., description="总数")
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    results: list[RecognitionResult] = Field(default_factory=list, description="各项识别结果")
