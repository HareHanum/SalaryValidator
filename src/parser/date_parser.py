"""Date parsing utilities for Israeli payslips."""

import re
from datetime import date
from typing import Optional

from src.logging_config import get_logger
from src.parser.hebrew_utils import HEBREW_MONTHS, normalize_hebrew_text

logger = get_logger("parser.date_parser")

# English month names mapping
ENGLISH_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def parse_payslip_date(text: str) -> Optional[date]:
    """
    Parse date from payslip text. Tries multiple formats.

    Args:
        text: Text containing date information

    Returns:
        Parsed date (first day of month) or None
    """
    normalized = normalize_hebrew_text(text)

    # Try various parsing strategies
    parsers = [
        _parse_hebrew_month_year,
        _parse_english_month_year,
        _parse_numeric_month_year,
        _parse_full_date,
    ]

    for parser in parsers:
        result = parser(normalized)
        if result:
            logger.debug(f"Parsed date '{text}' -> {result}")
            return result

    logger.debug(f"Could not parse date from: {text}")
    return None


def _parse_hebrew_month_year(text: str) -> Optional[date]:
    """Parse Hebrew month name with year."""
    for month_name, month_num in HEBREW_MONTHS.items():
        if month_name in text:
            # Look for year near the month name
            year = _extract_year(text)
            if year:
                return date(year, month_num, 1)

    return None


def _parse_english_month_year(text: str) -> Optional[date]:
    """Parse English month name with year."""
    text_lower = text.lower()

    for month_name, month_num in ENGLISH_MONTHS.items():
        if month_name in text_lower:
            year = _extract_year(text)
            if year:
                return date(year, month_num, 1)

    return None


def _parse_numeric_month_year(text: str) -> Optional[date]:
    """Parse numeric month/year formats like MM/YYYY or MM-YYYY."""
    patterns = [
        # MM/YYYY or MM-YYYY
        r'(\d{1,2})[/\-](\d{4})',
        # YYYY/MM or YYYY-MM
        r'(\d{4})[/\-](\d{1,2})',
        # Month YYYY (just numbers)
        r'\b(\d{1,2})\s+(\d{4})\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            g1, g2 = match.groups()

            # Determine which is month and which is year
            if len(g1) == 4:
                year, month = int(g1), int(g2)
            elif len(g2) == 4:
                month, year = int(g1), int(g2)
            else:
                continue

            # Validate month
            if 1 <= month <= 12 and 2000 <= year <= 2100:
                return date(year, month, 1)

    return None


def _parse_full_date(text: str) -> Optional[date]:
    """Parse full date formats like DD/MM/YYYY."""
    patterns = [
        # DD/MM/YYYY or DD-MM-YYYY
        r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})',
        # YYYY/MM/DD or YYYY-MM-DD
        r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            parts = [int(p) for p in match.groups()]

            # Try DD/MM/YYYY format (common in Israel)
            if parts[2] > 1900:
                day, month, year = parts
            # Try YYYY/MM/DD format
            elif parts[0] > 1900:
                year, month, day = parts
            else:
                continue

            # Validate
            if 1 <= month <= 12 and 1 <= day <= 31 and 2000 <= year <= 2100:
                try:
                    # Return first of month for payslip purposes
                    return date(year, month, 1)
                except ValueError:
                    continue

    return None


def _extract_year(text: str) -> Optional[int]:
    """Extract a valid year from text."""
    # Look for 4-digit years
    years = re.findall(r'\b(20\d{2})\b', text)

    if years:
        # Return the most likely year (prefer recent years)
        return int(years[0])

    # Try 2-digit years
    two_digit = re.findall(r'\b(\d{2})\b', text)
    for y in two_digit:
        year = int(y)
        if 20 <= year <= 30:  # Assume 2020-2030
            return 2000 + year

    return None


def extract_pay_period(text: str) -> tuple[Optional[date], Optional[date]]:
    """
    Extract pay period start and end dates.

    Args:
        text: Text containing pay period information

    Returns:
        Tuple of (start_date, end_date)
    """
    # Look for patterns like "01/01/2024 - 31/01/2024" or "תקופה: 01/24 - 01/24"
    period_patterns = [
        r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s*[-–—]\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'(\d{1,2}[/\-]\d{2,4})\s*[-–—]\s*(\d{1,2}[/\-]\d{2,4})',
    ]

    for pattern in period_patterns:
        match = re.search(pattern, text)
        if match:
            start_str, end_str = match.groups()
            start_date = parse_payslip_date(start_str)
            end_date = parse_payslip_date(end_str)
            if start_date and end_date:
                return start_date, end_date

    # If only one date found, assume it's the pay period month
    single_date = parse_payslip_date(text)
    if single_date:
        # Return first and last day of that month
        if single_date.month == 12:
            end_date = date(single_date.year + 1, 1, 1)
        else:
            end_date = date(single_date.year, single_date.month + 1, 1)
        return single_date, end_date

    return None, None


def format_hebrew_date(d: date) -> str:
    """
    Format date in Hebrew.

    Args:
        d: Date to format

    Returns:
        Hebrew formatted date string
    """
    hebrew_month_names = {v: k for k, v in HEBREW_MONTHS.items()}
    month_name = hebrew_month_names.get(d.month, str(d.month))
    return f"{month_name} {d.year}"
