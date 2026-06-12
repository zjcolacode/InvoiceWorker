from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


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
