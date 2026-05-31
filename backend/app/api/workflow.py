"""月度整理流程API

串联 邮件拉取 -> 发票识别 -> 自动分类 -> 文件归档 四个步骤。

设计:
- ProcessingTask 表持久化任务记录(开始/结束时间, 状态, 错误日志摘要, 影响的发票数)
- 实时状态(进度/当前步骤/各步骤详情) 维护在模块级 _STATE 字典中, 接口查询时优先取内存,
  内存不存在则从 DB 还原(error_log 字段中持久化了 JSON 形式的步骤摘要)
- 后台执行通过 asyncio.create_task() 启动, 不阻塞请求
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, require_role
from app.models.email_config import EmailConfig
from app.models.invoice import Invoice
from app.models.processing_task import ProcessingTask
from app.models.user import User
from app.schemas.workflow import (
    WorkflowHistoryItem,
    WorkflowHistoryPage,
    WorkflowStartRequest,
    WorkflowStartResponse,
    WorkflowStatus,
    WorkflowStepDetail,
)
from app.services.email_fetcher import EmailFetcherService
from app.services.file_organizer import organize_by_invoice_date
from app.services.invoice_classifier import batch_classify
from app.services.invoice_recognition import recognize_invoice

logger = logging.getLogger(__name__)

router = APIRouter()

OPERATOR_ROLES = ["admin", "operator", "manager", "user"]
ADMIN_ROLES = ["admin"]


# ---------- 内存状态 ----------
class _WorkflowRuntime:
    """单个流程的运行时状态"""

    def __init__(self, task_id: int, options: WorkflowStartRequest, user_id: Optional[int]):
        self.task_id = task_id
        self.options = options
        self.user_id = user_id
        self.status: str = "processing"
        self.current_step: str = ""
        self.progress: int = 0
        self.invoice_count: int = 0
        self.error_log: Optional[str] = None
        self.started_at: Optional[datetime] = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.cancelled: bool = False
        self.task: Optional[asyncio.Task] = None

        # 4 个步骤(按 options 决定是否参与)
        self.steps: List[Dict[str, Any]] = []
        for key, label in [
            ("email_fetch", "邮件拉取"),
            ("recognize", "AI识别发票"),
            ("classify", "自动分类"),
            ("organize", "文件归档"),
        ]:
            enabled = bool(getattr(options, key))
            self.steps.append(
                {
                    "step": label,
                    "key": key,
                    "status": "pending" if enabled else "skipped",
                    "result": None,
                    "error": None,
                    "started_at": None,
                    "completed_at": None,
                }
            )

    @property
    def active_step_count(self) -> int:
        return sum(1 for s in self.steps if s["status"] != "skipped")

    @property
    def completed_step_count(self) -> int:
        return sum(1 for s in self.steps if s["status"] in ("completed", "failed"))

    def update_progress(self) -> None:
        total = self.active_step_count or 1
        done = sum(1 for s in self.steps if s["status"] == "completed")
        self.progress = int(done * 100 / total)

    def begin_step(self, key: str) -> Optional[Dict[str, Any]]:
        for s in self.steps:
            if s["key"] == key and s["status"] != "skipped":
                s["status"] = "processing"
                s["started_at"] = datetime.utcnow()
                self.current_step = s["step"]
                return s
        return None

    def finish_step(
        self,
        key: str,
        ok: bool,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        for s in self.steps:
            if s["key"] == key and s["status"] == "processing":
                s["status"] = "completed" if ok else "failed"
                s["completed_at"] = datetime.utcnow()
                s["result"] = result
                s["error"] = error
                break
        self.update_progress()

    def to_status(self) -> WorkflowStatus:
        return WorkflowStatus(
            task_id=self.task_id,
            status=self.status,
            current_step=self.current_step,
            progress=self.progress,
            steps_detail=[
                WorkflowStepDetail(
                    step=s["step"],
                    key=s["key"],
                    status=s["status"],
                    result=s["result"],
                    error=s["error"],
                    started_at=s["started_at"],
                    completed_at=s["completed_at"],
                )
                for s in self.steps
            ],
            started_at=self.started_at,
            completed_at=self.completed_at,
            error_log=self.error_log,
            invoice_count=self.invoice_count,
        )

    def to_persist_payload(self) -> str:
        """将步骤汇总序列化为 JSON 持久化到 ProcessingTask.error_log"""
        return json.dumps(
            {
                "current_step": self.current_step,
                "progress": self.progress,
                "steps": [
                    {
                        "step": s["step"],
                        "key": s["key"],
                        "status": s["status"],
                        "result": s["result"],
                        "error": s["error"],
                        "started_at": s["started_at"].isoformat() if s["started_at"] else None,
                        "completed_at": s["completed_at"].isoformat() if s["completed_at"] else None,
                    }
                    for s in self.steps
                ],
                "error_log": self.error_log,
            },
            ensure_ascii=False,
        )


_STATE: Dict[int, _WorkflowRuntime] = {}


# ---------- 步骤实现 ----------
def _do_email_fetch_sync(user_id: Optional[int]) -> Dict[str, Any]:
    """遍历活跃邮箱配置, 依次拉取(同步, 在线程中调用)"""
    db: Session = SessionLocal()
    summary = {"configs": 0, "checked": 0, "new_invoices": 0, "errors": []}
    try:
        configs = db.query(EmailConfig).filter(EmailConfig.is_active.is_(True)).all()
        summary["configs"] = len(configs)
        for cfg in configs:
            try:
                result = EmailFetcherService._do_fetch(cfg.id)
                summary["checked"] += int(result.get("total_emails_checked", 0))
                summary["new_invoices"] += int(result.get("new_invoices_found", 0))
                if result.get("errors"):
                    summary["errors"].extend(result["errors"])
            except Exception as exc:  # pragma: no cover
                logger.exception(f"邮箱拉取异常 config_id={cfg.id}")
                summary["errors"].append(f"config={cfg.id}: {exc}")
    finally:
        db.close()
    return summary


async def _step_email_fetch(rt: _WorkflowRuntime) -> None:
    rt.begin_step("email_fetch")
    try:
        summary = await asyncio.to_thread(_do_email_fetch_sync, rt.user_id)
        text = (
            f"扫描 {summary['configs']} 个邮箱, "
            f"检查 {summary['checked']} 封, 入库 {summary['new_invoices']} 张发票"
        )
        rt.invoice_count += int(summary["new_invoices"])
        ok = not summary["errors"]
        rt.finish_step(
            "email_fetch",
            ok=ok,
            result=text,
            error="; ".join(summary["errors"])[:500] if summary["errors"] else None,
        )
    except Exception as exc:
        logger.exception("email_fetch 步骤异常")
        rt.finish_step("email_fetch", ok=False, error=str(exc))


async def _step_recognize(rt: _WorkflowRuntime) -> None:
    rt.begin_step("recognize")
    db: Session = SessionLocal()
    success = 0
    failed = 0
    errors: List[str] = []
    try:
        pendings = db.query(Invoice).filter(Invoice.status == "pending").all()
        total = len(pendings)
        for idx, inv in enumerate(pendings, 1):
            if rt.cancelled:
                raise asyncio.CancelledError()
            if not inv.file_path or not os.path.exists(inv.file_path):
                inv.status = "error"
                failed += 1
                errors.append(f"invoice {inv.id}: 文件不存在")
                continue
            try:
                res = await recognize_invoice(inv.file_path)
                if res.get("success") and res.get("data"):
                    data = res["data"]
                    inv.invoice_no = data.get("invoice_no") or inv.invoice_no
                    inv.invoice_date = data.get("invoice_date") or inv.invoice_date
                    inv.seller_name = data.get("seller_name") or inv.seller_name
                    inv.buyer_name = data.get("buyer_name") or inv.buyer_name
                    if data.get("amount") is not None:
                        inv.amount = float(data["amount"])
                    if data.get("tax") is not None:
                        inv.tax = float(data["tax"])
                    if data.get("total") is not None:
                        inv.total = float(data["total"])
                    if data.get("items"):
                        inv.items = str(data["items"])
                    inv.status = "recognized"
                    inv.recognized_at = datetime.utcnow()
                    success += 1
                else:
                    inv.status = "error"
                    failed += 1
                    errors.append(f"invoice {inv.id}: {res.get('error')}")
            except Exception as exc:
                inv.status = "error"
                failed += 1
                errors.append(f"invoice {inv.id}: {exc}")
            db.commit()
            # 实时进度: 当前步骤内部进度叠加
            inner_progress = int(idx * 100 / max(total, 1))
            base = sum(1 for s in rt.steps if s["status"] == "completed") * 100
            rt.progress = int((base + inner_progress) / max(rt.active_step_count, 1))

        rt.invoice_count += success
        text = f"待识别 {total} 张, 成功 {success}, 失败 {failed}"
        ok = failed == 0
        rt.finish_step(
            "recognize",
            ok=ok,
            result=text,
            error="; ".join(errors[:5])[:500] if errors else None,
        )
    except asyncio.CancelledError:
        rt.finish_step("recognize", ok=False, error="任务已取消")
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("recognize 步骤异常")
        rt.finish_step("recognize", ok=False, error=str(exc))
    finally:
        db.close()


def _do_classify_sync() -> Dict[str, Any]:
    """对已识别但未分类的发票执行批量分类"""
    db: Session = SessionLocal()
    try:
        # 找出已识别且未分类的发票ID
        rows = (
            db.query(Invoice.id)
            .filter(Invoice.status.in_(["recognized", "verified"]))
            .filter((Invoice.category.is_(None)) | (Invoice.category == ""))
            .all()
        )
        ids = [r[0] for r in rows]
        if not ids:
            return {"total": 0, "updated": 0, "skipped": 0}
        return batch_classify(db, invoice_ids=ids)
    finally:
        db.close()


async def _step_classify(rt: _WorkflowRuntime) -> None:
    rt.begin_step("classify")
    try:
        res = await asyncio.to_thread(_do_classify_sync)
        text = f"待分类 {res['total']} 张, 更新 {res['updated']}, 跳过 {res['skipped']}"
        rt.finish_step("classify", ok=True, result=text)
    except Exception as exc:
        logger.exception("classify 步骤异常")
        rt.finish_step("classify", ok=False, error=str(exc))


def _do_organize_sync() -> Dict[str, Any]:
    """按开票日期重新归档已识别的发票文件"""
    db: Session = SessionLocal()
    moved = 0
    skipped = 0
    errors: List[str] = []
    try:
        rows = (
            db.query(Invoice)
            .filter(Invoice.invoice_date.isnot(None))
            .filter(Invoice.invoice_date != "")
            .filter(Invoice.file_path.isnot(None))
            .all()
        )
        for inv in rows:
            try:
                new_path = organize_by_invoice_date(inv.file_path, inv.invoice_date)
                if new_path and new_path != inv.file_path:
                    inv.file_path = new_path
                    moved += 1
                else:
                    skipped += 1
            except Exception as exc:
                errors.append(f"invoice {inv.id}: {exc}")
        if moved:
            db.commit()
    finally:
        db.close()
    return {"moved": moved, "skipped": skipped, "errors": errors}


async def _step_organize(rt: _WorkflowRuntime) -> None:
    rt.begin_step("organize")
    try:
        res = await asyncio.to_thread(_do_organize_sync)
        text = f"已归档 {res['moved']} 张, 跳过 {res['skipped']}"
        rt.finish_step(
            "organize",
            ok=not res["errors"],
            result=text,
            error="; ".join(res["errors"][:5])[:500] if res["errors"] else None,
        )
    except Exception as exc:
        logger.exception("organize 步骤异常")
        rt.finish_step("organize", ok=False, error=str(exc))


# ---------- 流程编排 ----------
def _persist(rt: _WorkflowRuntime) -> None:
    """同步回写 ProcessingTask 表"""
    db: Session = SessionLocal()
    try:
        task = db.query(ProcessingTask).filter(ProcessingTask.id == rt.task_id).first()
        if not task:
            return
        task.status = rt.status
        task.started_at = rt.started_at
        task.completed_at = rt.completed_at
        task.invoice_count = rt.invoice_count
        task.error_log = rt.to_persist_payload()
        db.commit()
    except Exception as exc:
        logger.error(f"持久化任务失败 task_id={rt.task_id}: {exc}")
        db.rollback()
    finally:
        db.close()


async def _run_workflow(rt: _WorkflowRuntime) -> None:
    """串联执行四个步骤"""
    try:
        if rt.options.email_fetch:
            await _step_email_fetch(rt)
            _persist(rt)
        if rt.cancelled:
            raise asyncio.CancelledError()

        if rt.options.recognize:
            await _step_recognize(rt)
            _persist(rt)
        if rt.cancelled:
            raise asyncio.CancelledError()

        if rt.options.classify:
            await _step_classify(rt)
            _persist(rt)
        if rt.cancelled:
            raise asyncio.CancelledError()

        if rt.options.organize:
            await _step_organize(rt)
            _persist(rt)

        # 汇总状态
        any_failed = any(s["status"] == "failed" for s in rt.steps)
        rt.status = "failed" if any_failed else "completed"
        rt.current_step = "已完成" if not any_failed else "部分失败"
        rt.progress = 100
        rt.completed_at = datetime.utcnow()
        _persist(rt)
    except asyncio.CancelledError:
        rt.status = "cancelled"
        rt.current_step = "已取消"
        rt.completed_at = datetime.utcnow()
        rt.error_log = "任务已被取消"
        _persist(rt)
    except Exception as exc:
        logger.exception(f"workflow 执行异常 task_id={rt.task_id}")
        rt.status = "failed"
        rt.completed_at = datetime.utcnow()
        rt.error_log = str(exc)
        _persist(rt)


# ---------- API ----------
@router.post("/start", response_model=WorkflowStartResponse)
async def start_workflow(
    payload: WorkflowStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(OPERATOR_ROLES)),
):
    """启动月度整理流程"""
    if not any([payload.email_fetch, payload.recognize, payload.classify, payload.organize]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少选择一个流程步骤",
        )

    # 防重: 是否有正在执行的任务
    running = (
        db.query(ProcessingTask)
        .filter(ProcessingTask.task_type == "monthly_workflow")
        .filter(ProcessingTask.status == "processing")
        .first()
    )
    if running and running.id in _STATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"已有流程正在执行(task_id={running.id}), 请等待完成或先取消",
        )

    task = ProcessingTask(
        task_type="monthly_workflow",
        status="processing",
        started_at=datetime.utcnow(),
        invoice_count=0,
        user_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    rt = _WorkflowRuntime(task.id, payload, current_user.id)
    _STATE[task.id] = rt
    rt.task = asyncio.create_task(_run_workflow(rt))

    return WorkflowStartResponse(task_id=task.id, status="processing")


def _restore_status_from_db(task: ProcessingTask) -> WorkflowStatus:
    """从 DB 还原历史任务状态(已完成/失败/取消)"""
    steps_detail: List[WorkflowStepDetail] = []
    current_step = ""
    progress = 100 if task.status in ("completed", "failed", "cancelled") else 0
    error_log: Optional[str] = task.error_log
    payload: Dict[str, Any] = {}
    if task.error_log:
        try:
            payload = json.loads(task.error_log)
        except (ValueError, TypeError):
            payload = {}
    if isinstance(payload, dict) and payload.get("steps"):
        for s in payload["steps"]:
            steps_detail.append(
                WorkflowStepDetail(
                    step=s.get("step", ""),
                    key=s.get("key", ""),
                    status=s.get("status", "pending"),
                    result=s.get("result"),
                    error=s.get("error"),
                    started_at=_parse_dt(s.get("started_at")),
                    completed_at=_parse_dt(s.get("completed_at")),
                )
            )
        current_step = payload.get("current_step", "") or current_step
        progress = int(payload.get("progress") or progress)
        error_log = payload.get("error_log") or error_log

    return WorkflowStatus(
        task_id=task.id,
        status=task.status,
        current_step=current_step,
        progress=progress,
        steps_detail=steps_detail,
        started_at=task.started_at,
        completed_at=task.completed_at,
        error_log=error_log,
        invoice_count=int(task.invoice_count or 0),
    )


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


@router.get("/status/{task_id}", response_model=WorkflowStatus)
async def get_workflow_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询流程状态(优先从内存读取实时状态)"""
    rt = _STATE.get(task_id)
    if rt is not None:
        return rt.to_status()

    task = db.query(ProcessingTask).filter(ProcessingTask.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: id={task_id}",
        )
    return _restore_status_from_db(task)


