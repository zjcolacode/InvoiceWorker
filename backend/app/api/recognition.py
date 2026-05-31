"""
发票识别API路由
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.category import Category
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.invoice import (
    BatchRecognitionRequest,
    BatchRecognitionResponse,
    RecognitionResult,
)
from app.services.invoice_recognition import recognize_invoice, batch_recognize

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_active_category_names(db: Session) -> list[str]:
    """获取数据库中启用状态的分类名称列表"""
    rows = (
        db.query(Category.name)
        .filter(Category.is_active == True)  # noqa: E712
        .all()
    )
    return [r[0] for r in rows if r[0]]


def _normalize_category(value: str | None, allowed: list[str]) -> str:
    """将模型返回的分类值规范化为允许列表中的名称，否则返回“其他”"""
    if value and isinstance(value, str):
        v = value.strip()
        if v in allowed:
            return v
    return "其他"


@router.post("/recognize/{invoice_id}", response_model=RecognitionResult)
async def recognize_single_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    识别指定发票

    - 需要认证(operator以上)
    - 从数据库获取发票记录的file_path
    - 调用识别服务
    - 将结果更新到invoice记录
    """
    # 查询发票记录
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"发票记录不存在: id={invoice_id}",
        )

    # 检查文件路径
    if not invoice.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该发票记录没有关联的文件路径",
        )

    logger.info(f"开始识别发票 id={invoice_id}, file={invoice.file_path}")

    # 获取启用的分类名称列表，供模型同步推理分类
    category_names = _get_active_category_names(db)

    # 调用识别服务
    result = await recognize_invoice(invoice.file_path, categories=category_names)

    # 如果识别成功，更新数据库记录
    if result["success"] and result["data"]:
        data = result["data"]
        invoice.invoice_no = data.get("invoice_no")
        invoice.invoice_date = data.get("invoice_date")
        invoice.seller_name = data.get("seller_name")
        invoice.buyer_name = data.get("buyer_name")
        invoice.amount = data.get("amount")
        invoice.tax = data.get("tax")
        invoice.total = data.get("total")
        invoice.items = data.get("items")
        # 校验模型返回的分类，不在启用分类列表中的统一设为“其他”
        invoice.category = _normalize_category(data.get("category"), category_names)
        invoice.status = "recognized"
        invoice.recognized_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(invoice)
        logger.info(f"发票识别成功并更新数据库: id={invoice_id}, invoice_no={invoice.invoice_no}")
    else:
        # 识别失败，更新状态为error
        invoice.status = "error"
        db.commit()
        logger.warning(f"发票识别失败: id={invoice_id}, error={result.get('error')}")

    return RecognitionResult(
        success=result["success"],
        data=result.get("data"),
        error=result.get("error"),
    )


@router.post("/batch", response_model=BatchRecognitionResponse)
async def batch_recognize_invoices(
    request: BatchRecognitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量识别发票

    - 接收 invoice_ids 列表
    - 逐个识别并更新数据库
    - 返回处理结果摘要
    """
    if not request.invoice_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invoice_ids不能为空",
        )

    # 查询所有发票记录
    invoices = (
        db.query(Invoice)
        .filter(Invoice.id.in_(request.invoice_ids))
        .all()
    )

    if not invoices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到任何匹配的发票记录",
        )

    # 构建id到invoice的映射
    invoice_map = {inv.id: inv for inv in invoices}

    # 收集有效的文件路径
    file_paths = []
    valid_ids = []
    results = []

    for inv_id in request.invoice_ids:
        inv = invoice_map.get(inv_id)
        if not inv:
            results.append(RecognitionResult(
                success=False,
                data=None,
                error=f"发票记录不存在: id={inv_id}",
            ))
        elif not inv.file_path:
            results.append(RecognitionResult(
                success=False,
                data=None,
                error=f"发票记录无文件路径: id={inv_id}",
            ))
        else:
            file_paths.append(inv.file_path)
            valid_ids.append(inv_id)

    # 获取启用的分类名称列表，供模型同步推理分类
    category_names = _get_active_category_names(db)

    # 批量识别
    if file_paths:
        logger.info(f"开始批量识别 {len(file_paths)} 张发票")
        recognition_results = await batch_recognize(file_paths, categories=category_names)

        for inv_id, rec_result in zip(valid_ids, recognition_results):
            inv = invoice_map[inv_id]

            if rec_result["success"] and rec_result["data"]:
                data = rec_result["data"]
                inv.invoice_no = data.get("invoice_no")
                inv.invoice_date = data.get("invoice_date")
                inv.seller_name = data.get("seller_name")
                inv.buyer_name = data.get("buyer_name")
                inv.amount = data.get("amount")
                inv.tax = data.get("tax")
                inv.total = data.get("total")
                inv.items = data.get("items")
                # 校验模型返回的分类，不在启用分类列表中的统一设为“其他”
                inv.category = _normalize_category(data.get("category"), category_names)
                inv.status = "recognized"
                inv.recognized_at = datetime.now(timezone.utc)
            else:
                inv.status = "error"

            results.append(RecognitionResult(
                success=rec_result["success"],
                data=rec_result.get("data"),
                error=rec_result.get("error"),
            ))

        db.commit()

    # 统计结果
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    logger.info(f"批量识别完成: 总数={len(results)}, 成功={success_count}, 失败={failed_count}")

    return BatchRecognitionResponse(
        total=len(results),
        success_count=success_count,
        failed_count=failed_count,
        results=results,
    )
