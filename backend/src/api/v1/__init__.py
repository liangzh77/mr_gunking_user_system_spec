"""API v1 routers.

User Story 1 - 游戏授权与实时计费:
- /auth/game/authorize - 游戏授权请求
"""

from fastapi import APIRouter

from .admin_auth import router as admin_auth_router
from .auth import router as auth_router

# Create main API v1 router
api_router = APIRouter()

# Include all v1 routers
api_router.include_router(admin_auth_router)
api_router.include_router(auth_router)  # User Story 1: 游戏授权

__all__ = ["api_router"]
