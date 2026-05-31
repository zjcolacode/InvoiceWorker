from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """创建分类请求"""

    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    keywords: Optional[str] = Field(None, description="关键词，逗号分隔")
    description: Optional[str] = Field(None, max_length=500, description="分类描述")
    color: Optional[str] = Field("#409EFF", max_length=20, description="显示颜色")


class CategoryUpdate(BaseModel):
    """更新分类请求(全部字段可选)"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    keywords: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """分类响应"""

    id: int
    name: str
    keywords: Optional[str] = None
    description: Optional[str] = None
    color: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReclassifyResponse(BaseModel):
    """重新分类的响应"""

    total: int = Field(..., description="处理的发票总数")
    updated: int = Field(..., description="实际更新的发票数")
    skipped: int = Field(0, description="无开票内容跳过的数量")
