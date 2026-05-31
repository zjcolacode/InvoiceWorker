from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 基础配置
    APP_NAME: str = "InvoiceWorker"
    DEBUG: bool = True

    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./invoice_worker.db"

    # DashScope API配置
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_BASE_URL: str = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    VISION_MODEL: str = "qwen3.6-plus"

    # 文件存储路径
    PDF_STORAGE_PATH: str = "./storage/pdf_invoices"
    PAPER_STORAGE_PATH: str = "./storage/paper_invoices"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
