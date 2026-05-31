from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.core.database import Base


class Category(Base):
    """发票分类模型"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)  # 分类名称
    keywords = Column(Text, nullable=True)  # 关键词列表，用逗号分隔，用于自动匹配
    description = Column(String(500), nullable=True)  # 分类描述
    color = Column(String(20), nullable=False, default="#409EFF")  # 显示颜色
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
