"""
邮箱配置相关的Pydantic Schema
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class EmailConfigCreate(BaseModel):
    """创建邮箱配置请求"""

    email_address: EmailStr = Field(..., description="邮箱地址")
    imap_server: str = Field(..., min_length=1, max_length=200, description="IMAP服务器")
    port: int = Field(default=993, ge=1, le=65535, description="端口号")
    password: str = Field(..., min_length=1, max_length=200, description="密码或授权码")
    check_interval_minutes: int = Field(default=30, ge=1, le=1440, description="拉取频率(分钟)")
    use_ssl: bool = Field(default=True, description="是否使用SSL")


class EmailConfigUpdate(BaseModel):
    """更新邮箱配置请求(所有字段可选)"""

    email_address: Optional[EmailStr] = None
    imap_server: Optional[str] = Field(default=None, min_length=1, max_length=200)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    password: Optional[str] = Field(default=None, min_length=1, max_length=200)
    check_interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    use_ssl: Optional[bool] = None
    is_active: Optional[bool] = None


class EmailConfigResponse(BaseModel):
    """邮箱配置响应(不返回密码)"""

    id: int
    email_address: str
    imap_server: str
    port: int
    check_interval_minutes: int
    use_ssl: bool = True
    is_active: bool
    last_check_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailTestRequest(BaseModel):
    """测试邮箱连接请求"""

    email_address: EmailStr = Field(..., description="邮箱地址")
    imap_server: str = Field(..., min_length=1, max_length=200, description="IMAP服务器")
    port: int = Field(default=993, ge=1, le=65535, description="端口号")
    password: str = Field(..., min_length=1, max_length=200, description="密码或授权码")
    use_ssl: bool = Field(default=True, description="是否使用SSL")


class EmailTestResponse(BaseModel):
    """测试邮箱连接响应"""

    success: bool
    message: str


class EmailFetchLog(BaseModel):
    """邮箱拉取日志"""

    id: int
    config_id: int
    email_address: Optional[str] = None
    fetch_time: Optional[datetime] = None
    new_invoices_count: int = 0
    total_emails_checked: int = 0
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class EmailFetchResult(BaseModel):
    """邮件拉取结果"""

    config_id: int
    total_emails_checked: int
    new_invoices_found: int
    errors: list[str] = Field(default_factory=list)
    status: str = "success"


class EmailFetchLogPage(BaseModel):
    """拉取日志分页响应"""

    total: int
    page: int
    page_size: int
    items: list[EmailFetchLog] = Field(default_factory=list)
