"""
邮件拉取服务
支持IMAP连接、密码加密、附件下载、发票记录创建。
"""
import asyncio
import base64
import email as email_lib
import hashlib
import imaplib
import logging
import os
import re
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.email_config import EmailConfig
from app.models.email_fetch_log import EmailFetchLog
from app.models.email_message import EmailMessage
from app.schemas.email_config import EmailTestRequest

logger = logging.getLogger(__name__)

# ---------- 异步拉取任务进度存储（进程内存，适用于单 worker uvicorn）----------
_progress_store: dict[str, dict] = {}
_progress_lock = threading.Lock()
_PROGRESS_TTL_SECONDS = 60 * 60  # 保留 1 小时后供前端轮询查看结果


def _gc_progress_store() -> None:
    """清理过期的进度记录。"""
    now = time.time()
    with _progress_lock:
        expired = [
            tid for tid, p in _progress_store.items()
            if p.get("finished_at") and now - p["finished_at"] > _PROGRESS_TTL_SECONDS
        ]
        for tid in expired:
            _progress_store.pop(tid, None)


def _set_progress(task_id: str, **kwargs) -> None:
    """原子更新某个任务的进度字段。"""
    if not task_id:
        return
    with _progress_lock:
        data = _progress_store.setdefault(task_id, {})
        data.update(kwargs)


def get_progress(task_id: str) -> Optional[dict]:
    """获取某个任务的进度快照。"""
    with _progress_lock:
        data = _progress_store.get(task_id)
        return dict(data) if data else None


# ---------- 密码加解密 ----------
def _derive_fernet_key() -> bytes:
    """从SECRET_KEY派生32字节base64编码的Fernet密钥"""
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key())


