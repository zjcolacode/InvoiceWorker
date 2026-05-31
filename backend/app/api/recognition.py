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

# 允许触发识别的源状态（占位前的状态机白名单）
_RECOGNIZABLE_STATUSES = ("pending", "error", "failed")


def _is_admin(user: User) -> bool:
    return (user.role or "").lower() == "admin"


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


def _restore_recognizing(db: Session, ids: list[int]) -> None:
    """异常兜底：将仍处于 recognizing 的发票恢复为 pending"""
    if not ids:
        return
    try:
        db.query(Invoice).filter(
            Invoice.id.in_(ids),
            Invoice.status == "recognizing",
        ).update({"status": "pending"}, synchronize_session=False)
        db.commit()
    except Exception:  # pragma: no cover
        logger.exception("恢复 recognizing -> pending 失败")
        db.rollback()


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

    # 用户隔离：非 admin 只能识别自己的发票
    if not _is_admin(current_user) and (
        invoice.user_id is None or invoice.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权操作他人的发票",
        )

    # 检查文件路径
    if not invoice.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该发票记录没有关联的文件路径",
        )

    # 状态机检查：正在被其他流程处理时直接拒绝
    if invoice.status == "recognizing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该发票正在被其他流程识别中，请稍后再试",
        )

    # 占位锁：标记为 recognizing 并立即 commit，防止并发触发
    invoice.status = "recognizing"
    db.commit()
    locked_id = invoice.id

    logger.info(f"开始识别发票 id={invoice_id}, file={invoice.file_path}")

    # 获取启用的分类名称列表，供模型同步推理分类
    category_names = _get_active_category_names(db)

    try:
        # 调用识别服务
        result = await recognize_invoice(invoice.file_path, categories=category_names)
    except Exception as exc:
        # 识别异常，回退占位锁为 pending 后向上抛
        logger.exception(f"发票识别异常: id={invoice_id}")
        _restore_recognizing(db, [locked_id])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发票识别异常: {exc}",
        ) from exc

    # 重新获取最新的 invoice 实例（commit 后可能需要 refresh）
    db.refresh(invoice)

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
    - 仅处理 pending / error / failed 状态的发票，其他状态（如 recognizing / recognized）跳过
    - 开始前将待处理发票批量标记为 recognizing 作为占位锁
    - 逐个识别并更新数据库
    - 返回处理结果摘要（含被跳过的数量）
    """
    if not request.invoice_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invoice_ids不能为空",
        )

    requested_ids = list(dict.fromkeys(request.invoice_ids))  # 去重保序
    requested_count = len(requested_ids)

    # 查询所有请求的发票记录（先做用户隔离）
    invoice_query = db.query(Invoice).filter(Invoice.id.in_(requested_ids))
    if not _is_admin(current_user):
        invoice_query = invoice_query.filter(Invoice.user_id == current_user.id)
    all_owned_invoices = invoice_query.all()

    if not all_owned_invoices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到任何可识别的发票记录（如识别他人的发票请联系管理员）",
        )

    # 仅筛选状态在白名单内的发票（pending / error / failed）
    processable = [
        inv for inv in all_owned_invoices if inv.status in _RECOGNIZABLE_STATUSES
    ]

    # 计算被跳过的数量（包括状态不符或权限不足/不存在的）
    skipped_count = requested_count - len(processable)

    # 占位锁：立即将待处理发票标记为 recognizing 并 commit
    locked_ids = [inv.id for inv in processable]
    for inv in processable:
        inv.status = "recognizing"
    if locked_ids:
        db.commit()

    # 构建 id -> invoice 映射
    invoice_map = {inv.id: inv for inv in processable}

    # 收集有效的文件路径
    file_paths: list[str] = []
    valid_ids: list[int] = []
    results: list[RecognitionResult] = []

    for inv_id in requested_ids:
        inv = invoice_map.get(inv_id)
        if not inv:
            # 状态不符或不存在/无权访问 —— 已计入 skipped_count，不再加入 results
            continue
        if not inv.file_path:
            # 无文件路径：恢复 pending 后记为失败
            inv.status = "pending"
            results.append(RecognitionResult(
                success=False,
                data=None,
                error=f"发票记录无文件路径: id={inv_id}",
            ))
        else:
            file_paths.append(inv.file_path)
            valid_ids.append(inv_id)

    # 提交上面对无文件路径行的状态回退
    if any(inv.status == "pending" for inv in processable if not inv.file_path):
        db.commit()

    # 获取启用的分类名称列表，供模型同步推理分类
    category_names = _get_active_category_names(db)

    # 批量识别
    if file_paths:
        logger.info(f"开始批量识别 {len(file_paths)} 张发票")
        try:
            recognition_results = await batch_recognize(file_paths, categories=category_names)
        except Exception as exc:
            # 整体异常：将所有已上锁的发票恢复为 pending
            logger.exception("批量识别接口整体异常")
            _restore_recognizing(db, valid_ids)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"批量识别异常: {exc}",
            ) from exc

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

    # 兜底：以防仍有 recognizing 残留
    _restore_recognizing(db, locked_ids)

    # 统计结果
    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    skipped_message = None
    if skipped_count > 0:
        skipped_message = (
            f"{skipped_count} 张发票正在被其他流程处理或状态不可识别，已跳过"
        )

    logger.info(
        f"批量识别完成: 请求={requested_count}, 处理={len(results)}, "
        f"成功={success_count}, 失败={failed_count}, 跳过={skipped_count}"
    )

    return BatchRecognitionResponse(
        total=len(results),
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        skipped_message=skipped_message,
        results=results,
    )
