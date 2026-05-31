import logging

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

logger = logging.getLogger(__name__)


def init_db() -> None:
    """初始化数据库，创建默认admin用户"""
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
