"""Pension contribution validation rule."""

from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger
from src.models import Payslip, Violation, ViolationType
from src.validator.base import ValidationRule, ViolationSeverity
from src.validator.labor_law_data import get_pension_rates

logger = get_logger("validator.rules.pension")


class PensionContributionRule(ValidationRule):
    """
    Validates that pension contributions are being made.

    Israeli law (צו הרחבה לפנסיה חובה) requires mandatory pension
    contributions for most employees after a qualifying period.
    """

    # Tolerance for rounding differences
    TOLERANCE_PERCENT = Decimal("0.005")  # 0.5%

    @property
    def name(self) -> str:
        return "Pension Contribution"

    @property
    def description(self) -> str:
        return "Checks if mandatory pension contributions are being made"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.MISSING_PENSION

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.HIGH

    @property
    def legal_reference(self) -> Optional[str]:
        return "צו הרחבה לביטוח פנסיוני מקיף במשק, 2008"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """
        Validate pension contribution presence.

        Args:
            payslip: The payslip to validate

        Returns:
            Violation if pension contribution is missing or insufficient, None otherwise
        """
        # Get required pension rates
        rates = get_pension_rates(payslip.payslip_date)

        # Calculate expected minimum employee contribution
        pension_base = payslip.gross_salary  # Simplified - actual base may differ
        expected_employee = (pension_base * rates.employee_rate).quantize(Decimal("0.01"))

        actual_employee = payslip.deductions.pension_employee

        # Check if pension contribution exists
        if actual_employee == 0:
            # Complete absence of pension contribution
            hebrew_desc = (
                f"לא נוכתה הפרשה לפנסיה מהשכר. "
                f"על פי החוק, יש להפריש לפחות {rates.employee_rate * 100:.1f}% משכר העובד לפנסיה. "
                f"עבור שכר ברוטו של {payslip.gross_salary:.2f} ש\"ח, "
                f"ההפרשה הנדרשת היא {expected_employee:.2f} ש\"ח."
            )
            english_desc = (
                f"No pension contribution deducted. "
                f"By law, at least {rates.employee_rate * 100:.1f}% must be contributed. "
                f"For gross salary of {payslip.gross_salary:.2f} ILS, "
                f"required contribution is {expected_employee:.2f} ILS."
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_employee,
                actual_value=Decimal("0"),
                missing_amount=expected_employee,
                legal_reference=self.legal_reference,
            )

        # Check if contribution is sufficient
        min_expected = expected_employee * (1 - self.TOLERANCE_PERCENT)

        if actual_employee < min_expected:
            missing_amount = expected_employee - actual_employee

            hebrew_desc = (
                f"הפרשת העובד לפנסיה ({actual_employee:.2f} ש\"ח) נמוכה מהנדרש. "
                f"השיעור החוקי הוא {rates.employee_rate * 100:.1f}% = {expected_employee:.2f} ש\"ח. "
                f"חסרים {missing_amount:.2f} ש\"ח."
            )
            english_desc = (
                f"Employee pension contribution ({actual_employee:.2f} ILS) below required. "
                f"Legal rate is {rates.employee_rate * 100:.1f}% = {expected_employee:.2f} ILS. "
                f"Missing {missing_amount:.2f} ILS."
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_employee,
                actual_value=actual_employee,
                missing_amount=missing_amount,
                legal_reference=self.legal_reference,
            )

        logger.debug(
            f"Pension check passed: {actual_employee} >= {min_expected} "
            f"({rates.employee_rate * 100:.1f}%)"
        )
        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """
        Check if pension validation is applicable.

        Note: Pension is mandatory after 6 months of employment,
        but we can't determine tenure from a single payslip.
        """
        return payslip.gross_salary > 0


class EmployerPensionRule(ValidationRule):
    """
    Validates employer's pension contribution.

    Employers must contribute at least 6.5% of salary to pension.
    """

    TOLERANCE_PERCENT = Decimal("0.005")

    @property
    def name(self) -> str:
        return "Employer Pension Contribution"

    @property
    def description(self) -> str:
        return "Checks if employer pension contribution is shown and sufficient"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.MISSING_PENSION

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.MEDIUM

    @property
    def legal_reference(self) -> Optional[str]:
        return "צו הרחבה לביטוח פנסיוני מקיף במשק, 2008"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """
        Validate employer pension contribution.

        Note: Employer contribution may not always appear on payslip,
        so we only validate if it's present but insufficient.
        """
        rates = get_pension_rates(payslip.payslip_date)

        # If employer contribution is shown
        if payslip.deductions.pension_employer > 0:
            expected_employer = (payslip.gross_salary * rates.employer_rate).quantize(
                Decimal("0.01")
            )
            min_expected = expected_employer * (1 - self.TOLERANCE_PERCENT)

            if payslip.deductions.pension_employer < min_expected:
                missing_amount = expected_employer - payslip.deductions.pension_employer

                hebrew_desc = (
                    f"הפרשת המעסיק לפנסיה ({payslip.deductions.pension_employer:.2f} ש\"ח) "
                    f"נמוכה מהנדרש ({expected_employer:.2f} ש\"ח = {rates.employer_rate * 100:.1f}%). "
                    f"חסרים {missing_amount:.2f} ש\"ח."
                )
                english_desc = (
                    f"Employer pension contribution ({payslip.deductions.pension_employer:.2f} ILS) "
                    f"below required ({expected_employer:.2f} ILS = {rates.employer_rate * 100:.1f}%). "
                    f"Missing {missing_amount:.2f} ILS."
                )

                return Violation(
                    violation_type=self.violation_type,
                    description=english_desc,
                    description_hebrew=hebrew_desc,
                    expected_value=expected_employer,
                    actual_value=payslip.deductions.pension_employer,
                    missing_amount=missing_amount,
                    legal_reference=self.legal_reference,
                )

        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """Only validate if employer contribution is shown on payslip."""
        return payslip.deductions.pension_employer > 0
