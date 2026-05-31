"""仪表盘相关 Schemas"""
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class CategoryItem(BaseModel):
    """分类分布项"""

    name: str
    count: int
    amount: float


class TrendItem(BaseModel):
    """月度趋势项"""

    month: str  # YYYY-MM
    count: int
    amount: float


class RecentInvoiceItem(BaseModel):
    """最近发票简要信息"""

    id: int
    invoice_no: Optional[str] = None
    invoice_date: Optional[str] = None
    seller_name: Optional[str] = None
    total: Optional[float] = None
    category: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class DashboardStats(BaseModel):
    """仪表盘统计数据"""

    total_invoices: int = Field(..., description="本月发票总数")
    total_amount: float = Field(..., description="本月总金额")
    pending_count: int = Field(..., description="待识别数量")
    recognized_count: int = Field(..., description="已识别数量")
    category_distribution: List[CategoryItem] = Field(default_factory=list)
    recent_invoices: List[RecentInvoiceItem] = Field(default_factory=list)
    monthly_trend: List[TrendItem] = Field(default_factory=list)


class ActivityLogItem(BaseModel):
    """操作日志项"""

    id: int
    task_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    invoice_count: int = 0
    error_log: Optional[str] = None
    created_at: Optional[datetime] = None


class ActivityLogPage(BaseModel):
    """操作日志分页"""

    total: int
    page: int
    page_size: int
    items: List[ActivityLogItem] = Field(default_factory=list)


__all__ = [
    "CategoryItem",
    "TrendItem",
    "RecentInvoiceItem",
    "DashboardStats",
    "ActivityLogItem",
    "ActivityLogPage",
]
