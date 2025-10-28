"""Timestamp validation utilities for API security.

This module provides utilities for validating request timestamps
to prevent replay attacks and ensure requests are within acceptable time windows.
"""

from datetime import datetime, timezone
from typing import Optional


def get_current_timestamp() -> int:
    """Get current UTC timestamp in seconds.

    Returns:
        int: Current Unix timestamp (seconds since epoch)

    Example:
        >>> ts = get_current_timestamp()
        >>> ts > 1700000000  # After 2023-11-14
        True
    """
    return int(datetime.now(timezone.utc).timestamp())


def is_timestamp_valid(
    timestamp: int,
    max_age_seconds: int = 300,
    allow_future: bool = False,
    future_tolerance_seconds: int = 60,
) -> bool:
    """Validate if a timestamp is within acceptable time range.

    This function helps prevent replay attacks by ensuring requests
    are neither too old nor (optionally) too far in the future.

    Args:
        timestamp: Unix timestamp to validate (seconds since epoch)
        max_age_seconds: Maximum age allowed for timestamp (default: 300 = 5 minutes)
        allow_future: Whether to allow future timestamps (default: False)
        future_tolerance_seconds: If allow_future=True, max seconds into future (default: 60)

    Returns:
        bool: True if timestamp is valid, False otherwise

    Example:
        >>> current = get_current_timestamp()
        >>> is_timestamp_valid(current)
        True
        >>> is_timestamp_valid(current - 600)  # 10 minutes ago
        False
        >>> is_timestamp_valid(current + 120)  # 2 minutes in future
        False
    """
    current = get_current_timestamp()

    # Check if timestamp is too old
    age = current - timestamp
    if age > max_age_seconds:
        return False

    # Check if timestamp is in the future
    if timestamp > current:
        if not allow_future:
            return False
        # If future is allowed, check if it's within tolerance
        if timestamp - current > future_tolerance_seconds:
            return False

    return True


def validate_timestamp(
    timestamp: int,
    max_age_seconds: int = 300,
    allow_future: bool = False,
    future_tolerance_seconds: int = 60,
) -> tuple[bool, Optional[str]]:
    """Validate timestamp and return result with error message.

    Args:
        timestamp: Unix timestamp to validate
        max_age_seconds: Maximum age allowed (default: 300 seconds)
        allow_future: Whether to allow future timestamps (default: False)
        future_tolerance_seconds: Max future tolerance if allowed (default: 60)

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
            - is_valid: True if valid, False otherwise
            - error_message: None if valid, descriptive error message if invalid

    Example:
        >>> current = get_current_timestamp()
        >>> validate_timestamp(current)
        (True, None)
        >>> validate_timestamp(current - 600)
        (False, 'Timestamp is too old (expired)')
    """
    current = get_current_timestamp()

    # Check if timestamp is too old
    age = current - timestamp
    if age > max_age_seconds:
        return False, f"Timestamp is too old (expired)"

    # Check if timestamp is in the future
    if timestamp > current:
        if not allow_future:
            return False, "Timestamp is in the future (not allowed)"
        # If future is allowed, check tolerance
        future_diff = timestamp - current
        if future_diff > future_tolerance_seconds:
            return (
                False,
                f"Timestamp is too far in the future (max {future_tolerance_seconds}s)",
            )

    return True, None


def timestamp_to_datetime(timestamp: int) -> datetime:
    """Convert Unix timestamp to timezone-aware datetime (UTC).

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        datetime: Timezone-aware datetime object in UTC

    Example:
        >>> dt = timestamp_to_datetime(1700000000)
        >>> dt.year
        2023
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to Unix timestamp.

    Args:
        dt: datetime object (will be converted to UTC if not timezone-aware)

    Returns:
        int: Unix timestamp (seconds since epoch)

    Example:
        >>> dt = datetime(2023, 11, 14, 12, 0, 0, tzinfo=timezone.utc)
        >>> ts = datetime_to_timestamp(dt)
        >>> ts == 1699963200
        True
    """
    # If naive datetime, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def get_timestamp_age(timestamp: int) -> int:
    """Get the age of a timestamp in seconds.

    Args:
        timestamp: Unix timestamp to check

    Returns:
        int: Age in seconds (positive if in past, negative if in future)

    Example:
        >>> current = get_current_timestamp()
        >>> get_timestamp_age(current - 60)
        60
        >>> get_timestamp_age(current + 60)
        -60
    """
    current = get_current_timestamp()
    return current - timestamp


def format_timestamp(timestamp: int, format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Format a Unix timestamp as a human-readable string.

    Args:
        timestamp: Unix timestamp to format
        format_str: strftime format string (default: ISO-like with timezone)

    Returns:
        str: Formatted timestamp string

    Example:
        >>> ts = 1700000000
        >>> formatted = format_timestamp(ts)
        >>> "2023" in formatted
        True
    """
    dt = timestamp_to_datetime(timestamp)
    return dt.strftime(format_str)


def parse_timestamp(timestamp_str: str) -> Optional[int]:
    """Parse a timestamp string to Unix timestamp.

    Supports multiple formats:
    - Unix timestamp as string: "1700000000"
    - ISO 8601: "2023-11-14T12:00:00Z" or "2023-11-14T12:00:00+00:00"

    Args:
        timestamp_str: Timestamp string to parse

    Returns:
        Optional[int]: Parsed Unix timestamp, or None if parsing fails

    Example:
        >>> parse_timestamp("1700000000")
        1700000000
        >>> parse_timestamp("2023-11-14T22:13:20+00:00") == 1700000000
        True
    """
    try:
        # Try parsing as integer first
        return int(timestamp_str)
    except ValueError:
        pass

    try:
        # Try parsing as ISO 8601 datetime
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        return datetime_to_timestamp(dt)
    except (ValueError, AttributeError):
        return None
