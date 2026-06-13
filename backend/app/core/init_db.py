import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


def _ensure_invoice_file_hash_column() -> None:
    """为已有 invoices 表补充 file_hash 列（SQLite 兼容的轻量迁移）。"""
    try:
        with engine.connect() as conn:
            dialect = engine.dialect.name
            if dialect == "sqlite":
                rows = conn.execute(text("PRAGMA table_info(invoices)")).fetchall()
                columns = {row[1] for row in rows}
                if not rows:
                    # invoices 表尚未创建 (会由 create_all 创建) —— 无需迁移
                    return
                if "file_hash" not in columns:
                    conn.execute(text("ALTER TABLE invoices ADD COLUMN file_hash VARCHAR(64)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_invoices_file_hash ON invoices(file_hash)"))
                    conn.commit()
                    logger.info("已为 invoices 表补充 file_hash 列及索引")
            else:
                # 其他数据库：尝试添加列，失败则忽略（表示已存在）
                try:
                    conn.execute(text("ALTER TABLE invoices ADD COLUMN file_hash VARCHAR(64)"))
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"检查/补充 invoices.file_hash 列失败（可忽略）: {e}")


def _ensure_user_menu_permissions_column() -> None:
    """为已有 users 表补充 menu_permissions 列（SQLite 兼容的轻量迁移）。"""
    try:
        with engine.connect() as conn:
            dialect = engine.dialect.name
            if dialect == "sqlite":
                rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
                columns = {row[1] for row in rows}
                if not rows:
                    return
                if "menu_permissions" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN menu_permissions TEXT"))
                    conn.commit()
                    logger.info("已为 users 表补充 menu_permissions 列")
            else:
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN menu_permissions TEXT"))
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"检查/补充 users.menu_permissions 列失败（可忽略）: {e}")


def _ensure_email_messages_uid_column() -> None:
    """为已有 email_messages 表补充 message_uid 列（SQLite 兼容的轻量迁移）。"""
    try:
        with engine.connect() as conn:
            dialect = engine.dialect.name
            if dialect == "sqlite":
                rows = conn.execute(text("PRAGMA table_info(email_messages)")).fetchall()
                if not rows:
                    return
                columns = {row[1] for row in rows}
                if "message_uid" not in columns:
                    conn.execute(text("ALTER TABLE email_messages ADD COLUMN message_uid VARCHAR(100)"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_email_messages_uid ON email_messages(message_uid)"))
                    conn.commit()
                    logger.info("已为 email_messages 表补充 message_uid 列及索引")
            else:
                try:
                    conn.execute(text("ALTER TABLE email_messages ADD COLUMN message_uid VARCHAR(100)"))
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"检查/补充 email_messages.message_uid 列失败（可忽略）: {e}")


def _ensure_invoice_reimbursement_columns() -> None:
    """为已有 invoices 表补充 is_reimbursed 和 reimbursed_at 列（SQLite 兼容的轻量迁移）。"""
    try:
        with engine.connect() as conn:
            dialect = engine.dialect.name
            if dialect == "sqlite":
                rows = conn.execute(text("PRAGMA table_info(invoices)")).fetchall()
                if not rows:
                    return
                columns = {row[1] for row in rows}
                if "is_reimbursed" not in columns:
                    conn.execute(text(
                        "ALTER TABLE invoices ADD COLUMN is_reimbursed BOOLEAN DEFAULT 0 NOT NULL"
                    ))
                    conn.commit()
                    logger.info("已为 invoices 表补充 is_reimbursed 列")
                if "reimbursed_at" not in columns:
                    conn.execute(text(
                        "ALTER TABLE invoices ADD COLUMN reimbursed_at DATETIME"
                    ))
                    conn.commit()
                    logger.info("已为 invoices 表补充 reimbursed_at 列")
            else:
                try:
                    conn.execute(text(
                        "ALTER TABLE invoices ADD COLUMN is_reimbursed BOOLEAN DEFAULT FALSE NOT NULL"
                    ))
                    conn.commit()
                except Exception:
                    pass
                try:
                    conn.execute(text(
                        "ALTER TABLE invoices ADD COLUMN reimbursed_at DATETIME"
                    ))
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"检查/补充 invoices 核销列失败（可忽略）: {e}")


