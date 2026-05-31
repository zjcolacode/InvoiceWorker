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
from datetime import datetime, timezone
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
def _decode_str(value) -> str:
    """解码邮件中可能编码过的字符串(主题、文件名等)"""
    if value is None:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return value.decode("latin-1", errors="replace")
    parts = decode_header(value)
    out = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                out.append(part.decode(charset or "utf-8", errors="replace"))
            except Exception:
                out.append(part.decode("latin-1", errors="replace"))
        else:
            out.append(part)
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
    def _build_search_criteria(last_check_at: Optional[datetime]) -> str:
        """构造IMAP搜索条件"""
        if last_check_at is None:
            return "UNSEEN"
        # 使用SINCE检索last_check_at之后的邮件 (IMAP仅按日期粒度)
        since_str = last_check_at.strftime("%d-%b-%Y")
        return f'(SINCE "{since_str}")'

    @staticmethod
    def _do_fetch(config_id: int) -> dict:
        """同步执行邮件拉取(在线程中调用)"""
        db: Session = SessionLocal()
        result = {
            "config_id": config_id,
            "total_emails_checked": 0,
            "new_invoices_found": 0,
            "errors": [],
            "status": "success",
        }
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

            # 使用UID SEARCH代替普通SEARCH，获取稳定的UID用于去重
            criteria = EmailFetcherService._build_search_criteria(config.last_check_at)
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

            today = datetime.now().strftime("%Y-%m-%d")
            target_dir = os.path.join(settings.EMAIL_TEMP_PATH, today)

            for uid in new_uids:
                try:
                    typ, msg_data = client.uid("fetch", uid, "(RFC822)")
                    if typ != "OK" or not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = email_lib.message_from_bytes(raw)
                    subject = _decode_str(msg.get("Subject", ""))
                    sender = _decode_str(msg.get("From", ""))
                    received_at = _parse_email_date(msg.get("Date", ""))
                    attachments = EmailFetcherService._process_message(msg, target_dir)
                    uid_str = uid.decode()
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
                except Exception as item_err:
                    msg_err = f"邮件处理失败 uid={uid!r}: {item_err}"
                    logger.warning(msg_err)
                    result["errors"].append(msg_err)

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
        return result

    @staticmethod
    async def fetch_invoices(config_id: int) -> dict:
        """异步触发邮件拉取"""
        return await asyncio.to_thread(EmailFetcherService._do_fetch, config_id)


# 模块级便捷接口
email_fetcher_service = EmailFetcherService()
