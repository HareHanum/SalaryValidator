"""Validator module for checking payslips against Israeli labor laws."""

from src.validator.base import ValidationError, ValidationRule, ViolationSeverity
from src.validator.labor_law_data import (
    MINIMUM_WAGE_HISTORY,
    OVERTIME_RATES,
    PENSION_RATES_HISTORY,
    STANDARD_HOURS_PER_MONTH,
    get_minimum_hourly_wage,
    get_minimum_monthly_wage,
    get_minimum_wage,
    get_pension_rates,
    get_vacation_days_entitlement,
)
from src.validator.payslip_validator import (
    PayslipValidator,
    RuleRegistry,
    create_default_registry,
    validate_payslip,
)
from src.validator.rules import (
    EmployerPensionRule,
    HoursRateRule,
    MinimumWageRule,
    MonthlyMinimumWageRule,
    OvertimeCalculationRule,
    PensionContributionRule,
)

__all__ = [
    # Main validator
    "PayslipValidator",
    "validate_payslip",
    "RuleRegistry",
    "create_default_registry",
    # Base classes
    "ValidationRule",
    "ValidationError",
    "ViolationSeverity",
    # Rules
    "MinimumWageRule",
    "MonthlyMinimumWageRule",
    "HoursRateRule",
    "OvertimeCalculationRule",
    "PensionContributionRule",
    "EmployerPensionRule",
    # Labor law data
    "get_minimum_wage",
    "get_minimum_hourly_wage",
    "get_minimum_monthly_wage",
    "get_pension_rates",
    "get_vacation_days_entitlement",
    "MINIMUM_WAGE_HISTORY",
    "PENSION_RATES_HISTORY",
    "OVERTIME_RATES",
    "STANDARD_HOURS_PER_MONTH",
]