def _ensure_invoice_detail_reimburse_status_column() -> None:
    """为已有 invoice_details 表补充 reimburse_status 列（SQLite 兼容的轻量迁移）。"""
    try:
        with engine.connect() as conn:
            dialect = engine.dialect.name
            if dialect == "sqlite":
                rows = conn.execute(text("PRAGMA table_info(invoice_details)")).fetchall()
                if not rows:
                    return
                columns = {row[1] for row in rows}
                if "reimburse_status" not in columns:
                    conn.execute(text(
                        "ALTER TABLE invoice_details ADD COLUMN reimburse_status VARCHAR(20) DEFAULT '待报销'"
                    ))
                    conn.commit()
                    logger.info("已为 invoice_details 表补充 reimburse_status 列")
            else:
                try:
                    conn.execute(text(
                        "ALTER TABLE invoice_details ADD COLUMN reimburse_status VARCHAR(20) DEFAULT '待报销'"
                    ))
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"检查/补充 invoice_details.reimburse_status 列失败（可忽略）: {e}")


def _deduplicate_email_messages() -> None:
    """清理 email_messages 表中的重复数据

    1. 删除所有 message_uid=NULL 的旧记录（最早一次批量下载残留，无去重价值）
    2. 对剩余记录按 (config_id, message_uid, attachment_name) 去重，保留 id 最大的一条
    """
    from app.models.email_message import EmailMessage

    db = SessionLocal()
    try:
        # 1. 删除所有 message_uid=NULL 的旧记录
        deleted_null = db.query(EmailMessage).filter(
            EmailMessage.message_uid.is_(None)
        ).delete(synchronize_session=False)
        if deleted_null:
            logger.info(f"删除 {deleted_null} 条无UID的旧记录")

        # 2. 对剩余记录按 (config_id, message_uid, attachment_name) 去重，保留 id 最大的
        keep_ids_sql = text('''
            SELECT MAX(id) as keep_id
            FROM email_messages
            WHERE message_uid IS NOT NULL
            GROUP BY config_id, message_uid, COALESCE(attachment_name, '')
        ''')
        keep_ids = {row[0] for row in db.execute(keep_ids_sql).fetchall()}

        all_ids_sql = text('''
            SELECT id FROM email_messages WHERE message_uid IS NOT NULL
        ''')
        all_ids = {row[0] for row in db.execute(all_ids_sql).fetchall()}

        delete_ids = all_ids - keep_ids
        if delete_ids:
            db.query(EmailMessage).filter(
                EmailMessage.id.in_(list(delete_ids))
            ).delete(synchronize_session=False)
            logger.info(f"去重删除 {len(delete_ids)} 条重复记录")

        db.commit()

        remaining = db.query(EmailMessage).count()
        logger.info(f"邮件去重清理完成，剩余 {remaining} 条记录")
    except Exception as e:
        db.rollback()
        logger.warning(f"邮件去重清理失败: {e}")
    finally:
        db.close()


def _ensure_invoice_details_schema() -> None:
    """检测旧版 invoice_details 表结构（含已移除的 27 列字段）并重建。

    SQLite 不支持 DROP COLUMN，如果检测到表中还保留着 ``tax_category_code`` 等
    旧字段，直接 DROP 该表，在后续 Base.metadata.create_all() 时会以新结构重建。
    本函数需在 create_all 之前调用。
    """
    try:
        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(engine)
        if "invoice_details" not in inspector.get_table_names():
            return
        columns = [c["name"] for c in inspector.get_columns("invoice_details")]
        if "tax_category_code" in columns:
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS invoice_details"))
                conn.commit()
            logger.info("检测到 invoice_details 表为旧结构，已删除以供重建为 19 列新结构")
    except Exception as e:
        logger.warning(f"检测/重建 invoice_details 表结构失败（可忽略）: {e}")


def init_db() -> None:
    """初始化数据库，创建默认admin用户并进行必要的表结构迁移"""
    _ensure_invoice_file_hash_column()
    _ensure_user_menu_permissions_column()
    _ensure_email_messages_uid_column()
    _ensure_invoice_reimbursement_columns()
    _ensure_invoice_detail_reimburse_status_column()
    _deduplicate_email_messages()
    db: Session = SessionLocal()
    try:
        # 检查是否已有admin用户
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            logger.info("未检测到admin用户，正在创建默认admin账号...")
            default_admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                email="admin@invoiceworker.local",
                role="admin",
                is_active=True,
            )
            db.add(default_admin)
            db.commit()
            logger.info("默认admin账号创建成功: username=admin, password=admin123")
        else:
            logger.info("admin用户已存在，跳过初始化")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        db.rollback()
    finally:
        db.close()
