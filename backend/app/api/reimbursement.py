"""报销单管理 API：上传发票明细清单核销 + 历史记录查询。"""
import csv
import io
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.invoice import Invoice
from app.models.reimbursement import ReimbursementRecord
from app.models.user import User
from app.schemas.reimbursement import ReimbursementRecordResponse, ReimbursementResult

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_invoice_numbers_from_xlsx(content: bytes) -> list[str]:
    """从 xlsx 文件中提取「发票号码」列的所有值。"""
    wb = load_workbook(filename=io.BytesIO(content), read_only=True)
    ws = wb.active
    if ws is None:
        raise ValueError("Excel 文件没有活动工作表")

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel 文件为空")

    # 在表头行中查找「发票号码」列
    header = rows[0]
    col_idx = None
    for idx, cell in enumerate(header):
        if cell and "发票号码" in str(cell).strip():
            col_idx = idx
            break
    if col_idx is None:
        raise ValueError("未找到「发票号码」列，请检查文件表头")

    invoice_nos = []
    for row in rows[1:]:
        if col_idx < len(row) and row[col_idx] is not None:
            val = str(row[col_idx]).strip()
            if val:
                invoice_nos.append(val)
    wb.close()
    return invoice_nos


def _parse_invoice_numbers_from_csv(content: bytes) -> list[str]:
    """从 csv 文件中提取「发票号码」列的所有值。"""
    # 尝试多种编码
    text = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb2312"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("无法识别文件编码，请使用 UTF-8 或 GBK 编码")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError("CSV 文件为空")

    header = rows[0]
    col_idx = None
    for idx, cell in enumerate(header):
        if "发票号码" in cell.strip():
            col_idx = idx
            break
    if col_idx is None:
        raise ValueError("未找到「发票号码」列，请检查文件表头")

    invoice_nos = []
    for row in rows[1:]:
        if col_idx < len(row) and row[col_idx].strip():
            invoice_nos.append(row[col_idx].strip())
    return invoice_nos


# ============================================================
# 上传核销
# ============================================================
@router.post("/upload", response_model=ReimbursementResult)
async def upload_and_verify(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传发票明细清单（xlsx/csv），根据发票号码核销已有发票记录。"""
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail="仅支持 xlsx 和 csv 格式文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 解析发票号码
    try:
        if ext == "xlsx":
            invoice_nos = _parse_invoice_numbers_from_xlsx(content)
        else:
            invoice_nos = _parse_invoice_numbers_from_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 去重（保留顺序）
    seen = set()
    unique_nos = []
    for no in invoice_nos:
        if no not in seen:
            seen.add(no)
            unique_nos.append(no)

    if not unique_nos:
        raise HTTPException(status_code=400, detail="文件中未解析到有效的发票号码")

    # 查询系统中匹配的发票
    matched_invoices = (
        db.query(Invoice)
        .filter(Invoice.invoice_no.in_(unique_nos))
        .all()
    )
    matched_nos = {inv.invoice_no for inv in matched_invoices}
    unmatched_nos = [no for no in unique_nos if no not in matched_nos]

    # 批量更新核销状态
    now = datetime.now(timezone.utc)
    for inv in matched_invoices:
        inv.is_reimbursed = True
        inv.reimbursed_at = now

    # 保存核销记录
    record = ReimbursementRecord(
        original_filename=filename,
        uploaded_by=current_user.id,
        total_count=len(unique_nos),
        matched_count=len(matched_invoices),
        unmatched_count=len(unmatched_nos),
        unmatched_details=json.dumps(unmatched_nos, ensure_ascii=False),
    )
    db.add(record)
    db.commit()

    logger.info(
        f"核销完成: 文件={filename}, 总数={len(unique_nos)}, "
        f"匹配={len(matched_invoices)}, 未匹配={len(unmatched_nos)}"
    )

    return ReimbursementResult(
        total_count=len(unique_nos),
        matched_count=len(matched_invoices),
        unmatched_count=len(unmatched_nos),
        unmatched_details=unmatched_nos,
    )


# ============================================================
# 核销历史记录
# ============================================================
@router.get("/records", response_model=dict)
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取核销历史记录（分页）。"""
    query = db.query(ReimbursementRecord)
    total = query.count()
    records = (
        query.order_by(ReimbursementRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for r in records:
        # 获取上传者用户名
        uploader_username = None
        if r.uploaded_by:
            user = db.query(User).filter(User.id == r.uploaded_by).first()
            if user:
                uploader_username = user.username

        unmatched = []
        if r.unmatched_details:
            try:
                unmatched = json.loads(r.unmatched_details)
            except (json.JSONDecodeError, TypeError):
                unmatched = []

        items.append(
            ReimbursementRecordResponse(
                id=r.id,
                original_filename=r.original_filename,
                uploaded_by=r.uploaded_by,
                uploader_username=uploader_username,
                total_count=r.total_count,
                matched_count=r.matched_count,
                unmatched_count=r.unmatched_count,
                unmatched_details=unmatched,
                created_at=r.created_at,
            )
        )

    return {"total": total, "page": page, "page_size": page_size, "items": items}
