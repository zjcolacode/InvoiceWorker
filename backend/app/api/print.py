"""
打印API路由

- POST   /api/print/generate         生成A4打印PDF (每页2张发票)
- GET    /api/print/download/{name}  下载打印PDF
- GET    /api/print/preview/{name}   浏览器内预览(inline)
- GET    /api/print/files            列出最近生成的打印文件
- DELETE /api/print/files/{name}     删除指定打印文件
- DELETE /api/print/clean            清理7天前的打印文件 (admin)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.invoice import Invoice
from app.models.user import User
from app.services.print_service import (
    PrintService,
    cleanup_old_print_files,
    ensure_output_dir,
    list_print_files,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# 普通操作允许的角色
ALLOWED_ROLES = ["admin", "user", "operator", "manager"]
# 仅 admin 可执行的操作
ADMIN_ROLES = ["admin"]


# ----------------------------------------------------------------------
# 请求/响应模型
# ----------------------------------------------------------------------
class GeneratePrintRequest(BaseModel):
    invoice_ids: List[int] = Field(..., description="要打印的发票ID列表")
    layout: str = Field("2_per_page", description="排版方式, 当前固定: 2_per_page")


class GeneratePrintResponse(BaseModel):
    filename: str
    download_url: str
    preview_url: str
    invoice_count: int
    page_count: int


class PrintFileItem(BaseModel):
    filename: str
    size: int
    created_at: str
    download_url: str
    preview_url: str


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------
def _safe_filename(name: str) -> str:
    """防止路径穿越, 仅允许文件名(无目录分隔符)"""
    base = os.path.basename(name)
    if base != name or not base or base.startswith(".."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非法的文件名",
        )
    return base


def _resolve_print_file(filename: str) -> Path:
    """解析打印输出文件的绝对路径并校验存在"""
    name = _safe_filename(filename)
    out_dir = ensure_output_dir()
    target = (out_dir / name).resolve()
    # 确保仍在输出目录内
    try:
        target.relative_to(out_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非法的文件路径",
        )
    if not target.exists() or not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"打印文件不存在: {name}",
        )
    return target


# ----------------------------------------------------------------------
# 路由
# ----------------------------------------------------------------------
@router.post("/generate", response_model=GeneratePrintResponse)
async def generate_print_pdf(
    payload: GeneratePrintRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """生成A4打印PDF(每页2张发票)"""
    if not payload.invoice_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少选择一张发票",
        )
    if payload.layout not in ("2_per_page",):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"暂不支持的排版方式: {payload.layout}",
        )

    invoices: List[Invoice] = (
        db.query(Invoice).filter(Invoice.id.in_(payload.invoice_ids)).all()
    )
    if not invoices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到任何发票记录",
        )

    # 按用户传入顺序排列
    id_order = {inv_id: idx for idx, inv_id in enumerate(payload.invoice_ids)}
    invoices.sort(key=lambda inv: id_order.get(inv.id, 9999))

    file_paths: List[str] = []
    missing: List[int] = []
    for inv in invoices:
        if not inv.file_path:
            missing.append(inv.id)
            continue
        p = Path(inv.file_path)
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if not p.exists():
            missing.append(inv.id)
            continue
        file_paths.append(str(p))

    if not file_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"所选发票均没有可访问的源文件 (missing ids: {missing})",
        )

    service = PrintService()
    try:
        out_path = service.generate_print_pdf(file_paths)
    except Exception as e:
        logger.exception("生成打印PDF失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成打印PDF失败: {e}",
        )

    filename = os.path.basename(out_path)
    page_count = (len(file_paths) + 1) // 2

    logger.info(
        f"用户 {current_user.username} 生成打印PDF: {filename} "
        f"(发票 {len(file_paths)} 张, 共 {page_count} 页, 缺失 {len(missing)} 张)"
    )

    return GeneratePrintResponse(
        filename=filename,
        download_url=f"/api/print/download/{filename}",
        preview_url=f"/api/print/preview/{filename}",
        invoice_count=len(file_paths),
        page_count=page_count,
    )


@router.get("/download/{filename}")
async def download_print_pdf(
    filename: str,
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """下载打印PDF"""
    target = _resolve_print_file(filename)
    return FileResponse(
        path=str(target),
        media_type="application/pdf",
        filename=target.name,
        headers={
            "Content-Disposition": f'attachment; filename="{target.name}"',
        },
    )


@router.get("/preview/{filename}")
async def preview_print_pdf(
    filename: str,
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """浏览器内预览(inline)"""
    target = _resolve_print_file(filename)
    return FileResponse(
        path=str(target),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{target.name}"',
        },
    )


@router.get("/files", response_model=List[PrintFileItem])
async def list_files(
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """列出最近生成的打印文件"""
    items = list_print_files()
    return [
        PrintFileItem(
            filename=it["filename"],
            size=it["size"],
            created_at=datetime.fromtimestamp(it["created_at"]).isoformat(),
            download_url=f"/api/print/download/{it['filename']}",
            preview_url=f"/api/print/preview/{it['filename']}",
        )
        for it in items
    ]


@router.delete("/files/{filename}", response_model=dict)
async def delete_file(
    filename: str,
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """删除指定打印文件"""
    target = _resolve_print_file(filename)
    try:
        target.unlink()
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除失败: {e}",
        )
    logger.info(f"用户 {current_user.username} 删除打印文件: {target.name}")
    return {"success": True, "filename": target.name}


@router.delete("/clean", response_model=dict)
async def clean_old_files(
    days: Optional[int] = 7,
    current_user: User = Depends(require_role(ADMIN_ROLES)),
):
    """清理超过指定天数的打印文件 (默认7天, 仅 admin)"""
    keep_days = days if days and days > 0 else 7
    removed = cleanup_old_print_files(days=keep_days)
    return {"success": True, "removed": removed, "days": keep_days}
