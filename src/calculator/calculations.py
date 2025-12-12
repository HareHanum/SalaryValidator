"""Per-payslip calculation utilities."""

from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger
from src.models import Payslip, Violation, ViolationType
from src.validator.labor_law_data import (
    OVERTIME_RATES,
    get_minimum_wage,
    get_pension_rates,
)

logger = get_logger("calculator.calculations")


def calculate_expected_base_salary(payslip: Payslip) -> Decimal:
    """
    Calculate expected base salary from hours and rate.

    Args:
        payslip: The payslip to calculate for

    Returns:
        Expected base salary
    """
    return (payslip.hours_worked * payslip.hourly_rate).quantize(Decimal("0.01"))


def calculate_minimum_wage_difference(payslip: Payslip) -> Decimal:
    """
    Calculate the difference between actual and minimum wage.

    Args:
        payslip: The payslip to calculate for

    Returns:
        Missing amount (positive if underpaid, 0 if compliant)
    """
    min_wage = get_minimum_wage(payslip.payslip_date)

    if payslip.hourly_rate >= min_wage.hourly_wage:
        return Decimal("0")

    expected = min_wage.hourly_wage * payslip.hours_worked
    actual = payslip.hourly_rate * payslip.hours_worked

    return (expected - actual).quantize(Decimal("0.01"))


def calculate_hours_rate_difference(payslip: Payslip) -> Decimal:
    """
    Calculate discrepancy between stated base salary and hours × rate.

    Args:
        payslip: The payslip to calculate for

    Returns:
        Missing amount (positive if underpaid)
    """
    expected = calculate_expected_base_salary(payslip)
    actual = payslip.base_salary

    difference = expected - actual
    return difference if difference > 0 else Decimal("0")


def calculate_expected_overtime(payslip: Payslip) -> Decimal:
    """
    Calculate expected overtime pay based on legal rates.

    Israeli law:
    - First 2 hours overtime per day: 125%
    - Additional overtime hours: 150%

    For simplicity, we calculate conservatively assuming all at 125%.

    Args:
        payslip: The payslip to calculate for

    Returns:
        Expected minimum overtime pay
    """
    if payslip.overtime_hours <= 0:
        return Decimal("0")

    rate = payslip.hourly_rate
    hours = payslip.overtime_hours

    # Conservative: all at 125%
    return (rate * OVERTIME_RATES.first_tier_multiplier * hours).quantize(Decimal("0.01"))


def calculate_overtime_difference(payslip: Payslip) -> Decimal:
    """
    Calculate underpayment in overtime.

    Args:
        payslip: The payslip to calculate for

    Returns:
        Missing overtime amount
    """
    if payslip.overtime_hours <= 0:
        return Decimal("0")

    expected = calculate_expected_overtime(payslip)
    actual = payslip.overtime_pay

    difference = expected - actual
    return difference if difference > 0 else Decimal("0")


def calculate_expected_pension_contribution(
    payslip: Payslip, contribution_type: str = "employee"
) -> Decimal:
    """
    Calculate expected pension contribution.

    Args:
        payslip: The payslip to calculate for
        contribution_type: "employee" or "employer"

    Returns:
        Expected contribution amount
    """
    rates = get_pension_rates(payslip.payslip_date)

    if contribution_type == "employee":
        rate = rates.employee_rate
    else:
        rate = rates.employer_rate

    # Pension is typically calculated on gross salary
    return (payslip.gross_salary * rate).quantize(Decimal("0.01"))


def calculate_pension_difference(payslip: Payslip) -> Decimal:
    """
    Calculate missing employee pension contribution.

    Args:
        payslip: The payslip to calculate for

    Returns:
        Missing pension amount
    """
    expected = calculate_expected_pension_contribution(payslip, "employee")
    actual = payslip.deductions.pension_employee

    difference = expected - actual
    return difference if difference > 0 else Decimal("0")


def calculate_total_expected_pay(payslip: Payslip) -> Decimal:
    """
    Calculate total expected pay based on legal minimums.

    Args:
        payslip: The payslip to calculate for

    Returns:
        Total expected gross pay
    """
    min_wage = get_minimum_wage(payslip.payslip_date)

    # Base pay at minimum wage (or actual if higher)
    effective_rate = max(payslip.hourly_rate, min_wage.hourly_wage)
    base = effective_rate * payslip.hours_worked

    # Overtime at legal rates
    overtime = Decimal("0")
    if payslip.overtime_hours > 0:
        overtime = effective_rate * OVERTIME_RATES.first_tier_multiplier * payslip.overtime_hours

    # Weekend pay
    weekend = Decimal("0")
    if payslip.weekend_hours > 0:
        weekend = effective_rate * OVERTIME_RATES.weekend_multiplier * payslip.weekend_hours

    # Other additions (take as-is)
    other = payslip.vacation_pay + payslip.bonus + payslip.other_additions

    return (base + overtime + weekend + other).quantize(Decimal("0.01"))


def calculate_total_missing(payslip: Payslip) -> Decimal:
    """
    Calculate total missing amount from all violation types.

    Args:
        payslip: The payslip to calculate for

    Returns:
        Total missing amount
    """
    total = Decimal("0")

    total += calculate_minimum_wage_difference(payslip)
    total += calculate_hours_rate_difference(payslip)
    total += calculate_overtime_difference(payslip)
    total += calculate_pension_difference(payslip)

    return total


def get_violation_amount(violation: Violation) -> Decimal:
    """
    Get the monetary amount associated with a violation.

    Args:
        violation: The violation to get amount for

    Returns:
        Missing amount from the violation
    """
    return violation.missing_amount


def categorize_violation(violation: Violation) -> str:
    """
    Get a human-readable category for a violation.

    Args:
        violation: The violation to categorize

    Returns:
        Category string
    """
    categories = {
        ViolationType.MINIMUM_WAGE: "שכר מינימום",
        ViolationType.HOURS_RATE_MISMATCH: "חישוב שעות",
        ViolationType.MISSING_PENSION: "פנסיה",
        ViolationType.OVERTIME_UNDERPAID: "שעות נוספות",
        ViolationType.WEEKEND_UNDERPAID: "עבודה בשבת",
        ViolationType.MISSING_VACATION: "חופשה",
    }
    return categories.get(violation.violation_type, "אחר")
