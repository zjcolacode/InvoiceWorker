"""
发票管理API路由

提供发票上传、列表查询、详情、删除、统计等接口。
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.invoice import InvoiceResponse
from app.services.file_organizer import (
    ALLOWED_EXTENSIONS,
    delete_invoice_file,
    save_upload_file,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 允许上传/查看/管理的角色 (operator及以上 - 当前系统包含 admin/user)
ALLOWED_ROLES = ["admin", "user", "operator", "manager"]

# 单文件最大字节数 (20MB)
MAX_FILE_SIZE = 20 * 1024 * 1024


@router.post("/upload", response_model=List[InvoiceResponse])
async def upload_invoices(
    files: List[UploadFile] = File(..., description="发票文件,支持多文件"),
    source_type: str = Form(..., description="来源类型: pdf / paper"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """
    上传发票文件 (支持多文件)

    - 文件类型限制: .pdf / .jpg / .jpeg / .png
    - 单文件最大 20MB
    - 按来源类型存储到 pdf_invoices 或 paper_invoices 目录,并按当前日期分文件夹
    - 创建 status=pending 的 Invoice 记录
    """
    if source_type not in ("pdf", "paper"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_type 必须为 pdf 或 paper",
        )
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未上传任何文件",
        )

    created: List[Invoice] = []

    for file in files:
        # 校验扩展名
        filename = file.filename or ""
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {filename}",
            )

        # 校验源类型与文件类型匹配
        if source_type == "pdf" and ext != ".pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"电子发票仅支持 PDF: {filename}",
            )
        if source_type == "paper" and ext == ".pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"纸质发票仅支持图片: {filename}",
            )

        # 文件大小校验 (尽力而为, 通过 spooled file 大小)
        try:
            file.file.seek(0, 2)
            size = file.file.tell()
            file.file.seek(0)
        except Exception:
            size = 0
        if size and size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件超过 20MB 限制: {filename}",
            )

        # 保存文件
        try:
            rel_path = await save_upload_file(file, source_type)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        except Exception as e:
            logger.exception(f"保存文件失败: {filename}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"保存文件失败: {e}",
            )

        # 创建数据库记录
        invoice = Invoice(
            source_type=source_type,
            file_path=rel_path,
            original_filename=filename,
            status="pending",
            user_id=current_user.id,
        )
        db.add(invoice)
        created.append(invoice)

    db.commit()
    for inv in created:
        db.refresh(inv)

    logger.info(f"用户 {current_user.username} 上传 {len(created)} 张发票")
    return created


@router.get("/", response_model=dict)
async def list_invoices(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    category: Optional[str] = Query(None, description="发票分类"),
    source_type: Optional[str] = Query(None, description="来源类型"),
    invoice_status: Optional[str] = Query(None, alias="status", description="状态"),
    date_from: Optional[str] = Query(None, description="开票日期起"),
    date_to: Optional[str] = Query(None, description="开票日期止"),
    keyword: Optional[str] = Query(None, description="关键词:销售方/购买方/明细"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """获取发票列表(分页+筛选+搜索)"""
    query = db.query(Invoice)

    if category:
        query = query.filter(Invoice.category == category)
    if source_type:
        query = query.filter(Invoice.source_type == source_type)
    if invoice_status:
        query = query.filter(Invoice.status == invoice_status)
    if date_from:
        query = query.filter(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.filter(Invoice.invoice_date <= date_to)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (Invoice.seller_name.like(like))
            | (Invoice.buyer_name.like(like))
            | (Invoice.items.like(like))
            | (Invoice.invoice_no.like(like))
        )

    total = query.count()
    items = (
        query.order_by(Invoice.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [InvoiceResponse.model_validate(i).model_dump() for i in items],
    }


@router.get("/stats/summary", response_model=dict)
async def get_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """统计摘要: 本月发票总数/总金额, 各分类占比"""
    now = datetime.now()
    month_prefix = now.strftime("%Y-%m")

    # 本月发票 (按 invoice_date 前缀匹配; 若 invoice_date 为空则不计入)
    month_query = db.query(Invoice).filter(Invoice.invoice_date.like(f"{month_prefix}%"))
    month_count = month_query.count()
    month_total = (
        db.query(func.coalesce(func.sum(Invoice.total), 0.0))
        .filter(Invoice.invoice_date.like(f"{month_prefix}%"))
        .scalar()
        or 0.0
    )

    # 各分类占比 (全局)
    category_rows = (
        db.query(Invoice.category, func.count(Invoice.id), func.coalesce(func.sum(Invoice.total), 0.0))
        .group_by(Invoice.category)
        .all()
    )
    total_count = sum(r[1] for r in category_rows) or 1
    categories = [
        {
            "category": row[0] or "未分类",
            "count": int(row[1]),
            "amount": float(row[2] or 0.0),
            "percent": round(row[1] * 100.0 / total_count, 2),
        }
        for row in category_rows
    ]

    return {
        "month": month_prefix,
        "month_count": month_count,
        "month_total": float(month_total),
        "categories": categories,
    }


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """获取发票详情"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"发票不存在: id={invoice_id}",
        )
    return invoice


@router.delete("/{invoice_id}", response_model=dict)
async def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """删除发票(同时删除磁盘文件)"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"发票不存在: id={invoice_id}",
        )

    file_path = invoice.file_path
    db.delete(invoice)
    db.commit()

    file_deleted = False
    if file_path:
        file_deleted = delete_invoice_file(file_path)

    logger.info(
        f"用户 {current_user.username} 删除发票 id={invoice_id}, file_deleted={file_deleted}"
    )
    return {"success": True, "id": invoice_id, "file_deleted": file_deleted}
