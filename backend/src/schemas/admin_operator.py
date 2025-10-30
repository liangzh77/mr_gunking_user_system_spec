"""Admin operator management schemas."""

from datetime import datetime
from uuid import UUID
import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from .common import TimestampMixin, UUIDMixin


class CreateOperatorRequest(BaseModel):
    """Create operator account request schema."""

    username: str = Field(..., min_length=3, max_length=64, description="运营商标识符，全局唯一")
    password: str = Field(..., min_length=8, max_length=128, description="运营商登录密码")
    full_name: str = Field(..., min_length=2, max_length=128, description="运营商真实姓名或公司名称")
    email: EmailStr = Field(..., description="运营商邮箱地址")
    phone: str = Field(..., min_length=11, max_length=32, description="运营商联系电话")
    customer_tier: str = Field(default="standard", description="客户分类：vip/standard/trial")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """验证密码复杂度"""
        if len(v) < 8:
            raise ValueError('密码长度不能少于8位')

        # 检查是否包含大写字母
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含至少一个大写字母')

        # 检查是否包含小写字母
        if not re.search(r'[a-z]', v):
            raise ValueError('密码必须包含至少一个小写字母')

        # 检查是否包含数字
        if not re.search(r'\d', v):
            raise ValueError('密码必须包含至少一个数字')

        # 检查是否包含特殊字符
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('密码必须包含至少一个特殊字符')

        # 检查是否包含常见的弱密码模式
        weak_patterns = [
            r'password', r'123456', r'admin', r'qwerty',
            r'abc123', r'111111', r'000000'
        ]
        pattern_lower = v.lower()
        for pattern in weak_patterns:
            if pattern in pattern_lower:
                raise ValueError('密码不能使用常见的弱密码模式')

        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """验证手机号格式"""
        # 中国大陆手机号格式验证
        if not re.match(r'^1[3-9]\d{9}$', v):
            raise ValueError('手机号格式不正确，请输入有效的中国大陆手机号')
        return v

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """验证用户名格式"""
        # 只允许字母、数字、下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v


class OperatorDetailResponse(UUIDMixin, TimestampMixin):
    """Operator detailed information response schema."""

    username: str = Field(description="运营商标识符")
    full_name: str = Field(description="运营商真实姓名或公司名称")
    email: EmailStr = Field(description="运营商邮箱地址")
    phone: str = Field(description="运营商联系电话")
    balance: float = Field(description="账户余额（单位：元）")
    customer_tier: str = Field(description="客户分类：vip/standard/trial")
    is_active: bool = Field(description="账户状态")
    is_locked: bool = Field(description="账户锁定状态")
    locked_reason: str | None = Field(default=None, description="锁定原因")
    locked_at: datetime | None = Field(default=None, description="锁定时间")
    last_login_at: datetime | None = Field(default=None, description="最近登录时间")
    last_login_ip: str | None = Field(default=None, description="最近登录IP")
    api_key: str = Field(description="API Key")

    class Config:
        """Pydantic config."""
        from_attributes = True


class OperatorListItem(UUIDMixin, TimestampMixin):
    """Operator list item response schema."""

    username: str = Field(description="运营商标识符")
    full_name: str = Field(description="运营商真实姓名或公司名称")
    email: EmailStr = Field(description="运营商邮箱地址")
    phone: str = Field(description="运营商联系电话")
    balance: float = Field(description="账户余额（单位：元）")
    customer_tier: str = Field(description="客户分类：vip/standard/trial")
    is_active: bool = Field(description="账户状态")
    is_locked: bool = Field(description="账户锁定状态")
    last_login_at: datetime | None = Field(default=None, description="最近登录时间")

    class Config:
        """Pydantic config."""
        from_attributes = True


class OperatorListResponse(BaseModel):
    """Operator list response schema."""

    items: list[OperatorListItem] = Field(description="运营商列表")
    total: int = Field(description="总数量")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页条数")


class UpdateOperatorRequest(BaseModel):
    """Update operator account request schema."""

    full_name: str | None = Field(None, min_length=2, max_length=128, description="运营商真实姓名或公司名称")
    email: EmailStr | None = Field(None, description="运营商邮箱地址")
    phone: str | None = Field(None, min_length=11, max_length=32, description="运营商联系电话")
    customer_tier: str | None = Field(None, description="客户分类：vip/standard/trial")
    is_active: bool | None = Field(None, description="账户状态")


class ResetApiKeyRequest(BaseModel):
    """Reset API key request schema."""

    operator_id: UUID = Field(..., description="运营商ID")


class ResetApiKeyResponse(BaseModel):
    """Reset API key response schema."""

    operator_id: UUID = Field(description="运营商ID")
    new_api_key: str = Field(description="新的API Key")
    message: str = Field(description="操作结果消息")


class OperatorApiKeyResponse(BaseModel):
    """Operator API key response schema."""

    operator_id: UUID = Field(description="运营商ID")
    username: str = Field(description="运营商用户名")
    api_key: str = Field(description="API Key")
    created_at: datetime = Field(description="账户创建时间")

    class Config:
        """Pydantic config."""
        from_attributes = True