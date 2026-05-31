"""
APScheduler定时任务调度器
- 每分钟扫描一次email_configs，根据各自的check_interval_minutes判断是否到期
- 到期则触发EmailFetcherService.fetch_invoices
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import SessionLocal
from app.models.email_config import EmailConfig
from app.services.email_fetcher import EmailFetcherService

logger = logging.getLogger(__name__)

# 单例调度器
_scheduler: Optional[BackgroundScheduler] = None

# 主轮询间隔(分钟)。每分钟检查一次哪些邮箱到期。
SCAN_INTERVAL_MINUTES = 1


def _run_fetch_for_config(config_id: int) -> None:
    """同步包装异步fetch调用"""
    try:
        asyncio.run(EmailFetcherService.fetch_invoices(config_id))
    except Exception as e:
        logger.exception(f"调度任务执行失败 config_id={config_id}: {e}")


def check_email_job() -> None:
    """轮询所有active邮箱，检查是否到期需要拉取"""
    db = SessionLocal()
    try:
        configs = db.query(EmailConfig).filter(EmailConfig.is_active == True).all()  # noqa: E712
        now = datetime.now(timezone.utc)
        triggered = 0
        for cfg in configs:
            interval = cfg.check_interval_minutes or 30
            last_check = cfg.last_check_at
            should_run = False
            if last_check is None:
                should_run = True
            else:
                # 兼容naive datetime
                if last_check.tzinfo is None:
                    last_check = last_check.replace(tzinfo=timezone.utc)
                if now - last_check >= timedelta(minutes=interval):
                    should_run = True
            if should_run:
                logger.info(
                    f"[Scheduler] 触发邮箱拉取: id={cfg.id} email={cfg.email_address}"
                )
                _run_fetch_for_config(cfg.id)
                triggered += 1
        if triggered:
            logger.info(f"[Scheduler] 本轮触发了 {triggered} 个邮箱拉取任务")
    except Exception as e:
        logger.exception(f"[Scheduler] check_email_job执行异常: {e}")
    finally:
        db.close()


def start_scheduler() -> None:
    """启动调度器"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("[Scheduler] 调度器已在运行，跳过启动")
        return
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        check_email_job,
        trigger=IntervalTrigger(minutes=SCAN_INTERVAL_MINUTES),
        id="check_email_job",
        name="邮箱拉取轮询任务",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        f"[Scheduler] 调度器已启动，每{SCAN_INTERVAL_MINUTES}分钟轮询一次"
    )


def stop_scheduler() -> None:
    """停止调度器"""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[Scheduler] 调度器已停止")
    _scheduler = None
