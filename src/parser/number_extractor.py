"""Number and currency extraction utilities."""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from src.logging_config import get_logger

logger = get_logger("parser.number_extractor")


# Israeli currency symbol
ILS_SYMBOLS = ["₪", "ש\"ח", "שח", "ש״ח", "NIS", "ILS"]

# Common patterns for numbers in Israeli payslips
NUMBER_PATTERNS = [
    # Standard decimal: 1,234.56 or 1234.56
    r'[\d,]+\.\d{1,2}',
    # European format: 1.234,56 or 1234,56
    r'[\d.]+,\d{1,2}',
    # Integer with commas: 1,234
    r'\d{1,3}(?:,\d{3})+',
    # Plain integer or decimal
    r'\d+(?:\.\d+)?',
]


def extract_decimal(text: str) -> Optional[Decimal]:
    """
    Extract a decimal number from text.

    Args:
        text: Text containing a number

    Returns:
        Decimal value or None
    """
    if not text:
        return None

    # Clean the text
    cleaned = text.strip()

    # Remove currency symbols
    for symbol in ILS_SYMBOLS:
        cleaned = cleaned.replace(symbol, "")

    cleaned = cleaned.strip()

    # Remove thousands separators and normalize decimal point
    # Israeli format typically uses comma for thousands, period for decimal
    # But some systems use European format (period for thousands, comma for decimal)

    # Check if this looks like European format (comma as decimal separator)
    if re.match(r'^\d{1,3}(?:\.\d{3})*,\d{1,2}$', cleaned):
        # European format: remove period thousands separators, replace comma with period
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        # Standard format: remove comma thousands separators
        cleaned = cleaned.replace(",", "")

    # Handle negative numbers
    is_negative = False
    if cleaned.startswith("-") or cleaned.startswith("("):
        is_negative = True
        cleaned = cleaned.lstrip("-").strip("()")

    # Remove any remaining non-numeric characters except decimal point
    cleaned = re.sub(r'[^\d.]', '', cleaned)

    if not cleaned:
        return None

    try:
        value = Decimal(cleaned)
        return -value if is_negative else value
    except InvalidOperation:
        logger.debug(f"Could not parse decimal from: {text}")
        return None


def extract_all_numbers(text: str) -> list[Decimal]:
    """
    Extract all numbers from text.

    Args:
        text: Text containing numbers

    Returns:
        List of Decimal values
    """
    numbers = []

    # Combine all patterns
    combined_pattern = '|'.join(f'({p})' for p in NUMBER_PATTERNS)

    for match in re.finditer(combined_pattern, text):
        num_str = match.group(0)
        value = extract_decimal(num_str)
        if value is not None:
            numbers.append(value)

    return numbers


def extract_currency_amount(text: str) -> Optional[Decimal]:
    """
    Extract a currency amount from text, looking for ILS symbols.

    Args:
        text: Text containing currency amount

    Returns:
        Decimal value or None
    """
    # Build pattern for currency amounts
    symbols_pattern = '|'.join(re.escape(s) for s in ILS_SYMBOLS)
    number_pattern = r'[\d,]+(?:\.\d{1,2})?'

    # Try: symbol before number (₪1,234.56)
    pattern1 = rf'(?:{symbols_pattern})\s*({number_pattern})'
    # Try: symbol after number (1,234.56 ש"ח)
    pattern2 = rf'({number_pattern})\s*(?:{symbols_pattern})'

    for pattern in [pattern1, pattern2]:
        match = re.search(pattern, text)
        if match:
            return extract_decimal(match.group(1))

    return None


def extract_hours(text: str) -> Optional[Decimal]:
    """
    Extract hours value from text.

    Args:
        text: Text containing hours

    Returns:
        Decimal hours value or None
    """
    # Common patterns for hours
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:שעות|שעה|hours?|hrs?)',
        r'(?:שעות|hours?)\s*[:=]?\s*(\d+(?:\.\d+)?)',
        r'(\d+(?::\d{2})?)\s*(?:שעות|שעה)',  # Format like 8:30
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hours_str = match.group(1)

            # Handle time format (8:30 -> 8.5)
            if ':' in hours_str:
                parts = hours_str.split(':')
                hours = Decimal(parts[0])
                minutes = Decimal(parts[1]) / 60
                return hours + minutes

            return extract_decimal(hours_str)

    return None


def extract_percentage(text: str) -> Optional[Decimal]:
    """
    Extract a percentage value from text.

    Args:
        text: Text containing percentage

    Returns:
        Decimal value (as fraction, e.g., 0.065 for 6.5%)
    """
    # Pattern for percentage
    pattern = r'(\d+(?:\.\d+)?)\s*%'

    match = re.search(pattern, text)
    if match:
        value = extract_decimal(match.group(1))
        if value is not None:
            return value / 100

    return None


def format_ils(amount: Decimal) -> str:
    """
    Format a decimal amount as Israeli Shekels.

    Args:
        amount: Amount to format

    Returns:
        Formatted string (e.g., "₪1,234.56")
    """
    # Format with 2 decimal places and thousands separator
    formatted = f"{amount:,.2f}"
    return f"₪{formatted}"


def parse_salary_line(line: str) -> tuple[Optional[str], Optional[Decimal]]:
    """
    Parse a single line from a payslip to extract label and value.

    Args:
        line: Single line of payslip text

    Returns:
        Tuple of (label, value) - either may be None
    """
    # Common separators in payslips
    separators = [':', '-', '–', '—', '\t', '  ']

    for sep in separators:
        if sep in line:
            parts = line.split(sep, 1)
            if len(parts) == 2:
                label = parts[0].strip()
                value_str = parts[1].strip()

                # Extract number from value part
                value = extract_currency_amount(value_str)
                if value is None:
                    value = extract_decimal(value_str)

                if label and value is not None:
                    return label, value

    # Try to find a number at the end of the line
    numbers = extract_all_numbers(line)
    if numbers:
        # Assume the last number is the value
        value = numbers[-1]
        # Remove the number from the line to get the label
        label = re.sub(r'[\d,.\s₪]+$', '', line).strip()
        if label:
            return label, value

    return None, None
