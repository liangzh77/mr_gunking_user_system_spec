"""Application configuration using Pydantic Settings.

This module defines the configuration model for the entire application,
loading values from environment variables and .env files.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ========== Database Configuration ==========
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://mr_admin:mr_password@localhost:5432/mr_game_ops",
        description="PostgreSQL database connection URL with asyncpg driver",
    )
    DATABASE_POOL_SIZE: int = Field(default=20, ge=1, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=50)
    DATABASE_ECHO: bool = Field(default=False, description="Enable SQL query logging")

    # ========== Redis Configuration ==========
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and sessions",
    )
    REDIS_PASSWORD: str = Field(default="", description="Redis password (if required)")
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=1, le=500)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5, ge=1, le=60)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5, ge=1, le=60)

    # ========== Security Configuration ==========
    SECRET_KEY: str = Field(
        default="dev_secret_key_change_in_production",
        min_length=32,
        description="Secret key for general cryptographic operations",
    )
    JWT_SECRET_KEY: str = Field(
        default="dev_jwt_secret_change_in_production",
        min_length=32,
        description="Secret key for JWT token signing",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=43200,  # 30 days
        ge=1,
        description="JWT access token expiration time in minutes",
    )
    ENCRYPTION_KEY: str = Field(
        default="dev_encryption_key_32_bytes_long",
        min_length=32,
        max_length=64,  # 支持base64编码的32字节密钥(44字符)或十六进制(64字符)
        description="Encryption key for sensitive data - 32 chars hex or 44 chars base64",
    )

    # ========== Application Configuration ==========
    APP_NAME: str = Field(default="MR游戏运营管理系统", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development", description="Deployment environment"
    )

    # ========== API Configuration ==========
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix path")
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Allowed CORS origins (comma-separated)",
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="Allow credentials in CORS")
    MAX_REQUEST_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024,
        description="Maximum request body size in bytes",
    )

    # ========== Server Configuration ==========
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, ge=1, le=65535, description="Server port")
    WORKERS: int = Field(default=1, ge=1, le=32, description="Number of worker processes")
    RELOAD: bool = Field(default=True, description="Enable auto-reload in development")

    # ========== Rate Limiting Configuration ==========
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=10,
        ge=1,
        description="Rate limit per endpoint per minute",
    )
    RATE_LIMIT_IP_PER_MINUTE: int = Field(
        default=100,
        ge=1,
        description="Global rate limit per IP per minute",
    )

    # ========== Logging Configuration ==========
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    LOG_FORMAT: Literal["json", "text"] = Field(
        default="json", description="Log output format"
    )
    LOG_FILE_PATH: str = Field(default="logs/app.log", description="Log file path")

    # ========== Payment Platform Configuration ==========
    WECHAT_PAY_APP_ID: str = Field(default="", description="WeChat Pay App ID")
    WECHAT_PAY_MCH_ID: str = Field(default="", description="WeChat Pay Merchant ID")
    WECHAT_PAY_API_KEY: str = Field(default="", description="WeChat Pay API Key")

    ALIPAY_APP_ID: str = Field(default="", description="Alipay App ID")
    ALIPAY_PRIVATE_KEY: str = Field(default="", description="Alipay Private Key")
    ALIPAY_PUBLIC_KEY: str = Field(default="", description="Alipay Public Key")

    # ========== File Storage Configuration ==========
    UPLOAD_DIR: str = Field(default="uploads", description="Upload directory path")
    INVOICE_DIR: str = Field(default="invoices", description="Invoice directory path")
    MAX_FILE_SIZE: int = Field(
        default=5 * 1024 * 1024,  # 5MB
        ge=1024,
        description="Maximum upload file size in bytes",
    )

    # ========== Business Configuration ==========
    # Note: These are backup values. Actual values are stored in database (system_configs table)
    BALANCE_THRESHOLD: float = Field(
        default=100.0,
        ge=0,
        description="Low balance alert threshold (yuan)",
    )
    SESSION_TIMEOUT_MINUTES: int = Field(
        default=30,
        ge=1,
        description="User session timeout in minutes",
    )
    PAYMENT_TIMEOUT_MINUTES: int = Field(
        default=5,
        ge=1,
        description="Payment callback timeout in minutes",
    )

    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DEBUG")
    @classmethod
    def parse_debug(cls, v: str | bool) -> bool:
        """Parse DEBUG flag from string or boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return False

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings instance.

    Uses functools.lru_cache to ensure settings are loaded only once.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Global settings instance (for convenience)
settings = get_settings()
