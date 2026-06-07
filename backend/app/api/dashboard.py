"""仪表盘统计API"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.invoice import Invoice
from app.models.processing_task import ProcessingTask
from app.models.user import User
from app.schemas.dashboard import (
    ActivityLogItem,
    ActivityLogPage,
    CategoryItem,
    DashboardStats,
    RecentInvoiceItem,
    TrendItem,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _month_prefix(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def _last_n_months(n: int) -> List[str]:
    """返回近 n 个月的 YYYY-MM 字符串(由远及近)"""
    today = datetime.now().replace(day=1)
    months: List[str] = []
    cursor = today
    for _ in range(n):
        months.append(cursor.strftime("%Y-%m"))
        # 上个月
        prev = cursor - timedelta(days=1)
        cursor = prev.replace(day=1)
    return list(reversed(months))


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取仪表盘统计数据

    非 admin 仅统计本人上传/导入的发票。
    """
    is_admin = (current_user.role or "").lower() == "admin"
    now = datetime.now()
    month_pref = _month_prefix(now)
    month_like = f"{month_pref}%"

    def _scoped(query):
        """非 admin 追加 user_id 过滤"""
        if not is_admin:
            query = query.filter(Invoice.user_id == current_user.id)
        return query

    # 本月发票总数(按 invoice_date 前缀; invoice_date 为空的不计入本月)
    total_invoices = (
        _scoped(
            db.query(func.count(Invoice.id)).filter(Invoice.invoice_date.like(month_like))
        )
        .scalar()
        or 0
    )

    # 本月总金额
    total_amount = (
        _scoped(
            db.query(func.coalesce(func.sum(Invoice.total), 0.0)).filter(
                Invoice.invoice_date.like(month_like)
            )
        )
        .scalar()
        or 0.0
    )

    # 待识别(全量: 不限月份, 反映系统中所有待处理发票)
    pending_count = (
        _scoped(db.query(func.count(Invoice.id)).filter(Invoice.status == "pending"))
        .scalar()
        or 0
    )

    # 已识别(全量: 不限月份, 反映系统累计已识别发票)
    recognized_count = (
        _scoped(
            db.query(func.count(Invoice.id)).filter(
                Invoice.status.in_(["recognized", "verified"])
            )
        )
        .scalar()
        or 0
    )

    # 分类分布(group by category)
    cat_rows = (
        _scoped(
            db.query(
                Invoice.category,
                func.count(Invoice.id),
                func.coalesce(func.sum(Invoice.total), 0.0),
            )
        )
        .group_by(Invoice.category)
        .all()
    )
    category_distribution = [
        CategoryItem(
            name=(row[0] or "未分类"),
            count=int(row[1]),
            amount=float(row[2] or 0.0),
        )
        for row in cat_rows
    ]

    # 月度趋势(近6个月)
    months = _last_n_months(6)
    trend_map = {m: {"count": 0, "amount": 0.0} for m in months}
    trend_rows = (
        _scoped(
            db.query(
                func.substr(Invoice.invoice_date, 1, 7).label("ym"),
                func.count(Invoice.id),
                func.coalesce(func.sum(Invoice.total), 0.0),
            )
            .filter(Invoice.invoice_date.isnot(None))
            .filter(Invoice.invoice_date != "")
            .filter(func.substr(Invoice.invoice_date, 1, 7).in_(months))
        )
        .group_by("ym")
        .all()
    )
    for ym, cnt, amt in trend_rows:
        if ym in trend_map:
            trend_map[ym] = {"count": int(cnt), "amount": float(amt or 0.0)}
    monthly_trend = [
        TrendItem(month=m, count=trend_map[m]["count"], amount=trend_map[m]["amount"])
        for m in months
    ]

    # 最近10条发票(按 created_at 倒序)
    recent_rows = (
        _scoped(db.query(Invoice))
        .order_by(Invoice.created_at.desc())
        .limit(10)
        .all()
    )
    recent_invoices = [
        RecentInvoiceItem(
            id=inv.id,
            invoice_no=inv.invoice_no,
            invoice_date=inv.invoice_date,
            seller_name=inv.seller_name,
            total=float(inv.total) if inv.total is not None else None,
            category=inv.category,
            status=inv.status,
            created_at=inv.created_at,
        )
        for inv in recent_rows
    ]

    return DashboardStats(
        total_invoices=int(total_invoices),
        total_amount=float(total_amount),
        pending_count=int(pending_count),
        recognized_count=int(recognized_count),
        category_distribution=category_distribution,
        recent_invoices=recent_invoices,
        monthly_trend=monthly_trend,
    )


@router.get("/activity-log", response_model=ActivityLogPage)
async def get_activity_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取操作日志(从 processing_tasks 表读取)"""
    base = db.query(ProcessingTask)
    total = base.count()
    rows = (
        base.order_by(ProcessingTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        ActivityLogItem(
            id=r.id,
            task_type=r.task_type,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            invoice_count=int(r.invoice_count or 0),
            error_log=r.error_log,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ActivityLogPage(total=total, page=page, page_size=page_size, items=items)