def encrypt_password(plain: str) -> str:
    """加密密码"""
    if plain is None:
        return ""
    token = _fernet.encrypt(plain.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_password(encrypted: str) -> str:
    """解密密码"""
    if not encrypted:
        return ""
    try:
        return _fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as e:
        logger.error(f"密码解密失败: {e}")
        raise ValueError("密码解密失败，请重新配置邮箱密码") from e


# ---------- 工具函数 ----------
_FALLBACK_ENCODINGS = ("utf-8", "gb18030", "gbk", "big5")


def _decode_bytes(raw: bytes, charset: Optional[str] = None) -> str:
    """按声明 charset 优先，再依次尝试常见中文编码解码字节序列。"""
    candidates: list[str] = []
    if charset:
        candidates.append(charset)
    for enc in _FALLBACK_ENCODINGS:
        if enc not in candidates:
            candidates.append(enc)
    for enc in candidates:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", errors="replace")


def _fix_mojibake(text: str) -> str:
    """修正 email 库以 surrogateescape/latin-1 预解码导致的伪字符串。

    例如：UTF-8 字节 0xE5 0xA2 0x9E 被 latin-1 解码成 'å¢\x9e'，
    这里再用 latin-1 编回字节、按 UTF-8/GBK 重新解码即可还原。
    """
    if not text or all(ord(c) < 128 for c in text):
        return text
    try:
        raw = text.encode("latin-1", errors="strict")
    except UnicodeEncodeError:
        # 含非 latin-1 字符，说明已是正常 Unicode，无需修复
        return text
    for enc in _FALLBACK_ENCODINGS:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return text


def _decode_str(value) -> str:
    """解码邮件中可能编码过的字符串(主题、文件名等)

    覆盖三类情况：
    1) bytes：按候选编码探测解码
    2) RFC2047 编码头(=?utf-8?B?...?=)：decode_header 已切分为 bytes+charset
    3) 裸 8bit 字节头：email 库会以 latin-1 把字节预解码成伪字符串，需反向修正
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return _decode_bytes(value)
    parts = decode_header(value)
    out: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            out.append(_decode_bytes(part, charset))
        else:
            out.append(_fix_mojibake(part))
    return "".join(out)


_INVOICE_KEYWORDS = ("发票", "invoice", "fapiao")


def _parse_email_date(date_str: str) -> Optional[datetime]:
    """解析邮件 Date 头为 datetime（带时区，失败返回 None）"""
    if not date_str:
        return None
    try:
        from email.utils import parsedate_to_datetime

        dt = parsedate_to_datetime(date_str)
        return dt
    except Exception:
        return None


def _is_invoice_attachment(filename: str) -> bool:
    """判断附件是否是发票PDF"""
    if not filename:
        return False
    lower = filename.lower()
    if not lower.endswith(".pdf"):
        return False
    # 命中任一发票关键词，或仅是PDF附件也接受
    if any(kw in lower for kw in _INVOICE_KEYWORDS):
        return True
    # 默认所有PDF附件都视为潜在发票
    return True


def _safe_filename(name: str) -> str:
    """清洗文件名，去除非法字符"""
    name = name.strip().replace("\\", "_").replace("/", "_")
    name = re.sub(r"[\r\n\t]", "", name)
    name = re.sub(r"[^\w\u4e00-\u9fa5\.\-_\(\) ]", "_", name)
    return name[:200] or "attachment.pdf"


# ---------- 核心服务 ----------
class EmailFetcherService:
    """邮箱拉取服务"""

    @staticmethod
    def _connect(
        imap_server: str,
        port: int,
        email_address: str,
        password: str,
        use_ssl: bool = True,
        timeout: int = 30,
    ) -> imaplib.IMAP4:
        """建立IMAP连接并登录"""
        if use_ssl:
            client = imaplib.IMAP4_SSL(imap_server, port, timeout=timeout)
        else:
            client = imaplib.IMAP4(imap_server, port, timeout=timeout)
        client.login(email_address, password)
        return client

    @staticmethod
    async def test_connection(config: EmailTestRequest) -> tuple[bool, str]:
        """测试邮箱连接

        返回 (success, message)
        """

        def _do_test() -> tuple[bool, str]:
            try:
                client = EmailFetcherService._connect(
                    config.imap_server,
                    config.port,
                    config.email_address,
                    config.password,
                    config.use_ssl,
                )
                try:
                    client.select("INBOX", readonly=True)
                finally:
                    try:
                        client.logout()
                    except Exception:
                        pass
                return True, "连接成功"
            except imaplib.IMAP4.error as e:
                return False, f"IMAP登录失败: {e}"
            except OSError as e:
                return False, f"网络连接失败: {e}"
            except Exception as e:  # pragma: no cover - 兜底
                return False, f"连接异常: {e}"

        return await asyncio.to_thread(_do_test)

    @staticmethod
    def _save_attachment(part, target_dir: str) -> Optional[str]:
        """保存附件到目录，返回文件完整路径"""
        raw_name = part.get_filename()
        filename = _decode_str(raw_name) if raw_name else ""
        if not _is_invoice_attachment(filename):
            return None

        os.makedirs(target_dir, exist_ok=True)
        safe = _safe_filename(filename)
        # 避免重名
        full_path = os.path.join(target_dir, safe)
        idx = 1
        base, ext = os.path.splitext(safe)
        while os.path.exists(full_path):
            full_path = os.path.join(target_dir, f"{base}_{idx}{ext}")
            idx += 1

        payload = part.get_payload(decode=True)
        if payload is None:
            return None
        with open(full_path, "wb") as f:
            f.write(payload)
        return full_path

    @staticmethod
    def _process_message(
        msg: email_lib.message.Message, target_dir: str
    ) -> list[tuple[str, str]]:
        """遍历邮件附件，下载发票PDF。返回 [(file_path, original_filename), ...]"""
        saved: list[tuple[str, str]] = []
        for part in msg.walk():
            if part.is_multipart():
                continue
            disposition = str(part.get("Content-Disposition") or "")
            content_type = part.get_content_type()
            # 必须是附件或PDF类型
            if "attachment" not in disposition.lower() and content_type != "application/pdf":
                continue
            raw_name = part.get_filename()
            original_name = _decode_str(raw_name) if raw_name else ""
            saved_path = EmailFetcherService._save_attachment(part, target_dir)
            if saved_path:
                saved.append((saved_path, original_name))
        return saved

    @staticmethod
    def _build_search_criteria(
        last_check_at: Optional[datetime],
        filters: Optional[dict] = None,
    ) -> tuple[str, Optional[str]]:
        """构造IMAP搜索条件

        返回 (criteria_str, keyword_post_filter)
        - criteria_str: IMAP UID SEARCH 所需的条件字符串
        - keyword_post_filter: 非ASCII关键字需要后置Python过滤（IMAP CHARSET 兑现差异较大）
        """
        filters = filters or {}
        parts: list[str] = []

        # 日期范围
        date_from = (filters.get("date_from") or "").strip() if filters.get("date_from") else ""
        date_to = (filters.get("date_to") or "").strip() if filters.get("date_to") else ""
        since_dt: Optional[datetime] = None
        if date_from:
            try:
                since_dt = datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                since_dt = None
        if since_dt is None:
            # 保持原逻辑：未指定时以当天作为 SINCE
            since_dt = datetime.now()
        parts.append(f'SINCE {since_dt.strftime("%d-%b-%Y")}')

        if date_to:
            try:
                # IMAP BEFORE 不包含当天，需+1天
                before_dt = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
                parts.append(f'BEFORE {before_dt.strftime("%d-%b-%Y")}')
            except ValueError:
                pass

        # 发件人
        sender = (filters.get("sender") or "").strip()
        if sender:
            sender_safe = sender.replace('"', "")
            parts.append(f'FROM "{sender_safe}"')

        # 主题关键字：ASCII 走 IMAP SEARCH；非ASCII（如中文）后置过滤
        keyword = (filters.get("keyword") or "").strip()
        keyword_post: Optional[str] = None
        if keyword:
            try:
                keyword.encode("ascii")
                kw_safe = keyword.replace('"', "")
                parts.append(f'SUBJECT "{kw_safe}"')
            except UnicodeEncodeError:
                keyword_post = keyword

        criteria = " ".join(parts) if parts else "ALL"
        return criteria, keyword_post

    @staticmethod
    def _do_fetch(config_id: int, filters: Optional[dict] = None, task_id: Optional[str] = None) -> dict:
        """同步执行邮件拉取(在线程中调用)

        :param filters: 可选过滤条件 keyword/date_from/date_to/sender/has_attachment
        :param task_id: 可选任务标识，传入后会同步上报进度
        """
        filters = filters or {}
        db: Session = SessionLocal()
        result = {
            "config_id": config_id,
            "total_emails_checked": 0,
            "new_invoices_found": 0,
            "errors": [],
            "status": "success",
        }
        _set_progress(
            task_id,
            status="running",
            stage="connecting",
            config_id=config_id,
            total=0,
            processed=0,
            new_invoices_found=0,
            errors=[],
        )
        client: Optional[imaplib.IMAP4] = None
        try:
            config = db.query(EmailConfig).filter(EmailConfig.id == config_id).first()
            if not config:
                raise ValueError(f"邮箱配置不存在: id={config_id}")

            password = decrypt_password(config.password_encrypted)
            use_ssl = getattr(config, "use_ssl", True)
            if use_ssl is None:
                use_ssl = True

            client = EmailFetcherService._connect(
                config.imap_server,
                config.port,
                config.email_address,
                password,
                bool(use_ssl),
            )
            client.select("INBOX")
            _set_progress(task_id, stage="searching", email_address=config.email_address)

            # 使用 UID SEARCH 获取稳定的 UID 用于去重。
            # 注意：搜索条件字符串不能加外层括号，imap.exmail.qq.com 等
            # 部分服务器会将 "(SINCE ... BEFORE ...)" 整个视为不可识别的单个
            # token 而退化为 ALL，导致日期过滤完全失效。
            criteria, keyword_post = EmailFetcherService._build_search_criteria(
                config.last_check_at, filters
            )
            typ, data = client.uid("search", None, criteria)
            if typ != "OK":
                raise RuntimeError(f"邮件搜索失败: {typ}")

            uids = data[0].split() if data and data[0] else []
            result["total_emails_checked"] = len(uids)
            logger.info(
                f"邮箱[{config.email_address}] 命中 {len(uids)} 封邮件 (criteria={criteria})"
            )

            # 查询已处理的UID集合用于去重
            existing_uids = set(
                row[0] for row in db.query(EmailMessage.message_uid).filter(
                    EmailMessage.config_id == config_id,
                    EmailMessage.message_uid.isnot(None),
                ).all()
            )
            new_uids = [uid for uid in uids if uid.decode() not in existing_uids]
            logger.info(
                f"去重后需处理 {len(new_uids)} 封新邮件 (已存在 {len(uids) - len(new_uids)} 封)"
            )
            _set_progress(
                task_id,
                stage="downloading",
                total=len(new_uids),
                total_emails_checked=len(uids),
                skipped_existing=len(uids) - len(new_uids),
            )

            today = datetime.now().strftime("%Y-%m-%d")
            target_dir = os.path.join(settings.EMAIL_TEMP_PATH, today)

            for idx, uid in enumerate(new_uids, start=1):
                try:
                    typ, msg_data = client.uid("fetch", uid, "(RFC822)")
                    if typ != "OK" or not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)
                    subject = _decode_str(msg.get("Subject", ""))
                    sender = _decode_str(msg.get("From", ""))
                    received_at = _parse_email_date(msg.get("Date", ""))
                    # 后置过滤：非ASCII关键字在 Python 侧判断主题包含
                    if keyword_post and keyword_post not in (subject or ""):
                        continue
                    attachments = EmailFetcherService._process_message(msg, target_dir)
                    uid_str = uid.decode()
                    only_with_attachment = bool(filters.get("has_attachment", True))
                    if attachments:
                        for file_path, original_filename in attachments:
                            try:
                                file_size = os.path.getsize(file_path)
                            except OSError:
                                file_size = 0
                            email_msg = EmailMessage(
                                config_id=config_id,
                                message_uid=uid_str,
                                subject=subject[:500] if subject else None,
                                sender=sender[:200] if sender else None,
                                received_at=received_at,
                                attachment_name=(original_filename or os.path.basename(file_path))[:300],
                                attachment_path=file_path,
                                file_size=file_size,
                                is_imported=False,
                                user_id=config.user_id,
                            )
                            db.add(email_msg)
                            result["new_invoices_found"] += 1
                    elif not only_with_attachment:
                        # 开关关闭：保存无PDF附件的邮件，便于用户手动查看正文下载链接
                        # 通过 subject 非空与 attachment_name 为空区分“无附件正常邮件”与“历史UID占位”
                        placeholder_subject = subject[:500] if subject else "(无主题)"
                        email_msg = EmailMessage(
                            config_id=config_id,
                            message_uid=uid_str,
                            subject=placeholder_subject,
                            sender=sender[:200] if sender else None,
                            received_at=received_at,
                            attachment_name=None,
                            attachment_path=None,
                            file_size=0,
                            is_imported=False,
                            user_id=config.user_id,
                        )
                        db.add(email_msg)
                        result["new_invoices_found"] += 1
                except Exception as item_err:
                    msg_err = f"邮件处理失败 uid={uid!r}: {item_err}"
                    logger.warning(msg_err)
                    result["errors"].append(msg_err)
                finally:
                    # 每处理一封邮件后上报进度，供前端展示进度条
                    _set_progress(
                        task_id,
                        processed=idx,
                        new_invoices_found=result["new_invoices_found"],
                    )

            config.last_check_at = datetime.now(timezone.utc)
            db.commit()

            if result["errors"]:
                result["status"] = "partial"
        except Exception as e:
            db.rollback()
            logger.exception(f"邮件拉取失败 config_id={config_id}")
            result["status"] = "failed"
            result["errors"].append(str(e))
        finally:
            if client is not None:
                try:
                    client.logout()
                except Exception:
                    pass

            # 写入拉取日志
            try:
                cfg = db.query(EmailConfig).filter(EmailConfig.id == config_id).first()
                log = EmailFetchLog(
                    config_id=config_id,
                    email_address=cfg.email_address if cfg else None,
                    total_emails_checked=result["total_emails_checked"],
                    new_invoices_count=result["new_invoices_found"],
                    status=result["status"],
                    error_message="; ".join(result["errors"])[:1000] if result["errors"] else None,
                )
                db.add(log)
                db.commit()
            except Exception as log_err:
                logger.error(f"写入拉取日志失败: {log_err}")
                db.rollback()
            finally:
                db.close()

            # 任务结束，刷新进度为终态
            _set_progress(
                task_id,
                status=result["status"],
                stage="finished",
                total_emails_checked=result["total_emails_checked"],
                new_invoices_found=result["new_invoices_found"],
                errors=result["errors"],
                finished_at=time.time(),
                result=result,
            )
            _gc_progress_store()
        return result

    @staticmethod
    async def fetch_invoices(config_id: int, filters: Optional[dict] = None) -> dict:
        """异步触发邮件拉取（同步等待完成，仅用于后台定时任务）"""
        return await asyncio.to_thread(EmailFetcherService._do_fetch, config_id, filters)

    @staticmethod
    def start_async_fetch(config_id: int, filters: Optional[dict] = None) -> str:
        """启动后台线程执行拉取，立即返回 task_id。

        前端可通过 GET /api/email/fetch-progress/{task_id} 轮询进度。
        """
        task_id = uuid.uuid4().hex
        _set_progress(
            task_id,
            status="running",
            stage="queued",
            config_id=config_id,
            total=0,
            processed=0,
            new_invoices_found=0,
            errors=[],
            started_at=time.time(),
        )

        def _runner() -> None:
            try:
                EmailFetcherService._do_fetch(config_id, filters, task_id=task_id)
            except Exception as exc:  # pragma: no cover - 兼容意外错误
                logger.exception(f"异步拉取崩溃 task_id={task_id}")
                _set_progress(
                    task_id,
                    status="failed",
                    stage="finished",
                    errors=[str(exc)],
                    finished_at=time.time(),
                )

        thread = threading.Thread(target=_runner, name=f"email-fetch-{task_id[:8]}", daemon=True)
        thread.start()
        return task_id


# 模块级便捷接口
email_fetcher_service = EmailFetcherService()
