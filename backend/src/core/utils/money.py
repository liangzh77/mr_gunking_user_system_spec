"""Money calculation utilities for precise financial operations.

This module provides utilities for handling monetary amounts with precision,
using Decimal type to avoid floating-point arithmetic errors.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union


# Type alias for money inputs (accepts int, float, str, or Decimal)
MoneyInput = Union[int, float, str, Decimal]


def to_decimal(amount: MoneyInput) -> Decimal:
    """Convert various input types to Decimal for precise calculation.

    Args:
        amount: Amount to convert (int, float, str, or Decimal)

    Returns:
        Decimal: Precise decimal representation

    Raises:
        ValueError: If amount cannot be converted to Decimal

    Example:
        >>> to_decimal(100)
        Decimal('100')
        >>> to_decimal("99.99")
        Decimal('99.99')
    """
    try:
        return Decimal(str(amount))
    except Exception as e:
        raise ValueError(f"Cannot convert {amount} to Decimal: {e}") from e


def round_money(amount: MoneyInput, places: int = 2) -> Decimal:
    """Round a monetary amount to specified decimal places.

    Uses ROUND_HALF_UP (banker's rounding) for consistent behavior.

    Args:
        amount: Amount to round
        places: Number of decimal places (default: 2 for yuan/cents)

    Returns:
        Decimal: Rounded amount

    Example:
        >>> round_money("99.995")
        Decimal('100.00')
        >>> round_money("99.994")
        Decimal('99.99')
    """
    decimal_amount = to_decimal(amount)
    quantizer = Decimal(10) ** -places
    return decimal_amount.quantize(quantizer, rounding=ROUND_HALF_UP)


def add_money(*amounts: MoneyInput) -> Decimal:
    """Add multiple monetary amounts with precision.

    Args:
        *amounts: Variable number of amounts to add

    Returns:
        Decimal: Sum of all amounts, rounded to 2 decimal places

    Example:
        >>> add_money("10.50", "20.30", "5.20")
        Decimal('36.00')
    """
    total = sum(to_decimal(amount) for amount in amounts)
    return round_money(total)


def subtract_money(minuend: MoneyInput, subtrahend: MoneyInput) -> Decimal:
    """Subtract one monetary amount from another with precision.

    Args:
        minuend: Amount to subtract from
        subtrahend: Amount to subtract

    Returns:
        Decimal: Difference, rounded to 2 decimal places

    Example:
        >>> subtract_money("100.00", "30.50")
        Decimal('69.50')
    """
    result = to_decimal(minuend) - to_decimal(subtrahend)
    return round_money(result)


def multiply_money(amount: MoneyInput, multiplier: MoneyInput) -> Decimal:
    """Multiply a monetary amount by a factor with precision.

    Args:
        amount: Base amount
        multiplier: Multiplication factor

    Returns:
        Decimal: Product, rounded to 2 decimal places

    Example:
        >>> multiply_money("10.50", "3")
        Decimal('31.50')
        >>> multiply_money("99.99", "1.1")
        Decimal('109.99')
    """
    result = to_decimal(amount) * to_decimal(multiplier)
    return round_money(result)


def divide_money(
    dividend: MoneyInput, divisor: MoneyInput, places: int = 2
) -> Decimal:
    """Divide one monetary amount by another with precision.

    Args:
        dividend: Amount to divide
        divisor: Division factor
        places: Number of decimal places for result (default: 2)

    Returns:
        Decimal: Quotient, rounded to specified places

    Raises:
        ValueError: If divisor is zero

    Example:
        >>> divide_money("100.00", "3")
        Decimal('33.33')
        >>> divide_money("100.00", "3", places=4)
        Decimal('33.3333')
    """
    divisor_decimal = to_decimal(divisor)
    if divisor_decimal == 0:
        raise ValueError("Cannot divide by zero")

    result = to_decimal(dividend) / divisor_decimal
    return round_money(result, places=places)


def is_positive(amount: MoneyInput) -> bool:
    """Check if a monetary amount is positive (greater than zero).

    Args:
        amount: Amount to check

    Returns:
        bool: True if amount > 0, False otherwise

    Example:
        >>> is_positive("100.00")
        True
        >>> is_positive("0")
        False
        >>> is_positive("-10.50")
        False
    """
    return to_decimal(amount) > 0


def is_negative(amount: MoneyInput) -> bool:
    """Check if a monetary amount is negative (less than zero).

    Args:
        amount: Amount to check

    Returns:
        bool: True if amount < 0, False otherwise

    Example:
        >>> is_negative("-10.50")
        True
        >>> is_negative("0")
        False
    """
    return to_decimal(amount) < 0


def is_zero(amount: MoneyInput) -> bool:
    """Check if a monetary amount is exactly zero.

    Args:
        amount: Amount to check

    Returns:
        bool: True if amount == 0, False otherwise

    Example:
        >>> is_zero("0")
        True
        >>> is_zero("0.00")
        True
        >>> is_zero("0.01")
        False
    """
    return to_decimal(amount) == 0


def compare_money(amount1: MoneyInput, amount2: MoneyInput) -> int:
    """Compare two monetary amounts.

    Args:
        amount1: First amount
        amount2: Second amount

    Returns:
        int: -1 if amount1 < amount2, 0 if equal, 1 if amount1 > amount2

    Example:
        >>> compare_money("100.00", "50.00")
        1
        >>> compare_money("50.00", "100.00")
        -1
        >>> compare_money("100.00", "100.00")
        0
    """
    dec1 = to_decimal(amount1)
    dec2 = to_decimal(amount2)

    if dec1 < dec2:
        return -1
    elif dec1 > dec2:
        return 1
    else:
        return 0


def format_money(amount: MoneyInput, symbol: str = "¥") -> str:
    """Format a monetary amount for display with currency symbol.

    Args:
        amount: Amount to format
        symbol: Currency symbol (default: "¥" for Chinese yuan)

    Returns:
        str: Formatted money string

    Example:
        >>> format_money("1234.56")
        '¥1,234.56'
        >>> format_money("1234.56", symbol="$")
        '$1,234.56'
    """
    rounded = round_money(amount)
    # Format with thousand separators
    formatted = f"{rounded:,.2f}"
    return f"{symbol}{formatted}"


def cents_to_yuan(cents: int) -> Decimal:
    """Convert cents (分) to yuan (元).

    Args:
        cents: Amount in cents

    Returns:
        Decimal: Amount in yuan

    Example:
        >>> cents_to_yuan(12345)
        Decimal('123.45')
    """
    return round_money(Decimal(cents) / 100)


def yuan_to_cents(yuan: MoneyInput) -> int:
    """Convert yuan (元) to cents (分).

    Args:
        yuan: Amount in yuan

    Returns:
        int: Amount in cents

    Example:
        >>> yuan_to_cents("123.45")
        12345
    """
    decimal_yuan = to_decimal(yuan)
    cents = decimal_yuan * 100
    return int(round_money(cents, places=0))
