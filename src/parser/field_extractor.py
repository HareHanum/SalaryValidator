"""Field extraction patterns for Israeli payslips."""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger
from src.parser.hebrew_utils import FIELD_LABELS, clean_ocr_artifacts, normalize_hebrew_text
from src.parser.number_extractor import extract_currency_amount, extract_decimal, extract_hours

logger = get_logger("parser.field_extractor")


@dataclass
class ExtractedFields:
    """Container for extracted payslip fields."""

    # Compensation
    base_salary: Optional[Decimal] = None
    hours_worked: Optional[Decimal] = None
    hourly_rate: Optional[Decimal] = None
    overtime_hours: Optional[Decimal] = None
    overtime_pay: Optional[Decimal] = None
    weekend_hours: Optional[Decimal] = None
    weekend_pay: Optional[Decimal] = None
    vacation_days: Optional[Decimal] = None
    vacation_pay: Optional[Decimal] = None
    bonus: Optional[Decimal] = None

    # Deductions
    income_tax: Optional[Decimal] = None
    national_insurance: Optional[Decimal] = None
    health_insurance: Optional[Decimal] = None
    pension_employee: Optional[Decimal] = None
    pension_employer: Optional[Decimal] = None
    provident_fund: Optional[Decimal] = None

    # Totals
    gross_salary: Optional[Decimal] = None
    net_salary: Optional[Decimal] = None

    # Metadata
    employee_name: Optional[str] = None
    employer_name: Optional[str] = None
    employee_id: Optional[str] = None

    # Raw extracted values for debugging
    raw_extractions: dict = field(default_factory=dict)

    def set_field(self, field_name: str, value: Decimal) -> bool:
        """
        Set a field value if it's a valid field name.

        Args:
            field_name: Name of the field
            value: Value to set

        Returns:
            True if field was set
        """
        if hasattr(self, field_name) and field_name != "raw_extractions":
            setattr(self, field_name, value)
            return True
        return False


