"""Security middleware for HTTPS enforcement and secure headers.

This module provides middleware for:
- HTTPS redirect enforcement
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- TLS 1.3 configuration
"""

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core import get_settings

logger = logging.getLogger(__name__)


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTPS connections.

    Redirects HTTP requests to HTTPS in production environment.
    Adds strict security headers to all responses.
    """

    def __init__(self, app: ASGIApp):
        """Initialize HTTPS redirect middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and enforce HTTPS.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with security headers
        """
        # Check if HTTPS enforcement is needed
        if self.settings.is_production:
            # Get request scheme (http or https)
            scheme = request.url.scheme

            # Check X-Forwarded-Proto header (for reverse proxy setups)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")

            # Redirect HTTP to HTTPS in production
            if scheme == "http" and forwarded_proto != "https":
                # Don't redirect health check endpoints
                if request.url.path not in ["/health", "/metrics"]:
                    https_url = request.url.replace(scheme="https")
                    logger.info(
                        "https_redirect",
                        from_url=str(request.url),
                        to_url=str(https_url)
                    )
                    return Response(
                        status_code=301,  # Permanent redirect
                        headers={"Location": str(https_url)}
                    )

        # Process request
        response = await call_next(request)

        # Add security headers to response
        self._add_security_headers(response)

        return response

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response.

        Args:
            response: Response object to modify
        """
        # Strict-Transport-Security (HSTS)
        # Force HTTPS for 1 year, include subdomains
        if self.settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # X-Content-Type-Options
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy, but still useful)
        # Enable browser XSS filter
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content-Security-Policy
        # Restrict resource loading to prevent XSS
        # In development: allow CDN resources for Swagger UI
        if self.settings.is_production:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
        else:
            # Development: allow CDN for Swagger UI
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "img-src 'self' data: https:",
                "font-src 'self' data: https://cdn.jsdelivr.net",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Referrer-Policy
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy (formerly Feature-Policy)
        # Disable unnecessary browser features
        permissions_directives = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Lightweight middleware for adding security headers only.

    Use this instead of HTTPSRedirectMiddleware if HTTPS redirect
    is handled by reverse proxy (nginx, CloudFlare, etc.)
    """

    def __init__(self, app: ASGIApp):
        """Initialize security headers middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # Add all security headers
        if self.settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # In development: allow CDN resources for Swagger UI
        if self.settings.is_production:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
        else:
            # Development: allow CDN for Swagger UI
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "img-src 'self' data: https:",
                "font-src 'self' data: https://cdn.jsdelivr.net",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        permissions_directives = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_directives)

        return response