@router.get("/history", response_model=WorkflowHistoryPage)
async def get_workflow_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取历史流程记录"""
    base = db.query(ProcessingTask).filter(ProcessingTask.task_type == "monthly_workflow")
    total = base.count()
    rows = (
        base.order_by(ProcessingTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items: List[WorkflowHistoryItem] = []
    for r in rows:
        summary = ""
        if r.error_log:
            try:
                payload = json.loads(r.error_log)
                if isinstance(payload, dict):
                    parts = []
                    for s in payload.get("steps", []):
                        if s.get("status") == "skipped":
                            continue
                        parts.append(f"{s.get('step')}: {s.get('status')}")
                    summary = " · ".join(parts)
            except (ValueError, TypeError):
                summary = (r.error_log or "")[:120]
        items.append(
            WorkflowHistoryItem(
                task_id=r.id,
                status=r.status,
                started_at=r.started_at,
                completed_at=r.completed_at,
                invoice_count=int(r.invoice_count or 0),
                error_log=None,
                summary=summary or None,
            )
        )
    return WorkflowHistoryPage(total=total, page=page, page_size=page_size, items=items)


@router.post("/cancel/{task_id}")
async def cancel_workflow(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ADMIN_ROLES)),
):
    """取消正在执行的流程(仅 admin)"""
    rt = _STATE.get(task_id)
    if rt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在或已完成: id={task_id}",
        )
    if rt.status != "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务当前状态为 {rt.status}, 无法取消",
        )
    rt.cancelled = True
    if rt.task and not rt.task.done():
        rt.task.cancel()
    return {"success": True, "task_id": task_id, "message": "取消请求已发送"}
