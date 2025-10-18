"""API v1 routers.

User Story 1 - 游戏授权与实时计费:
- /auth/game/authorize - 游戏授权请求

User Story 2 - 运营商账户与财务管理:
- /auth/operators/register - 运营商注册
- /auth/operators/login - 运营商登录
- /operators/me - 运营商个人信息管理
"""

from fastapi import APIRouter

from .admin_auth import router as admin_auth_router
from .admin_operations import router as admin_operations_router
from .auth import router as auth_router
from .finance import router as finance_router
from .operators import router as operators_router
from .webhooks import router as webhooks_router

# Create main API v1 router
api_router = APIRouter()

# Include all v1 routers
api_router.include_router(admin_auth_router)
api_router.include_router(admin_operations_router)  # Admin business operations
api_router.include_router(auth_router)  # User Story 1: 游戏授权 & User Story 2: 运营商认证 & User Story 6: 财务认证
api_router.include_router(finance_router)  # User Story 6: 财务后台业务 (T175-T186)
api_router.include_router(operators_router)  # User Story 2: 运营商个人信息管理
api_router.include_router(webhooks_router)  # User Story 2: 支付回调webhooks (T078)

__all__ = ["api_router"]
