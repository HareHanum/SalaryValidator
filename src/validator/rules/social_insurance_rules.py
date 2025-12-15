"""Social insurance validation rules - National Insurance, Health Tax, Severance."""

from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger
from src.models import Payslip, Violation, ViolationType
from src.validator.base import ValidationRule, ViolationSeverity
from src.validator.labor_law_data import (
    calculate_expected_national_insurance,
    calculate_expected_health_tax,
    get_national_insurance_rates,
    get_health_tax_rates,
    SEVERANCE_FUND_RATE,
)

logger = get_logger("validator.rules.social_insurance")


class NationalInsuranceRule(ValidationRule):
    """
    Validates National Insurance (Bituach Leumi) deductions.

    Israeli law requires mandatory National Insurance contributions:
    - 0.4% on income up to 60% of average wage
    - 7% on income above that threshold (up to maximum insurable income)

    NOTE: This check only flags SIGNIFICANT underpayments. NI calculations are complex
    and depend on many factors not on payslips (e.g., exemptions, other income sources).
    Minor discrepancies are expected and overpayments are not flagged as violations.
    """

    # Higher tolerance for complex calculations - only flag significant underpayments
    TOLERANCE_PERCENT = Decimal("0.10")  # 10% tolerance - only flag major discrepancies

    @property
    def name(self) -> str:
        return "National Insurance"

    @property
    def name_hebrew(self) -> str:
        return "ביטוח לאומי"

    @property
    def description(self) -> str:
        return "Checks if National Insurance deductions match legal requirements"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.NATIONAL_INSURANCE_MISMATCH

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.MEDIUM

    @property
    def legal_reference(self) -> Optional[str]:
        return "חוק הביטוח הלאומי [נוסח משולב], התשנ\"ה-1995"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """
        Validate National Insurance deduction.

        Args:
            payslip: The payslip to validate

        Returns:
            Violation if NI deduction doesn't match expected, None otherwise
        """
        rates = get_national_insurance_rates(payslip.payslip_date)
        expected_ni = calculate_expected_national_insurance(
            payslip.gross_salary, payslip.payslip_date
        )
        actual_ni = payslip.deductions.national_insurance

        # Skip if no NI data on payslip
        if actual_ni == 0:
            return None

        # Check if within tolerance
        lower_bound = expected_ni * (1 - self.TOLERANCE_PERCENT)
        upper_bound = expected_ni * (1 + self.TOLERANCE_PERCENT)

        if actual_ni < lower_bound:
            # Significant underpayment - flag for review
            missing_amount = expected_ni - actual_ni

            hebrew_desc = (
                f"ניכוי ביטוח לאומי ({actual_ni:.2f} ש\"ח) נמוך משמעותית מהצפוי ({expected_ni:.2f} ש\"ח). "
                f"הפרש: {missing_amount:.2f} ש\"ח. "
                f"הערה: חישוב זה משוער - מומלץ לאמת מול חשב שכר."
            )
            english_desc = (
                f"National Insurance deduction ({actual_ni:.2f} ILS) significantly below expected ({expected_ni:.2f} ILS). "
                f"Difference: {missing_amount:.2f} ILS. "
                f"Note: This is an estimate - verify with payroll accountant."
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_ni,
                actual_value=actual_ni,
                missing_amount=missing_amount,
                legal_reference=self.legal_reference,
            )

        # Note: Overpayments are NOT flagged as violations - they're usually due to
        # factors not visible on the payslip (additional income, special circumstances)

        logger.debug(f"NI check passed: {actual_ni:.2f} within tolerance of {expected_ni:.2f}")
        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """Only validate if NI deduction is shown on payslip."""
        return payslip.deductions.national_insurance > 0


