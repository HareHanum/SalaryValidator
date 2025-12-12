"""Hebrew text utilities for payslip parsing."""

import re
import unicodedata
from typing import Optional

# Hebrew month names mapping
HEBREW_MONTHS = {
    "ינואר": 1,
    "פברואר": 2,
    "מרץ": 3,
    "מרס": 3,
    "אפריל": 4,
    "מאי": 5,
    "יוני": 6,
    "יולי": 7,
    "אוגוסט": 8,
    "ספטמבר": 9,
    "אוקטובר": 10,
    "נובמבר": 11,
    "דצמבר": 12,
}

# Hebrew number words (for edge cases)
HEBREW_NUMBERS = {
    "אפס": 0,
    "אחת": 1,
    "אחד": 1,
    "שתיים": 2,
    "שניים": 2,
    "שלוש": 3,
    "שלושה": 3,
    "ארבע": 4,
    "ארבעה": 4,
    "חמש": 5,
    "חמישה": 5,
    "שש": 6,
    "שישה": 6,
    "שבע": 7,
    "שבעה": 7,
    "שמונה": 8,
    "תשע": 9,
    "תשעה": 9,
    "עשר": 10,
    "עשרה": 10,
}

# Common Hebrew payslip field labels
FIELD_LABELS = {
    # Salary components
    "שכר בסיס": "base_salary",
    "שכר יסוד": "base_salary",
    "משכורת בסיס": "base_salary",
    "שכר חודשי": "base_salary",
    "שעות עבודה": "hours_worked",
    "שעות רגילות": "hours_worked",
    "סה\"כ שעות": "hours_worked",
    "שכר שעתי": "hourly_rate",
    "תעריף שעתי": "hourly_rate",
    "שעות נוספות": "overtime_hours",
    "תוספת שעות נוספות": "overtime_pay",
    "גמול שעות נוספות": "overtime_pay",
    "שעות שבת": "weekend_hours",
    "תוספת שבת": "weekend_pay",
    "גמול שבת": "weekend_pay",
    "ימי חופשה": "vacation_days",
    "דמי חופשה": "vacation_pay",
    "פדיון חופשה": "vacation_pay",
    "בונוס": "bonus",
    "מענק": "bonus",
    "פרמיה": "bonus",

    # Deductions
    "מס הכנסה": "income_tax",
    "ביטוח לאומי": "national_insurance",
    "דמי בריאות": "health_insurance",
    "ביטוח בריאות": "health_insurance",
    "פנסיה עובד": "pension_employee",
    "הפרשת עובד לפנסיה": "pension_employee",
    "פנסיה מעביד": "pension_employer",
    "הפרשת מעביד לפנסיה": "pension_employer",
    "קרן השתלמות": "provident_fund",

    # Totals
    "שכר ברוטו": "gross_salary",
    "סה\"כ ברוטו": "gross_salary",
    "סך הכל ברוטו": "gross_salary",
    "שכר נטו": "net_salary",
    "סה\"כ נטו": "net_salary",
    "סך הכל נטו": "net_salary",
    "לתשלום": "net_salary",
    "נטו לתשלום": "net_salary",
}


def normalize_hebrew_text(text: str) -> str:
    """
    Normalize Hebrew text for consistent processing.

    Args:
        text: Raw Hebrew text

    Returns:
        Normalized text
    """
    # Normalize Unicode characters
    text = unicodedata.normalize("NFC", text)

    # Remove Hebrew diacritics (niqqud)
    text = re.sub(r'[\u0591-\u05C7]', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove zero-width characters
    text = re.sub(r'[\u200b-\u200f\u2028-\u202f]', '', text)

    return text.strip()


def extract_hebrew_month(text: str) -> Optional[int]:
    """
    Extract month number from Hebrew month name.

    Args:
        text: Text containing Hebrew month name

    Returns:
        Month number (1-12) or None
    """
    normalized = normalize_hebrew_text(text.lower())

    for month_name, month_num in HEBREW_MONTHS.items():
        if month_name in normalized:
            return month_num

    return None


def is_hebrew_text(text: str) -> bool:
    """
    Check if text contains Hebrew characters.

    Args:
        text: Text to check

    Returns:
        True if text contains Hebrew
    """
    hebrew_pattern = re.compile(r'[\u0590-\u05FF]')
    return bool(hebrew_pattern.search(text))


def reverse_hebrew_numbers(text: str) -> str:
    """
    Fix reversed numbers that can occur in RTL text processing.

    Some OCR engines may reverse number sequences in Hebrew text.
    This function attempts to detect and fix such cases.

    Args:
        text: Text with potentially reversed numbers

    Returns:
        Text with corrected number order
    """
    # Pattern to find numbers that might be reversed (e.g., "05.23" should be "32.50")
    # This is a heuristic and may need adjustment based on actual OCR output

    def fix_decimal(match: re.Match) -> str:
        num = match.group(0)
        # Check if this looks like a reversed decimal
        # e.g., "05.23" with leading zero after decimal might be reversed
        if '.' in num:
            parts = num.split('.')
            if len(parts) == 2:
                # If integer part starts with 0 and decimal part doesn't end with 0
                # it might be reversed
                if parts[0].startswith('0') and len(parts[0]) > 1:
                    return num[::-1].replace('.', '', 1)[::-1]
        return num

    # This is a conservative approach - only fix obvious cases
    return text


def extract_field_label(text: str) -> Optional[str]:
    """
    Extract standardized field name from Hebrew label.

    Args:
        text: Hebrew field label

    Returns:
        Standardized field name or None
    """
    normalized = normalize_hebrew_text(text)

    for hebrew_label, field_name in FIELD_LABELS.items():
        if hebrew_label in normalized:
            return field_name

    return None


def clean_ocr_artifacts(text: str) -> str:
    """
    Clean common OCR artifacts from text.

    Args:
        text: Raw OCR text

    Returns:
        Cleaned text
    """
    # Remove common OCR noise characters
    text = re.sub(r'[|\\]', '', text)

    # Fix common OCR mistakes in Hebrew
    replacements = {
        'ו0': 'ו',  # Zero confused with vav
        '0ו': 'ו',
        'יי': 'י',  # Double yod
        'וו': 'ו',  # Double vav
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove isolated single characters that are likely noise
    text = re.sub(r'\s[א-ת]\s', ' ', text)

    return text
