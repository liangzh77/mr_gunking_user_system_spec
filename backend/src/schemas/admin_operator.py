"""Admin operator management schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from .common import TimestampMixin, UUIDMixin


class CreateOperatorRequest(BaseModel):
    """Create operator account request schema."""

    username: str = Field(..., min_length=3, max_length=64, description="运营商标识符，全局唯一")
    password: str = Field(..., min_length=8, max_length=128, description="运营商登录密码")
    full_name: str = Field(..., min_length=2, max_length=128, description="运营商真实姓名或公司名称")
    email: EmailStr = Field(..., description="运营商邮箱地址")
    phone: str = Field(..., min_length=11, max_length=32, description="运营商联系电话")
    customer_tier: str = Field(default="standard", description="客户分类：vip/standard/trial")


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