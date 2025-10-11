"""Admin authentication API endpoints."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import CurrentUserToken, DatabaseSession
from ...schemas.admin import (
    AdminChangePasswordRequest,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUserInfo,
)
from ...schemas.common import MessageResponse
from ...services.admin_auth import AdminAuthService

router = APIRouter(prefix="/admin", tags=["Admin Authentication"])


@router.post(
    "/login",
    response_model=AdminLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Login",
    description="Authenticate admin and return access token",
)
async def admin_login(
    request: Request,
    login_data: AdminLoginRequest,
    db: DatabaseSession,
) -> AdminLoginResponse:
    """Admin login endpoint.

    Args:
        request: FastAPI request object (for client IP)
        login_data: Login credentials
        db: Database session

    Returns:
        AdminLoginResponse: Access token and user info
    """
    service = AdminAuthService(db)
    client_ip = request.client.host if request.client else "unknown"

    return await service.login(
        username=login_data.username,
        password=login_data.password,
        client_ip=client_ip,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Logout",
    description="Logout admin (client should discard token)",
)
async def admin_logout(
    token: CurrentUserToken,
) -> MessageResponse:
    """Admin logout endpoint.

    Note: This is a client-side operation. The server doesn't maintain
    a token blacklist. Client should simply discard the token.

    Args:
        token: Current user token (for authentication)

    Returns:
        MessageResponse: Success message
    """
    # In a stateless JWT system, logout is handled client-side
    # The token will expire naturally after JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    return MessageResponse(message="Logged out successfully")


@router.get(
    "/me",
    response_model=AdminUserInfo,
    status_code=status.HTTP_200_OK,
    summary="Get Current Admin Info",
    description="Get current authenticated admin user information",
)
async def get_current_admin_info(
    token: CurrentUserToken,
    db: DatabaseSession,
) -> AdminUserInfo:
    """Get current admin user info endpoint.

    Args:
        token: Current user token payload
        db: Database session

    Returns:
        AdminUserInfo: Current admin information
    """
    service = AdminAuthService(db)
    admin = await service.get_current_admin(token)
    return AdminUserInfo.model_validate(admin)


@router.post(
    "/refresh",
    response_model=AdminLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
    description="Refresh access token with current token",
)
async def refresh_admin_token(
    token: CurrentUserToken,
    db: DatabaseSession,
) -> AdminLoginResponse:
    """Refresh access token endpoint.

    Args:
        token: Current user token
        db: Database session

    Returns:
        AdminLoginResponse: New access token and user info
    """
    service = AdminAuthService(db)
    # Extract the raw token from Authorization header would be better,
    # but for now we'll recreate it from the payload
    # In production, you might want to pass the raw token
    return await service.refresh_token(token.get("raw_token", ""))


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Password",
    description="Change current admin password",
)
async def change_admin_password(
    password_data: AdminChangePasswordRequest,
    token: CurrentUserToken,
    db: DatabaseSession,
) -> MessageResponse:
    """Change admin password endpoint.

    Args:
        password_data: Old and new passwords
        token: Current user token
        db: Database session

    Returns:
        MessageResponse: Success message
    """
    service = AdminAuthService(db)
    admin_id = token.get("sub")

    await service.change_password(
        admin_id=admin_id,
        old_password=password_data.old_password,
        new_password=password_data.new_password,
    )

    return MessageResponse(message="Password changed successfully")
