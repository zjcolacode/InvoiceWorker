"""导出相关 Pydantic Schema"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ExportMode(str, Enum):
    """导出模式"""

    monthly_summary = "monthly_summary"  # 按月度汇总(按日期)
    category_summary = "category_summary"  # 按分类汇总
    detail = "detail"  # 明细表


class ExportRequest(BaseModel):
    """导出请求"""

    mode: ExportMode = Field(ExportMode.detail, description="导出模式")
    year: int = Field(..., ge=2000, le=2999, description="年份")
    month: int = Field(..., ge=1, le=12, description="月份")
    category: Optional[str] = Field(None, description="筛选分类(可选)")
    source_type: Optional[str] = Field(
        None, description="筛选来源类型: pdf / paper (可选)"
    )


class ExportResponse(BaseModel):
    """导出响应"""

    filename: str
    download_url: str
    record_count: int


class ExportFileItem(BaseModel):
    """导出历史文件项"""

    filename: str
    size: int
    created_at: str
    mode: Optional[str] = None
    download_url: str
