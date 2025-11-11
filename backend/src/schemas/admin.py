"""Admin authentication and user management schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from .common import TimestampMixin, TokenResponse, UUIDMixin


# ========== Authentication Schemas ==========


class AdminLoginRequest(BaseModel):
    """Admin login request schema."""

    username: str = Field(..., min_length=3, max_length=64, description="Admin username")
    password: str = Field(..., min_length=6, max_length=128, description="Admin password")
    captcha_key: str = Field(..., min_length=1, description="Captcha key")
    captcha_code: str = Field(..., min_length=4, max_length=4, description="Captcha code")


class AdminLoginResponse(TokenResponse):
    """Admin login response with token and user info."""

    user: "AdminUserInfo" = Field(description="Admin user information")


class AdminRefreshRequest(BaseModel):
    """Token refresh request schema."""

    refresh_token: str = Field(..., description="Refresh token")


# ========== User Info Schemas ==========


class AdminUserInfo(UUIDMixin, TimestampMixin):
    """Admin user information schema (public data only)."""

    username: str = Field(description="Admin username")
    full_name: str = Field(description="Full name")
    email: EmailStr = Field(description="Email address")
    phone: str = Field(description="Phone number")
    role: str = Field(description="Admin role")
    permissions: list[str] = Field(default_factory=list, description="Permission list")
    is_active: bool = Field(description="Account active status")
    last_login_at: datetime | None = Field(default=None, description="Last login time")
    last_login_ip: str | None = Field(default=None, description="Last login IP")

    class Config:
        """Pydantic config."""
        from_attributes = True


class AdminUserDetail(AdminUserInfo):
    """Admin user detailed information (for admin viewing)."""

    created_by: UUID | None = Field(default=None, description="Creator admin ID")


# ========== Admin Management Schemas ==========


class AdminCreateRequest(BaseModel):
    """Create admin account request."""

    username: str = Field(..., min_length=3, max_length=64, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    full_name: str = Field(..., min_length=2, max_length=128, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: str = Field(..., min_length=11, max_length=32, description="Phone number")
    role: str = Field(default="admin", description="Admin role")
    permissions: list[str] = Field(default_factory=list, description="Permissions")


class AdminUpdateRequest(BaseModel):
    """Update admin account request."""

    full_name: str | None = Field(None, min_length=2, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=11, max_length=32)
    role: str | None = None
    permissions: list[str] | None = None
    is_active: bool | None = None


class AdminChangePasswordRequest(BaseModel):
    """Change admin password request."""

    old_password: str = Field(..., min_length=6, max_length=128, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


# ========== Response Schemas ==========


class AdminListResponse(BaseModel):
    """Admin list response."""

    items: list[AdminUserInfo] = Field(description="Admin list")
    total: int = Field(description="Total count")


# ========== Application Authorization Request Management ==========


class ApplicationRequestReviewRequest(BaseModel):
    """Review application authorization request."""

    action: str = Field(..., description="Review action: approve/reject")
    reject_reason: str | None = Field(None, min_length=10, max_length=500, description="Reject reason (required if action=reject)")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "examples": [
                {
                    "action": "approve"
                },
                {
                    "action": "reject",
                    "reject_reason": "该应用暂未对您的客户分类开放授权"
                }
            ]
        }


# Rebuild models to resolve forward references
AdminLoginResponse.model_rebuild()
