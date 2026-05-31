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


def init_db() -> None:
    """初始化数据库，创建默认admin用户并进行必要的表结构迁移"""
    _ensure_invoice_file_hash_column()
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
