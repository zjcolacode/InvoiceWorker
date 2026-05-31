from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = None
    role: str = Field(default="operator", pattern="^(admin|operator|viewer)$")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """更新用户信息"""
    email: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|operator|viewer)$")
    is_active: Optional[bool] = None


class Token(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token数据"""
    username: Optional[str] = None
    role: Optional[str] = None
