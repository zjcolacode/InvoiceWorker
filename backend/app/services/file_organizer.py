"""
文件归档服务

提供发票文件的存储、归档和删除能力。
- 电子发票(PDF) 存放在 storage/pdf_invoices/{YYYY-MM-DD}/
- 纸质发票(图片) 存放在 storage/paper_invoices/{YYYY-MM-DD}/
"""
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _get_base_dir(source_type: str) -> Path:
    """根据来源类型获取存储根目录"""
    if source_type == "pdf":
        base = settings.PDF_STORAGE_PATH
    elif source_type == "paper":
        base = settings.PAPER_STORAGE_PATH
    else:
        raise ValueError(f"不支持的来源类型: {source_type}")
    return Path(base).resolve()


def _validate_extension(filename: str, source_type: str) -> str:
    """校验扩展名并返回小写扩展名"""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}")
    if source_type == "pdf" and ext not in PDF_EXTENSIONS:
        raise ValueError(f"电子发票仅支持PDF格式，当前: {ext}")
    if source_type == "paper" and ext not in IMAGE_EXTENSIONS:
        raise ValueError(f"纸质发票仅支持图片格式(.jpg/.jpeg/.png)，当前: {ext}")
    return ext


def _safe_filename(filename: str) -> str:
    """清理文件名，去除路径分隔符和危险字符"""
    name = os.path.basename(filename)
    # 仅保留中文、英数、点、下划线、横线
    name = re.sub(r"[^\w.\-\u4e00-\u9fa5]", "_", name)
    return name or "invoice"


def _resolve_conflict(target_dir: Path, filename: str) -> Path:
    """文件名冲突时自动添加序号 (1)、(2) ..."""
    target = target_dir / filename
    if not target.exists():
        return target
    stem = Path(filename).stem
    ext = Path(filename).suffix
    i = 1
    while True:
        candidate = target_dir / f"{stem}({i}){ext}"
        if not candidate.exists():
            return candidate
        i += 1


async def save_upload_file(file: UploadFile, source_type: str) -> str:
    """
    保存上传文件到对应目录。

    :param file: FastAPI UploadFile 对象
    :param source_type: pdf / paper
    :return: 相对存储路径(相对于项目根目录)
    """
    if not file.filename:
        raise ValueError("文件名为空")

    _validate_extension(file.filename, source_type)
    safe_name = _safe_filename(file.filename)

    base_dir = _get_base_dir(source_type)
    date_folder = datetime.now().strftime("%Y-%m-%d")
    target_dir = base_dir / date_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = _resolve_conflict(target_dir, safe_name)

    # 写入文件
    try:
        with target_path.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    finally:
        await file.close()

    logger.info(f"文件保存成功: {target_path}")

    # 返回相对路径
    try:
        rel = target_path.relative_to(Path.cwd())
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(target_path).replace("\\", "/")


def organize_by_invoice_date(file_path: str, invoice_date: str) -> Optional[str]:
    """
    按发票开票日期重新归档。

    将文件从 当前日期文件夹 移动到 以 invoice_date 命名的子文件夹下,
    保持原始的 source_type 根目录(pdf_invoices / paper_invoices) 不变。

    :param file_path: 当前文件相对路径
    :param invoice_date: 发票开票日期(任何能解析为日期的字符串, 例如 2025-01-15)
    :return: 新的相对路径; 若无需移动则返回原路径
    """
    if not file_path or not invoice_date:
        return file_path

    src = Path(file_path)
    if not src.is_absolute():
        src_abs = (Path.cwd() / src).resolve()
    else:
        src_abs = src.resolve()

    if not src_abs.exists():
        logger.warning(f"待归档文件不存在: {src_abs}")
        return file_path

    # 标准化日期格式 YYYY-MM-DD
    normalized = _normalize_date(invoice_date)
    if not normalized:
        logger.warning(f"无法识别的发票日期: {invoice_date}, 跳过归档")
        return file_path

    # 父目录的父目录即为 source_type 根目录
    source_root = src_abs.parent.parent
    new_dir = source_root / normalized
    new_dir.mkdir(parents=True, exist_ok=True)

    new_path = _resolve_conflict(new_dir, src_abs.name)
    if new_path == src_abs:
        return file_path

    shutil.move(str(src_abs), str(new_path))
    logger.info(f"按开票日期归档: {src_abs} -> {new_path}")

    try:
        rel = new_path.relative_to(Path.cwd())
        return str(rel).replace("\\", "/")
    except ValueError:
        return str(new_path).replace("\\", "/")


def _normalize_date(date_str: str) -> Optional[str]:
    """尝试将多种日期格式标准化为 YYYY-MM-DD"""
    if not date_str:
        return None
    s = date_str.strip()
    formats = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y年%m月%d日", "%Y%m%d"]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # 尝试提取数字
    m = re.search(r"(\d{4})\D?(\d{1,2})\D?(\d{1,2})", s)
    if m:
        try:
            y, mo, d = (int(x) for x in m.groups())
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def delete_invoice_file(file_path: str) -> bool:
    """
    删除发票文件。

    :param file_path: 文件相对或绝对路径
    :return: 是否删除成功
    """
    if not file_path:
        return False
    p = Path(file_path)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    if not p.exists():
        logger.warning(f"待删除文件不存在: {p}")
        return False
    try:
        p.unlink()
        logger.info(f"已删除文件: {p}")
        return True
    except OSError as e:
        logger.error(f"删除文件失败: {p}, error={e}")
        return False
