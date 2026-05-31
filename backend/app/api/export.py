"""
导出 API 路由

- POST   /api/export/generate         生成 Excel 文件
- GET    /api/export/download/{name}  下载 Excel
- GET    /api/export/history          获取导出历史
- DELETE /api/export/files/{name}     删除导出文件
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.user import User
from app.schemas.export import (
    ExportFileItem,
    ExportMode,
    ExportRequest,
    ExportResponse,
)
from app.services.excel_exporter import (
    ExcelExporter,
    ensure_export_dir,
    list_export_files,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# operator 以上(operator/manager/admin/user) 都可执行
ALLOWED_ROLES = ["admin", "user", "operator", "manager"]
ADMIN_ROLES = ["admin"]

EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def _safe_filename(name: str) -> str:
    """防止路径穿越"""
    base = os.path.basename(name)
    if base != name or not base or base.startswith(".."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="非法的文件名",
        )
    return base


def _resolve_export_file(filename: str) -> Path:
    """解析导出文件路径并校验"""
    name = _safe_filename(filename)
    out_dir = ensure_export_dir()
    target = (out_dir / name).resolve()
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
            detail=f"导出文件不存在: {name}",
        )
    return target


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------
@router.post("/generate", response_model=ExportResponse)
async def generate_export(
    payload: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """生成 Excel 导出文件

    非 admin 只能导出本人上传/导入的发票。
    """
    exporter = ExcelExporter()
    # 非 admin 仅限本人发票
    user_filter_id = (
        None if (current_user.role or "").lower() == "admin" else current_user.id
    )
    try:
        if payload.mode == ExportMode.monthly_summary:
            out_path, count = exporter.export_monthly_summary(
                db,
                year=payload.year,
                month=payload.month,
                category=payload.category,
                source_type=payload.source_type,
                user_id=user_filter_id,
            )
        elif payload.mode == ExportMode.category_summary:
            out_path, count = exporter.export_category_summary(
                db,
                year=payload.year,
                month=payload.month,
                category=payload.category,
                source_type=payload.source_type,
                user_id=user_filter_id,
            )
        else:
            out_path, count = exporter.export_detail(
                db,
                year=payload.year,
                month=payload.month,
                category=payload.category,
                source_type=payload.source_type,
                user_id=user_filter_id,
            )
    except Exception as e:
        logger.exception("生成导出文件失败")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成导出文件失败: {e}",
        )

    filename = os.path.basename(out_path)
    logger.info(
        f"用户 {current_user.username} 生成导出 {payload.mode.value}: "
        f"{filename} ({count} 张)"
    )
    return ExportResponse(
        filename=filename,
        download_url=f"/api/export/download/{filename}",
        record_count=count,
    )


@router.get("/download/{filename}")
async def download_export(
    filename: str,
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """下载 Excel 文件"""
    target = _resolve_export_file(filename)
    return FileResponse(
        path=str(target),
        media_type=EXCEL_MIME,
        filename=target.name,
        headers={
            "Content-Disposition": f'attachment; filename="{target.name}"',
        },
    )


@router.get("/history", response_model=List[ExportFileItem])
async def export_history(
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """获取导出历史"""
    items = list_export_files()
    return [
        ExportFileItem(
            filename=it["filename"],
            size=it["size"],
            created_at=datetime.fromtimestamp(it["created_at"]).isoformat(),
            mode=it.get("mode"),
            download_url=f"/api/export/download/{it['filename']}",
        )
        for it in items
    ]


@router.delete("/files/{filename}", response_model=dict)
async def delete_export_file(
    filename: str,
    current_user: User = Depends(require_role(ALLOWED_ROLES)),
):
    """删除导出文件"""
    target = _resolve_export_file(filename)
    try:
        target.unlink()
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除失败: {e}",
        )
    logger.info(f"用户 {current_user.username} 删除导出文件: {target.name}")
    return {"success": True, "filename": target.name}
