"""API v1 routers."""

from fastapi import APIRouter

from .admin_auth import router as admin_auth_router

# Create main API v1 router
api_router = APIRouter()

# Include all v1 routers
api_router.include_router(admin_auth_router)

__all__ = ["api_router"]
