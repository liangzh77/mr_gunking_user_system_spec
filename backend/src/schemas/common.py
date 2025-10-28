"""Common Pydantic schemas used across the application.

This module provides base schemas, response wrappers, pagination models,
and commonly reused schema patterns.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Generic type variable for response data
T = TypeVar("T")


class TimestampMixin(BaseModel):
    """Mixin for models with created_at and updated_at timestamps."""

    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class UUIDMixin(BaseModel):
    """Mixin for models with UUID primary key."""

    id: UUID = Field(description="Unique identifier (UUID)")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper.

    Attributes:
        success: Always True for success responses
        data: Response payload
        message: Optional success message
    """

    success: bool = Field(default=True, description="Operation success flag")
    data: T = Field(description="Response data")
    message: str = Field(default="Success", description="Success message")


class ErrorResponse(BaseModel):
    """Standard error response wrapper.

    Attributes:
        success: Always False for error responses
        error: Error details
        message: Error message
        code: Optional error code
    """

    success: bool = Field(default=False, description="Operation success flag")
    error: dict[str, Any] = Field(description="Error details")
    message: str = Field(description="Error message")
    code: str | None = Field(default=None, description="Error code")


class PaginationParams(BaseModel):
    """Pagination query parameters.

    Attributes:
        page: Page number (1-indexed)
        page_size: Number of items per page
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Items per page (max 100)"
    )

    @property
    def offset(self) -> int:
        """Calculate database offset from page and page_size.

        Returns:
            int: Offset for database query
        """
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get database limit (same as page_size).

        Returns:
            int: Limit for database query
        """
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper.

    Attributes:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
    """

    items: list[T] = Field(description="Items for current page")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")

    @classmethod
    def create(
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> "PaginatedResponse[T]":
        """Create a paginated response.

        Args:
            items: Items for current page
            total: Total number of items
            page: Current page number
            page_size: Items per page

        Returns:
            PaginatedResponse: Paginated response instance
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class TokenResponse(BaseModel):
    """JWT token response.

    Attributes:
        access_token: JWT access token
        token_type: Token type (always "bearer")
        expires_in: Token expiration time in seconds
    """

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time (seconds)")


class HealthCheckResponse(BaseModel):
    """Health check response.

    Attributes:
        status: Overall health status
        database: Database connectivity status
        version: Application version
        timestamp: Health check timestamp
    """

    status: str = Field(description="Overall health status (healthy/unhealthy)")
    database: bool = Field(description="Database connectivity status")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(description="Health check timestamp")


class MessageResponse(BaseModel):
    """Simple message response.

    Attributes:
        message: Response message
    """

    message: str = Field(description="Response message")


class IDResponse(BaseModel):
    """Response containing a single ID.

    Attributes:
        id: Resource identifier
    """

    id: UUID = Field(description="Resource identifier")


class MoneyField(BaseModel):
    """Money field with validation.

    Used for financial amounts to ensure proper formatting.

    Attributes:
        amount: Amount in yuan (RMB)
        currency: Currency code (default: CNY)
    """

    amount: float = Field(ge=0, description="Amount in yuan")
    currency: str = Field(default="CNY", description="Currency code")

    @field_validator("amount")
    @classmethod
    def validate_decimal_places(cls, v: float) -> float:
        """Validate that amount has at most 2 decimal places.

        Args:
            v: Amount value

        Returns:
            float: Validated amount

        Raises:
            ValueError: If amount has more than 2 decimal places
        """
        if round(v, 2) != v:
            raise ValueError("Amount must have at most 2 decimal places")
        return v


class DateRangeFilter(BaseModel):
    """Date range filter for queries.

    Attributes:
        start_date: Range start date (inclusive)
        end_date: Range end date (inclusive)
    """

    start_date: datetime | None = Field(
        default=None, description="Range start (inclusive)"
    )
    end_date: datetime | None = Field(
        default=None, description="Range end (inclusive)"
    )

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: datetime | None, info) -> datetime | None:
        """Validate that end_date is after start_date.

        Args:
            v: End date value
            info: Validation info containing other fields

        Returns:
            datetime | None: Validated end date

        Raises:
            ValueError: If end_date is before start_date
        """
        start_date = info.data.get("start_date")
        if v and start_date and v < start_date:
            raise ValueError("end_date must be after start_date")
        return v


class SortOrder(BaseModel):
    """Sort order specification.

    Attributes:
        field: Field name to sort by
        direction: Sort direction ("asc" or "desc")
    """

    field: str = Field(description="Field name to sort by")
    direction: str = Field(
        default="asc", pattern="^(asc|desc)$", description="Sort direction"
    )
