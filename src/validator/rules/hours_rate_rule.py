"""Hours × Rate verification rule."""

from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger
from src.models import Payslip, Violation, ViolationType
from src.validator.base import ValidationRule, ViolationSeverity

logger = get_logger("validator.rules.hours_rate")


class HoursRateRule(ValidationRule):
    """
    Validates that base salary matches hours × hourly rate.

    This rule checks for calculation errors where the base salary
    doesn't match what would be expected from the reported hours
    and hourly rate.
    """

    # Tolerance for rounding differences (in percentage)
    TOLERANCE_PERCENT = Decimal("0.01")  # 1% tolerance

    @property
    def name(self) -> str:
        return "Hours × Rate Verification"

    @property
    def description(self) -> str:
        return "Verifies that base salary equals hours worked × hourly rate"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.HOURS_RATE_MISMATCH

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.HIGH

    @property
    def legal_reference(self) -> Optional[str]:
        return "חוק הגנת השכר, התשי\"ח-1958"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """
        Validate that base salary matches hours × rate calculation.

        Args:
            payslip: The payslip to validate

        Returns:
            Violation if calculation doesn't match, None otherwise
        """
        # Calculate expected base salary
        expected_base = (payslip.hours_worked * payslip.hourly_rate).quantize(Decimal("0.01"))
        actual_base = payslip.base_salary

        # Calculate the difference
        difference = expected_base - actual_base

        # Check if difference exceeds tolerance
        tolerance_amount = expected_base * self.TOLERANCE_PERCENT

        if abs(difference) > tolerance_amount and abs(difference) > Decimal("1"):
            # Determine if underpaid or overpaid
            if difference > 0:
                # Underpaid
                hebrew_desc = (
                    f"שכר הבסיס ({actual_base:.2f} ש\"ח) אינו תואם לחישוב "
                    f"שעות × תעריף ({payslip.hours_worked:.1f} × {payslip.hourly_rate:.2f} = "
                    f"{expected_base:.2f} ש\"ח). "
                    f"חסרים {difference:.2f} ש\"ח."
                )
                english_desc = (
                    f"Base salary ({actual_base:.2f} ILS) doesn't match "
                    f"hours × rate ({payslip.hours_worked:.1f} × {payslip.hourly_rate:.2f} = "
                    f"{expected_base:.2f} ILS). "
                    f"Underpaid by {difference:.2f} ILS."
                )
                missing_amount = difference
            else:
                # Overpaid (still a mismatch, but not a violation in employee's favor)
                # We still report it as it indicates a calculation error
                hebrew_desc = (
                    f"שכר הבסיס ({actual_base:.2f} ש\"ח) אינו תואם לחישוב "
                    f"שעות × תעריף ({payslip.hours_worked:.1f} × {payslip.hourly_rate:.2f} = "
                    f"{expected_base:.2f} ש\"ח). "
                    f"הפרש של {abs(difference):.2f} ש\"ח (לטובת העובד)."
                )
                english_desc = (
                    f"Base salary ({actual_base:.2f} ILS) doesn't match "
                    f"hours × rate ({payslip.hours_worked:.1f} × {payslip.hourly_rate:.2f} = "
                    f"{expected_base:.2f} ILS). "
                    f"Difference of {abs(difference):.2f} ILS (in employee's favor)."
                )
                missing_amount = Decimal("0")  # No missing amount if overpaid

            logger.info(
                f"Hours×Rate mismatch: {actual_base} != {expected_base} "
                f"(diff: {difference})"
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_base,
                actual_value=actual_base,
                missing_amount=missing_amount,
                legal_reference=self.legal_reference,
            )

        logger.debug(
            f"Hours×Rate check passed: {actual_base} ≈ {expected_base} "
            f"(within {self.TOLERANCE_PERCENT*100}% tolerance)"
        )
        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """Check if we have enough data to validate."""
        return (
            payslip.hours_worked > 0
            and payslip.hourly_rate > 0
            and payslip.base_salary > 0
        )


class OvertimeCalculationRule(ValidationRule):
    """
    Validates overtime pay calculation.

    Israeli law requires:
    - First 2 overtime hours: 125% of regular rate
    - Additional overtime hours: 150% of regular rate
    """

    @property
    def name(self) -> str:
        return "Overtime Pay Calculation"

    @property
    def description(self) -> str:
        return "Verifies overtime pay matches legal requirements (125%/150%)"

    @property
    def violation_type(self) -> ViolationType:
        return ViolationType.OVERTIME_UNDERPAID

    @property
    def severity(self) -> ViolationSeverity:
        return ViolationSeverity.HIGH

    @property
    def legal_reference(self) -> Optional[str]:
        return "חוק שעות עבודה ומנוחה, התשי\"א-1951"

    def validate(self, payslip: Payslip) -> Optional[Violation]:
        """
        Validate overtime pay calculation.

        Args:
            payslip: The payslip to validate

        Returns:
            Violation if overtime is underpaid, None otherwise
        """
        if payslip.overtime_hours <= 0:
            return None

        # Calculate expected overtime pay
        # Simplified: assuming all overtime at 125% (first tier)
        # A more sophisticated implementation would track daily hours
        hourly_rate = payslip.hourly_rate
        overtime_hours = payslip.overtime_hours

        # Conservative calculation: all at 125%
        expected_overtime = (hourly_rate * Decimal("1.25") * overtime_hours).quantize(
            Decimal("0.01")
        )

        actual_overtime = payslip.overtime_pay

        # Allow some tolerance for mixed 125%/150% calculations
        min_expected = expected_overtime * Decimal("0.95")

        if actual_overtime < min_expected:
            missing_amount = expected_overtime - actual_overtime

            hebrew_desc = (
                f"תשלום שעות נוספות ({actual_overtime:.2f} ש\"ח) נמוך מהנדרש. "
                f"עבור {overtime_hours:.1f} שעות נוספות בתעריף {hourly_rate:.2f} ש\"ח, "
                f"הסכום המינימלי הוא {expected_overtime:.2f} ש\"ח (125%). "
                f"חסרים כ-{missing_amount:.2f} ש\"ח."
            )
            english_desc = (
                f"Overtime pay ({actual_overtime:.2f} ILS) is below minimum. "
                f"For {overtime_hours:.1f} overtime hours at {hourly_rate:.2f} ILS/hour, "
                f"minimum is {expected_overtime:.2f} ILS (125%). "
                f"Missing approximately {missing_amount:.2f} ILS."
            )

            return Violation(
                violation_type=self.violation_type,
                description=english_desc,
                description_hebrew=hebrew_desc,
                expected_value=expected_overtime,
                actual_value=actual_overtime,
                missing_amount=missing_amount,
                legal_reference=self.legal_reference,
            )

        return None

    def is_applicable(self, payslip: Payslip) -> bool:
        """Check if payslip has overtime hours to validate."""
        return payslip.overtime_hours > 0 and payslip.hourly_rate > 0
