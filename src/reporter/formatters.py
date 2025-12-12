"""Formatting utilities for Hebrew reports."""

from datetime import date
from decimal import Decimal
from typing import Union

from src.reporter.templates import HEBREW_MONTHS


def format_currency(amount: Union[Decimal, float, int], symbol: str = "₪") -> str:
    """
    Format amount as Israeli currency.

    Args:
        amount: Amount to format
        symbol: Currency symbol (default: ₪)

    Returns:
        Formatted string (e.g., "₪1,234.56")
    """
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))

    # Format with 2 decimal places and thousands separator
    formatted = f"{amount:,.2f}"
    return f"{symbol}{formatted}"


def format_currency_plain(amount: Union[Decimal, float, int]) -> str:
    """
    Format amount without currency symbol.

    Args:
        amount: Amount to format

    Returns:
        Formatted string (e.g., "1,234.56")
    """
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))

    return f"{amount:,.2f}"


def format_number(value: Union[Decimal, float, int], decimals: int = 2) -> str:
    """
    Format a number with specified decimal places.

    Args:
        value: Number to format
        decimals: Number of decimal places

    Returns:
        Formatted string
    """
    if isinstance(value, (int, float)):
        value = Decimal(str(value))

    format_str = f"{{:,.{decimals}f}}"
    return format_str.format(value)


def format_percentage(value: Union[Decimal, float], decimals: int = 1) -> str:
    """
    Format a percentage value.

    Args:
        value: Percentage value (e.g., 85.5 for 85.5%)
        decimals: Number of decimal places

    Returns:
        Formatted string (e.g., "85.5%")
    """
    format_str = f"{{:.{decimals}f}}%"
    return format_str.format(float(value))


def format_hours(hours: Union[Decimal, float]) -> str:
    """
    Format hours value.

    Args:
        hours: Hours to format

    Returns:
        Formatted string (e.g., "182.5 שעות")
    """
    if isinstance(hours, float):
        hours = Decimal(str(hours))

    if hours == hours.to_integral_value():
        return f"{int(hours)} שעות"
    else:
        return f"{hours:.1f} שעות"


def format_date_hebrew(d: date) -> str:
    """
    Format date in Hebrew (e.g., "ינואר 2024").

    Args:
        d: Date to format

    Returns:
        Hebrew formatted date string
    """
    month_name = HEBREW_MONTHS.get(d.month, str(d.month))
    return f"{month_name} {d.year}"


def format_date_full_hebrew(d: date) -> str:
    """
    Format full date in Hebrew (e.g., "15 בינואר 2024").

    Args:
        d: Date to format

    Returns:
        Hebrew formatted full date string
    """
    month_name = HEBREW_MONTHS.get(d.month, str(d.month))
    return f"{d.day} ב{month_name} {d.year}"


def format_date_numeric(d: date) -> str:
    """
    Format date in numeric format (DD/MM/YYYY).

    Args:
        d: Date to format

    Returns:
        Numeric date string
    """
    return d.strftime("%d/%m/%Y")


def format_month_year(d: date) -> str:
    """
    Format month and year (MM/YYYY).

    Args:
        d: Date to format

    Returns:
        Month/year string
    """
    return d.strftime("%m/%Y")


def pluralize_hebrew(count: int, singular: str, plural: str) -> str:
    """
    Return singular or plural form based on count.

    Args:
        count: Number of items
        singular: Singular form
        plural: Plural form

    Returns:
        Appropriate form
    """
    if count == 1:
        return singular
    return plural


def format_violation_count(count: int) -> str:
    """
    Format violation count with proper Hebrew grammar.

    Args:
        count: Number of violations

    Returns:
        Formatted string
    """
    if count == 0:
        return "אין הפרות"
    elif count == 1:
        return "הפרה אחת"
    elif count == 2:
        return "2 הפרות"
    else:
        return f"{count} הפרות"


def format_payslip_count(count: int) -> str:
    """
    Format payslip count with proper Hebrew grammar.

    Args:
        count: Number of payslips

    Returns:
        Formatted string
    """
    if count == 0:
        return "אין תלושים"
    elif count == 1:
        return "תלוש אחד"
    elif count == 2:
        return "2 תלושים"
    else:
        return f"{count} תלושים"


def format_month_count(count: int) -> str:
    """
    Format month count with proper Hebrew grammar.

    Args:
        count: Number of months

    Returns:
        Formatted string
    """
    if count == 0:
        return "אין חודשים"
    elif count == 1:
        return "חודש אחד"
    elif count == 2:
        return "חודשיים"
    else:
        return f"{count} חודשים"


def wrap_rtl(text: str) -> str:
    """
    Wrap text with RTL markers for proper display.

    Args:
        text: Text to wrap

    Returns:
        Text with RTL markers
    """
    return f"\u200F{text}\u200F"


def create_separator(char: str = "-", length: int = 50) -> str:
    """
    Create a text separator line.

    Args:
        char: Character to use
        length: Length of separator

    Returns:
        Separator string
    """
    return char * length


def format_table_row(columns: list[str], widths: list[int]) -> str:
    """
    Format a table row with fixed column widths.

    Args:
        columns: Column values
        widths: Column widths

    Returns:
        Formatted row string
    """
    formatted = []
    for col, width in zip(columns, widths):
        # Right-align for Hebrew (RTL)
        formatted.append(str(col).rjust(width))
    return " | ".join(formatted)
