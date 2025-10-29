"""Pydantic schemas for request/response validation.

User Story 1 - 游戏授权与实时计费:
- auth: 游戏授权请求/响应
- usage_record: 使用记录数据模型
- transaction: 交易记录数据模型
"""

from .admin import (
    AdminChangePasswordRequest,
    AdminCreateRequest,
    AdminListResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminRefreshRequest,
    AdminUpdateRequest,
    AdminUserDetail,
    AdminUserInfo,
)
from .admin_application import (
    ApplicationListResponse,
    ApplicationResponse,
    AuthorizationListResponse,
    AuthorizationResponse,
    AuthorizeApplicationRequest,
    CreateApplicationRequest,
    RevokeAuthorizationRequest,
    UpdateApplicationRequest,
)
from .auth import (
    GameAuthorizeRequest,
    GameAuthorizeResponse,
    GameAuthorizeData,
    ErrorDetail,
)
from .common import (
    DateRangeFilter,
    ErrorResponse,
    HealthCheckResponse,
    IDResponse,
    MessageResponse,
    MoneyField,
    PaginatedResponse,
    PaginationParams,
    SortOrder,
    SuccessResponse,
    TimestampMixin,
    TokenResponse,
    UUIDMixin,
)
from .transaction import (
    TransactionRecordCreate,
    TransactionRecordInDB,
    TransactionRecordResponse,
    RechargeRequest,
)
from .usage_record import (
    UsageRecordCreate,
    UsageRecordInDB,
    UsageRecordResponse,
)

__all__ = [
    # Mixins
    "TimestampMixin",
    "UUIDMixin",
    # Response wrappers
    "SuccessResponse",
    "ErrorResponse",
    "MessageResponse",
    "IDResponse",
    "TokenResponse",
    "HealthCheckResponse",
    # Pagination
    "PaginationParams",
    "PaginatedResponse",
    # Filters and sorting
    "DateRangeFilter",
    "SortOrder",
    # Special fields
    "MoneyField",
    # Admin schemas
    "AdminLoginRequest",
    "AdminLoginResponse",
    "AdminRefreshRequest",
    "AdminUserInfo",
    "AdminUserDetail",
    "AdminCreateRequest",
    "AdminUpdateRequest",
    "AdminChangePasswordRequest",
    "AdminListResponse",
    # Admin application management schemas
    "CreateApplicationRequest",
    "UpdateApplicationRequest",
    "ApplicationResponse",
    "ApplicationListResponse",
    "AuthorizeApplicationRequest",
    "AuthorizationResponse",
    "AuthorizationListResponse",
    "RevokeAuthorizationRequest",
    # User Story 1: Auth schemas
    "GameAuthorizeRequest",
    "GameAuthorizeResponse",
    "GameAuthorizeData",
    "ErrorDetail",
    # User Story 1: Usage record schemas
    "UsageRecordCreate",
    "UsageRecordInDB",
    "UsageRecordResponse",
    # User Story 1: Transaction schemas
    "TransactionRecordCreate",
    "TransactionRecordInDB",
    "TransactionRecordResponse",
    "RechargeRequest",
]
