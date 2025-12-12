"""Main payslip parser that combines OCR output into structured data."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from src.logging_config import get_logger
from src.models import Deductions, Payslip
from src.ocr import OCRResult, extract_text
from src.parser.date_parser import parse_payslip_date
from src.parser.field_extractor import ExtractedFields, extract_payslip_fields
from src.parser.hebrew_utils import is_hebrew_text

logger = get_logger("parser.payslip_parser")


class PayslipParseError(Exception):
    """Exception raised when payslip parsing fails."""

    pass


class PayslipParser:
    """Parser for converting OCR text into structured Payslip objects."""

    # Standard working hours per month in Israel
    STANDARD_MONTHLY_HOURS = Decimal("182")

    def __init__(self):
        """Initialize the payslip parser."""
        pass

    def parse_from_file(self, file_path: Path) -> Payslip:
        """
        Parse a payslip from an image or PDF file.

        Args:
            file_path: Path to the payslip file

        Returns:
            Parsed Payslip object

        Raises:
            PayslipParseError: If parsing fails
        """
        file_path = Path(file_path)
        logger.info(f"Parsing payslip from file: {file_path}")

        # Extract text using OCR
        try:
            ocr_result = extract_text(file_path)
        except Exception as e:
            raise PayslipParseError(f"OCR extraction failed: {e}") from e

        if ocr_result.is_empty:
            raise PayslipParseError("OCR extracted no text from file")

        # Parse the extracted text
        payslip = self.parse_from_text(ocr_result.text)
        payslip.source_file = str(file_path)
        payslip.raw_text = ocr_result.text
        payslip.confidence_score = ocr_result.confidence

        return payslip

    def parse_from_text(self, text: str) -> Payslip:
        """
        Parse a payslip from OCR text.

        Args:
            text: Raw text from OCR

        Returns:
            Parsed Payslip object

        Raises:
            PayslipParseError: If required fields cannot be extracted
        """
        logger.debug(f"Parsing payslip text ({len(text)} chars)")

        # Check if text contains Hebrew
        if not is_hebrew_text(text):
            logger.warning("Text does not contain Hebrew characters")

        # Extract fields from text
        extracted = extract_payslip_fields(text)

        # Extract date
        payslip_date = self._extract_date(text, extracted)

        # Validate and fill in required fields
        self._validate_extracted_fields(extracted)

        # Build the Payslip object
        payslip = self._build_payslip(extracted, payslip_date, text)

        return payslip

    def _extract_date(self, text: str, extracted: ExtractedFields) -> date:
        """Extract payslip date from text."""
        payslip_date = parse_payslip_date(text)

        if payslip_date is None:
            # Default to current month if no date found
            today = date.today()
            payslip_date = date(today.year, today.month, 1)
            logger.warning(f"Could not extract date, defaulting to: {payslip_date}")

        return payslip_date

    def _validate_extracted_fields(self, extracted: ExtractedFields) -> None:
        """
        Validate that we have minimum required fields to consider this a payslip.

        Raises:
            PayslipParseError: If the document doesn't appear to be a valid payslip
        """
        # Count how many payslip-specific fields we found
        payslip_indicators = 0

        # Salary fields (strong indicators)
        if extracted.gross_salary:
            payslip_indicators += 2
        if extracted.net_salary:
            payslip_indicators += 2
        if extracted.base_salary:
            payslip_indicators += 2
        if extracted.hourly_rate:
            payslip_indicators += 1

        # Deduction fields (strong indicators - these are payslip-specific)
        if extracted.income_tax:
            payslip_indicators += 2
        if extracted.national_insurance:
            payslip_indicators += 2
        if extracted.health_insurance:
            payslip_indicators += 2
        if extracted.pension_employee:
            payslip_indicators += 2
        if extracted.pension_employer:
            payslip_indicators += 1

        # Work-related fields
        if extracted.hours_worked:
            payslip_indicators += 1
        if extracted.overtime_hours or extracted.overtime_pay:
            payslip_indicators += 1

        # Require minimum threshold to consider it a payslip
        # Just need at least one salary field (gross, net, or base) to proceed
        has_salary = any([extracted.gross_salary, extracted.net_salary, extracted.base_salary])

        if not has_salary:
            raise PayslipParseError(
                "NOT_A_PAYSLIP"  # Error code for frontend translation
            )

        logger.info(f"Payslip validation passed: {payslip_indicators} indicators found, has_salary={has_salary}")

        # Try to infer missing critical fields only if we have a valid payslip
        if extracted.hours_worked is None:
            # Assume standard monthly hours
            extracted.hours_worked = self.STANDARD_MONTHLY_HOURS
            logger.info(f"Assuming standard hours: {self.STANDARD_MONTHLY_HOURS}")

        if extracted.hourly_rate is None and extracted.base_salary:
            extracted.hourly_rate = extracted.base_salary / extracted.hours_worked

        if extracted.base_salary is None and extracted.hourly_rate:
            extracted.base_salary = extracted.hourly_rate * extracted.hours_worked

    def _build_payslip(
        self, extracted: ExtractedFields, payslip_date: date, raw_text: str
    ) -> Payslip:
        """Build a Payslip object from extracted fields."""
        # Build deductions
        deductions = Deductions(
            income_tax=extracted.income_tax or Decimal("0"),
            national_insurance=extracted.national_insurance or Decimal("0"),
            health_insurance=extracted.health_insurance or Decimal("0"),
            pension_employee=extracted.pension_employee or Decimal("0"),
            pension_employer=extracted.pension_employer or Decimal("0"),
            provident_fund=extracted.provident_fund or Decimal("0"),
        )

        # Calculate gross if not provided
        gross_salary = extracted.gross_salary
        if gross_salary is None:
            gross_salary = self._calculate_gross(extracted)

        # Calculate net if not provided
        net_salary = extracted.net_salary
        if net_salary is None and gross_salary:
            net_salary = gross_salary - deductions.total

        # Ensure we have values for required fields
        base_salary = extracted.base_salary or gross_salary or Decimal("0")
        hours_worked = extracted.hours_worked or self.STANDARD_MONTHLY_HOURS
        hourly_rate = extracted.hourly_rate
        if hourly_rate is None and hours_worked > 0:
            hourly_rate = base_salary / hours_worked

        return Payslip(
            payslip_date=payslip_date,
            employee_name=extracted.employee_name,
            employer_name=extracted.employer_name,
            base_salary=base_salary,
            hours_worked=hours_worked,
            hourly_rate=hourly_rate or Decimal("0"),
            overtime_hours=extracted.overtime_hours or Decimal("0"),
            overtime_pay=extracted.overtime_pay or Decimal("0"),
            weekend_hours=extracted.weekend_hours or Decimal("0"),
            weekend_pay=extracted.weekend_pay or Decimal("0"),
            vacation_days=extracted.vacation_days or Decimal("0"),
            vacation_pay=extracted.vacation_pay or Decimal("0"),
            bonus=extracted.bonus or Decimal("0"),
            deductions=deductions,
            gross_salary=gross_salary or Decimal("0"),
            net_salary=net_salary or Decimal("0"),
            raw_text=raw_text,
        )

    def _calculate_gross(self, extracted: ExtractedFields) -> Optional[Decimal]:
        """Calculate gross salary from components."""
        if extracted.base_salary is None:
            return None

        gross = extracted.base_salary

        if extracted.overtime_pay:
            gross += extracted.overtime_pay
        if extracted.weekend_pay:
            gross += extracted.weekend_pay
        if extracted.vacation_pay:
            gross += extracted.vacation_pay
        if extracted.bonus:
            gross += extracted.bonus

        return gross


def parse_payslip(file_path: Path) -> Payslip:
    """
    Convenience function to parse a payslip file.

    Args:
        file_path: Path to the payslip file

    Returns:
        Parsed Payslip object
    """
    parser = PayslipParser()
    return parser.parse_from_file(file_path)


def parse_payslip_text(text: str) -> Payslip:
    """
    Convenience function to parse payslip text.

    Args:
        text: Raw text from OCR

    Returns:
        Parsed Payslip object
    """
    parser = PayslipParser()
    return parser.parse_from_text(text)