class FieldExtractor:
    """Extracts structured fields from payslip text."""

    # Patterns for specific fields
    FIELD_PATTERNS = {
        "base_salary": [
            r'שכר\s*(?:יסוד|בסיס)[:\s]*([₪\d,.\s]+)',
            r'משכורת\s*בסיס[:\s]*([₪\d,.\s]+)',
            r'base\s*salary[:\s]*([₪\d,.\s]+)',
        ],
        "hours_worked": [
            r'(?:סה"כ\s*)?שעות\s*(?:עבודה|רגילות)?[:\s]*(\d+(?:\.\d+)?)',
            r'שעות\s*חודשיות[:\s]*(\d+(?:\.\d+)?)',
            r'total\s*hours[:\s]*(\d+(?:\.\d+)?)',
        ],
        "hourly_rate": [
            r'(?:שכר|תעריף)\s*שעתי[:\s]*([₪\d,.\s]+)',
            r'hourly\s*rate[:\s]*([₪\d,.\s]+)',
        ],
        "overtime_hours": [
            r'שעות\s*נוספות[:\s]*(\d+(?:\.\d+)?)',
            r'overtime\s*hours[:\s]*(\d+(?:\.\d+)?)',
        ],
        "overtime_pay": [
            r'(?:גמול|תוספת)\s*שעות\s*נוספות[:\s]*([₪\d,.\s]+)',
            r'overtime\s*pay[:\s]*([₪\d,.\s]+)',
        ],
        "gross_salary": [
            r'(?:סה"כ|סך\s*הכל)?\s*(?:שכר\s*)?ברוטו[:\s]*([₪\d,.\s]+)',
            r'gross\s*(?:salary|pay)[:\s]*([₪\d,.\s]+)',
        ],
        "net_salary": [
            r'(?:סה"כ|סך\s*הכל)?\s*(?:שכר\s*)?נטו[:\s]*([₪\d,.\s]+)',
            r'(?:נטו\s*)?לתשלום[:\s]*([₪\d,.\s]+)',
            r'net\s*(?:salary|pay)[:\s]*([₪\d,.\s]+)',
        ],
        "income_tax": [
            r'מס\s*הכנסה[:\s]*([₪\d,.\s]+)',
            r'income\s*tax[:\s]*([₪\d,.\s]+)',
        ],
        "national_insurance": [
            r'ביטוח\s*לאומי[:\s]*([₪\d,.\s]+)',
            r'national\s*insurance[:\s]*([₪\d,.\s]+)',
        ],
        "health_insurance": [
            r'(?:דמי|ביטוח)\s*בריאות[:\s]*([₪\d,.\s]+)',
            r'health\s*insurance[:\s]*([₪\d,.\s]+)',
        ],
        "pension_employee": [
            r'(?:פנסיה|הפרשת)\s*עובד[:\s]*([₪\d,.\s]+)',
            r'employee\s*pension[:\s]*([₪\d,.\s]+)',
        ],
        "pension_employer": [
            r'(?:פנסיה|הפרשת)\s*מעביד[:\s]*([₪\d,.\s]+)',
            r'employer\s*pension[:\s]*([₪\d,.\s]+)',
        ],
        "provident_fund": [
            r'קרן\s*השתלמות[:\s]*([₪\d,.\s]+)',
            r'provident\s*fund[:\s]*([₪\d,.\s]+)',
        ],
    }

    # Patterns for metadata
    METADATA_PATTERNS = {
        "employee_name": [
            r'שם\s*(?:העובד|עובד)[:\s]*([א-ת\s]+)',
            r'employee\s*name[:\s]*(\w[\w\s]+)',
        ],
        "employer_name": [
            r'שם\s*(?:המעסיק|מעסיק|חברה)[:\s]*([א-ת\w\s]+)',
            r'employer[:\s]*(\w[\w\s]+)',
            r'company[:\s]*(\w[\w\s]+)',
        ],
        "employee_id": [
            r'(?:ת\.?ז\.?|תעודת\s*זהות)[:\s]*(\d{9})',
            r'(?:מספר\s*)?עובד[:\s]*(\d+)',
            r'employee\s*(?:id|number)[:\s]*(\d+)',
        ],
    }

    def __init__(self):
        """Initialize the field extractor."""
        self.compiled_patterns = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        for field_name, patterns in self.FIELD_PATTERNS.items():
            self.compiled_patterns[field_name] = [
                re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns
            ]

        for field_name, patterns in self.METADATA_PATTERNS.items():
            self.compiled_patterns[field_name] = [
                re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns
            ]

    def extract_fields(self, text: str) -> ExtractedFields:
        """
        Extract all fields from payslip text.

        Args:
            text: Raw payslip text from OCR

        Returns:
            ExtractedFields with populated values
        """
        # Log first 500 chars of raw text for debugging
        logger.info(f"Raw OCR text (first 500 chars): {text[:500] if text else 'EMPTY'}")

        # Normalize and clean the text
        text = clean_ocr_artifacts(text)
        normalized = normalize_hebrew_text(text)

        fields = ExtractedFields()

        # Extract using regex patterns
        self._extract_with_patterns(normalized, fields)

        # Extract using line-by-line analysis
        self._extract_from_lines(normalized, fields)

        # Try to calculate missing values
        self._calculate_derived_values(fields)

        # Log extracted salary fields for debugging
        logger.info(f"Extracted salaries - gross: {fields.gross_salary}, net: {fields.net_salary}, base: {fields.base_salary}")
        logger.debug(f"All extracted fields: {fields}")
        return fields

    def _extract_with_patterns(self, text: str, fields: ExtractedFields) -> None:
        """Extract fields using compiled regex patterns."""
        for field_name, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    value_str = match.group(1)

                    # Handle numeric vs string fields
                    if field_name in ["employee_name", "employer_name", "employee_id"]:
                        if field_name == "employee_id":
                            setattr(fields, field_name, value_str.strip())
                        else:
                            setattr(fields, field_name, value_str.strip())
                    else:
                        # Extract numeric value
                        if "hours" in field_name or "days" in field_name:
                            value = extract_hours(value_str)
                            if value is None:
                                value = extract_decimal(value_str)
                        else:
                            value = extract_currency_amount(value_str)
                            if value is None:
                                value = extract_decimal(value_str)

                        if value is not None:
                            fields.set_field(field_name, value)
                            fields.raw_extractions[field_name] = value_str

                    break  # Found a match, move to next field

    def _extract_from_lines(self, text: str, fields: ExtractedFields) -> None:
        """Extract fields by analyzing individual lines."""
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to match line against known field labels
            for hebrew_label, field_name in FIELD_LABELS.items():
                if hebrew_label in line:
                    # Extract the value from this line
                    value = extract_currency_amount(line)
                    if value is None:
                        value = extract_decimal(line)

                    if value is not None and getattr(fields, field_name, None) is None:
                        fields.set_field(field_name, value)
                        fields.raw_extractions[f"{field_name}_line"] = line

    def _calculate_derived_values(self, fields: ExtractedFields) -> None:
        """Calculate values that can be derived from other fields."""
        # Calculate hourly rate if we have base salary and hours
        if fields.hourly_rate is None and fields.base_salary and fields.hours_worked:
            if fields.hours_worked > 0:
                fields.hourly_rate = fields.base_salary / fields.hours_worked

        # Calculate base salary if we have hourly rate and hours
        if fields.base_salary is None and fields.hourly_rate and fields.hours_worked:
            fields.base_salary = fields.hourly_rate * fields.hours_worked

        # Estimate hours if we have base salary and hourly rate
        if fields.hours_worked is None and fields.base_salary and fields.hourly_rate:
            if fields.hourly_rate > 0:
                fields.hours_worked = fields.base_salary / fields.hourly_rate


def extract_payslip_fields(text: str) -> ExtractedFields:
    """
    Convenience function to extract fields from payslip text.

    Args:
        text: Raw payslip text from OCR

    Returns:
        ExtractedFields with populated values
    """
    extractor = FieldExtractor()
    return extractor.extract_fields(text)
