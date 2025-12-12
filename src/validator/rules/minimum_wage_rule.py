"""Minimum wage validation rule."""

from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger
from src.models import Payslip, Violation, ViolationType
from src.validator.base import ValidationRule, ViolationSeverity
from src.validator.labor_law_data import get_minimum_wage

logger = get_logger("validator.rules.minimum_wage")


class MinimumWageRule(ValidationRule):
    """
    Validates that the hourly wage meets or exceeds the legal minimum.

    Israeli law requires employers to pay at least the minimum wage
    as set by the Ministry of Economy and Industry.
    """

    @property
    def name(self) -> str:
        return "Minimum Wage Compliance"

    @property
    def description(self) -> str:
        return "Checks if hourly wage meets the legal minimum wage for the pay period"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.MINIMUM_WAGE

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.CRITICAL

    @property
    def legal_reference(self) -> Optional[str]:
        return "חוק שכר מינימום, התשמ\"ז-1987"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """
        Validate hourly wage against minimum wage.

        Args:
            payslip: The payslip to validate

        Returns:
            Violation if wage is below minimum, None otherwise
        """
        # Get minimum wage for the payslip period
        min_wage = get_minimum_wage(payslip.payslip_date)

        # Compare hourly rates
        if payslip.hourly_rate < min_wage.hourly_wage:
            # Calculate missing amount
            hours = payslip.hours_worked
            expected_pay = min_wage.hourly_wage * hours
            actual_pay = payslip.hourly_rate * hours
            missing_amount = expected_pay - actual_pay

            # Create Hebrew explanation
            hebrew_desc = (
                f"שולם שכר שעתי של {payslip.hourly_rate:.2f} ש\"ח לשעה. "
                f"שכר המינימום החוקי לתקופה זו הוא {min_wage.hourly_wage:.2f} ש\"ח לשעה. "
                f"עבדת {hours:.1f} שעות, ולכן חסרים {missing_amount:.2f} ש\"ח."
            )

            english_desc = (
                f"Paid {payslip.hourly_rate:.2f} ILS/hour, "
                f"below minimum wage of {min_wage.hourly_wage:.2f} ILS/hour. "
                f"For {hours:.1f} hours worked, missing {missing_amount:.2f} ILS."
            )

            logger.info(
                f"Minimum wage violation: {payslip.hourly_rate} < {min_wage.hourly_wage} "
                f"(missing: {missing_amount})"
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_pay,
                actual_value=actual_pay,
                missing_amount=missing_amount,
                legal_reference=self.legal_reference,
            )

        logger.debug(
            f"Minimum wage check passed: {payslip.hourly_rate} >= {min_wage.hourly_wage}"
        )
        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """Check if we have enough data to validate."""
        return payslip.hourly_rate > 0 and payslip.hours_worked > 0


class MonthlyMinimumWageRule(ValidationRule):
    """
    Validates that the monthly gross salary meets minimum wage requirements.

    This is an alternative check for salaried employees who may not have
    explicit hourly rates.
    """

    @property
    def name(self) -> str:
        return "Monthly Minimum Wage Compliance"

    @property
    def description(self) -> str:
        return "Checks if monthly salary meets minimum wage for full-time work"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.MINIMUM_WAGE

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.CRITICAL

    @property
    def legal_reference(self) -> Optional[str]:
        return "חוק שכר מינימום, התשמ\"ז-1987"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """
        Validate monthly salary against minimum wage.

        Args:
            payslip: The payslip to validate

        Returns:
            Violation if salary is below minimum for hours worked, None otherwise
        """
        min_wage = get_minimum_wage(payslip.payslip_date)

        # Calculate what minimum wage should be for hours worked
        # Using proportional calculation (hours worked / 182 * monthly minimum)
        standard_hours = Decimal("182")
        proportion = payslip.hours_worked / standard_hours
        expected_minimum = (min_wage.monthly_wage * proportion).quantize(Decimal("0.01"))

        if payslip.gross_salary < expected_minimum:
            missing_amount = expected_minimum - payslip.gross_salary

            hebrew_desc = (
                f"השכר החודשי ברוטו ({payslip.gross_salary:.2f} ש\"ח) "
                f"נמוך משכר המינימום הנדרש ({expected_minimum:.2f} ש\"ח) "
                f"עבור {payslip.hours_worked:.1f} שעות עבודה. "
                f"חסרים {missing_amount:.2f} ש\"ח."
            )

            english_desc = (
                f"Monthly gross salary ({payslip.gross_salary:.2f} ILS) "
                f"is below required minimum ({expected_minimum:.2f} ILS) "
                f"for {payslip.hours_worked:.1f} hours worked. "
                f"Missing {missing_amount:.2f} ILS."
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_minimum,
                actual_value=payslip.gross_salary,
                missing_amount=missing_amount,
                legal_reference=self.legal_reference,
            )

        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """Check if we have enough data to validate."""
        return payslip.gross_salary > 0 and payslip.hours_worked > 0