class HealthTaxRule(ValidationRule):
    """
    Validates Health Tax deductions.

    Israeli law requires Health Tax (מס בריאות) contributions:
    - 3.1% on income up to 60% of average wage
    - 5% on income above that threshold

    NOTE: This check only flags SIGNIFICANT underpayments. Health Tax calculations
    can vary due to factors not shown on payslips. Overpayments are not flagged.
    """

    TOLERANCE_PERCENT = Decimal("0.10")  # 10% tolerance - only flag major discrepancies

    @property
    def name(self) -> str:
        return "Health Tax"

    @property
    def name_hebrew(self) -> str:
        return "מס בריאות"

    @property
    def description(self) -> str:
        return "Checks if Health Tax deductions match legal requirements"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.HEALTH_TAX_MISMATCH

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.MEDIUM

    @property
    def legal_reference(self) -> Optional[str]:
        return "חוק ביטוח בריאות ממלכתי, התשנ\"ד-1994"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """Validate Health Tax deduction."""
        rates = get_health_tax_rates(payslip.payslip_date)
        expected_ht = calculate_expected_health_tax(
            payslip.gross_salary, payslip.payslip_date
        )
        actual_ht = payslip.deductions.health_insurance

        # Skip if no health tax data on payslip
        if actual_ht == 0:
            return None

        # Check if within tolerance
        lower_bound = expected_ht * (1 - self.TOLERANCE_PERCENT)
        upper_bound = expected_ht * (1 + self.TOLERANCE_PERCENT)

        if actual_ht < lower_bound:
            # Significant underpayment - flag for review
            missing_amount = expected_ht - actual_ht

            hebrew_desc = (
                f"ניכוי מס בריאות ({actual_ht:.2f} ש\"ח) נמוך משמעותית מהצפוי ({expected_ht:.2f} ש\"ח). "
                f"הפרש: {missing_amount:.2f} ש\"ח. "
                f"הערה: חישוב זה משוער - מומלץ לאמת מול חשב שכר."
            )
            english_desc = (
                f"Health Tax deduction ({actual_ht:.2f} ILS) significantly below expected ({expected_ht:.2f} ILS). "
                f"Difference: {missing_amount:.2f} ILS. "
                f"Note: This is an estimate - verify with payroll accountant."
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_ht,
                actual_value=actual_ht,
                missing_amount=missing_amount,
                legal_reference=self.legal_reference,
            )

        # Note: Overpayments are NOT flagged as violations - they may be due to
        # factors not visible on the payslip

        logger.debug(f"Health Tax check passed: {actual_ht:.2f} within tolerance of {expected_ht:.2f}")
        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """Only validate if Health Tax deduction is shown on payslip."""
        return payslip.deductions.health_insurance > 0


class SeveranceFundRule(ValidationRule):
    """
    Validates Severance Fund (קרן פיצויים) contributions.

    Under Section 14 arrangements, employers must contribute 8.33%
    of salary to a severance fund each month.
    """

    TOLERANCE_PERCENT = Decimal("0.01")  # 1% tolerance

    @property
    def name(self) -> str:
        return "Severance Fund"

    @property
    def name_hebrew(self) -> str:
        return "קרן פיצויים"

    @property
    def description(self) -> str:
        return "Checks if employer contributes 8.33% to severance fund"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.MISSING_SEVERANCE_FUND

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.HIGH

    @property
    def legal_reference(self) -> Optional[str]:
        return "חוק פיצויי פיטורים, התשכ\"ג-1963 (סעיף 14)"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """Validate severance fund contribution."""
        expected_severance = (payslip.gross_salary * SEVERANCE_FUND_RATE).quantize(Decimal("0.01"))
        actual_severance = payslip.severance_fund

        # Skip if no severance data on payslip
        if actual_severance == 0:
            return None

        min_expected = expected_severance * (1 - self.TOLERANCE_PERCENT)

        if actual_severance < min_expected:
            missing_amount = expected_severance - actual_severance

            hebrew_desc = (
                f"הפרשת המעסיק לפיצויים ({actual_severance:.2f} ש\"ח) נמוכה מהנדרש. "
                f"על פי סעיף 14, יש להפריש 8.33% = {expected_severance:.2f} ש\"ח. "
                f"חסרים {missing_amount:.2f} ש\"ח."
            )
            english_desc = (
                f"Employer severance contribution ({actual_severance:.2f} ILS) below required. "
                f"Under Section 14, 8.33% = {expected_severance:.2f} ILS required. "
                f"Missing {missing_amount:.2f} ILS."
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_severance,
                actual_value=actual_severance,
                missing_amount=missing_amount,
                legal_reference=self.legal_reference,
            )

        logger.debug(f"Severance fund check passed: {actual_severance:.2f} >= {min_expected:.2f}")
        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """Only validate if severance fund is shown on payslip."""
        return payslip.severance_fund > 0
