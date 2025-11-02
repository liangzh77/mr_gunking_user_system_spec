"""Admin application management schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .common import TimestampMixin, UUIDMixin


# ========== Application Management Schemas ==========


class CreateApplicationRequest(BaseModel):
    """Create application request schema."""

    app_name: str = Field(..., min_length=2, max_length=50, description="Application name")
    unit_price: Decimal = Field(..., gt=0, description="Price per player (in CNY)")
    min_players: int = Field(..., ge=1, description="Minimum number of players")
    max_players: int = Field(..., ge=1, description="Maximum number of players")
    description: str | None = Field(None, max_length=500, description="Application description")

    @field_validator("unit_price", mode="before")
    @classmethod
    def validate_price(cls, v):
        """Validate price format."""
        if isinstance(v, str):
            return Decimal(v)
        return v

    @field_validator("max_players")
    @classmethod
    def validate_player_range(cls, v, info):
        """Validate that max_players >= min_players."""
        min_players = info.data.get("min_players")
        if min_players and v < min_players:
            raise ValueError("max_players must be greater than or equal to min_players")
        return v

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "examples": [
                {
                    "app_name": "星际战争",
                    "unit_price": "12.00",
                    "min_players": 2,
                    "max_players": 6,
                    "description": "多人太空射击游戏，支持2-6人同时游玩"
                }
            ]
        }


class UpdateApplicationRequest(BaseModel):
    """Update application request schema (excludes unit_price)."""

    app_name: str | None = Field(None, min_length=2, max_length=50, description="Application name")
    min_players: int | None = Field(None, ge=1, description="Minimum number of players")
    max_players: int | None = Field(None, ge=1, description="Maximum number of players")
    description: str | None = Field(None, max_length=500, description="Application description")
    is_active: bool | None = Field(None, description="Application active status")
    launch_exe_path: str | None = Field(None, max_length=500, description="启动exe的绝对路径")

    @field_validator("max_players")
    @classmethod
    def validate_player_range(cls, v, info):
        """Validate that max_players >= min_players if both provided."""
        min_players = info.data.get("min_players")
        if min_players and v and v < min_players:
            raise ValueError("max_players must be greater than or equal to min_players")
        return v

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "examples": [
                {
                    "app_name": "太空探险（升级版）",
                    "min_players": 2,
                    "max_players": 8,
                    "description": "升级版太空探险，支持更多玩家"
                }
            ]
        }


class ApplicationResponse(UUIDMixin, TimestampMixin):
    """Application response schema."""

    app_code: str = Field(description="Application code (unique identifier)")
    app_name: str = Field(description="Application name")
    price_per_player: Decimal = Field(description="Price per player (in CNY)")
    min_players: int = Field(description="Minimum number of players")
    max_players: int = Field(description="Maximum number of players")
    description: str | None = Field(default=None, description="Application description")
    is_active: bool = Field(description="Application active status")
    launch_exe_path: str | None = Field(default=None, description="启动exe的绝对路径")
    created_by: UUID | None = Field(default=None, description="Creator admin ID")

    class Config:
        """Pydantic config."""
        from_attributes = True


# ========== Authorization Management Schemas ==========


class AuthorizeApplicationRequest(BaseModel):
    """Authorize application to operator request schema."""

    operator_id: UUID = Field(..., description="Operator ID")
    application_id: UUID = Field(..., description="Application ID")
    expires_at: datetime | None = Field(None, description="Authorization expiration time (null for permanent)")
    application_request_id: UUID | None = Field(None, description="Related application request ID (if from request)")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "examples": [
                {
                    "operator_id": "123e4567-e89b-12d3-a456-426614174000",
                    "application_id": "223e4567-e89b-12d3-a456-426614174000",
                    "expires_at": "2025-12-31T23:59:59Z"
                },
                {
                    "operator_id": "123e4567-e89b-12d3-a456-426614174000",
                    "application_id": "223e4567-e89b-12d3-a456-426614174000",
                    "expires_at": None
                }
            ]
        }


class AuthorizationResponse(UUIDMixin, TimestampMixin):
    """Authorization response schema."""

    operator_id: UUID = Field(description="Operator ID")
    application_id: UUID = Field(description="Application ID")
    operator_name: str = Field(description="Operator name")
    app_name: str = Field(description="Application name")
    authorized_at: datetime = Field(description="Authorization time")
    expires_at: datetime | None = Field(default=None, description="Expiration time (null for permanent)")
    authorized_by: UUID = Field(description="Authorizer admin ID")
    application_request_id: UUID | None = Field(default=None, description="Related application request ID")
    is_active: bool = Field(description="Authorization active status")

    class Config:
        """Pydantic config."""
        from_attributes = True


class RevokeAuthorizationRequest(BaseModel):
    """Revoke authorization request schema."""

    reason: str | None = Field(None, min_length=10, max_length=500, description="Revocation reason")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "examples": [
                {
                    "reason": "该运营商账户已注销，需要撤销所有授权"
                }
            ]
        }


# ========== Application List Response ==========


class ApplicationListResponse(BaseModel):
    """Application list response schema."""

    items: list[ApplicationResponse] = Field(description="Application list")
    total: int = Field(description="Total count")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total pages")


class AuthorizationListResponse(BaseModel):
    """Authorization list response schema."""

    items: list[AuthorizationResponse] = Field(description="Authorization list")
    total: int = Field(description="Total count")
    page: int = Field(description="Current page")
    page_size: int = Field(description="Page size")
    total_pages: int = Field(description="Total pages")
