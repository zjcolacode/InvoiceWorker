import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: Optional[str] = None
    role: str = Field(default="operator", pattern="^(admin|operator|viewer)$")
    menu_permissions: Optional[List[str]] = None
    full_name: str | None = None
    position: str | None = None


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
    menu_permissions: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    full_name: str | None = None
    position: str | None = None

    @field_validator("menu_permissions", mode="before")
    @classmethod
    def _parse_menu_permissions(cls, v):
        """将数据库中的 JSON 字符串反序列化为列表。"""
        if v is None or v == "":
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else None
            except (ValueError, TypeError):
                return None
        return None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """更新用户信息（admin 可修改全部字段；普通用户接口仅修改邮箱）"""
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[str] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|operator|viewer)$")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    full_name: str | None = None
    position: str | None = None


class UserPermissionsUpdate(BaseModel):
    """更新用户菜单权限"""
    permissions: List[str] = Field(default_factory=list)


class MenuItem(BaseModel):
    """可分配菜单项"""
    path: str
    title: str
    roles: Optional[List[str]] = None


class UserListResponse(BaseModel):
    """分页用户列表"""
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class Token(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token数据"""
    username: Optional[str] = None
    role: Optional[str] = None
