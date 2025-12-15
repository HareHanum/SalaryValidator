"""Field extraction for Israeli payslips using LLM."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from src.config import get_settings
from src.logging_config import get_logger

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
    """Extracts structured fields from payslip text using LLM."""

    # Standard working hours per month in Israel
    STANDARD_MONTHLY_HOURS = Decimal("182")

    def __init__(self):
        """Initialize the field extractor."""
        pass

    def extract_fields(self, text: str) -> ExtractedFields:
        """
        Extract all fields from payslip text using LLM.

        Args:
            text: Raw payslip text from OCR

        Returns:
            ExtractedFields with populated values

        Raises:
            ValueError: If LLM extraction is not configured
        """
        logger.info(f"Raw OCR text (first 500 chars): {text[:500] if text else 'EMPTY'}")

        settings = get_settings()

        if not settings.anthropic_api_key:
            raise ValueError(
                "Anthropic API key not configured. "
                "Set ANTHROPIC_API_KEY in your .env file."
            )

        from src.parser.llm_extractor import LLMExtractor

        llm_extractor = LLMExtractor(
            api_key=settings.anthropic_api_key,
            model=settings.llm_model
        )

        fields = llm_extractor.extract_fields(text)

        # Calculate derived values if missing
        self._calculate_derived_values(fields)

        logger.info(
            f"Extracted - gross: {fields.gross_salary}, net: {fields.net_salary}, "
            f"base: {fields.base_salary}"
        )

        return fields

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

        # If still no hours, assume standard
        if fields.hours_worked is None:
            fields.hours_worked = self.STANDARD_MONTHLY_HOURS


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
