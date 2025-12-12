"""Israeli labor law data - minimum wages and statutory requirements."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger

logger = get_logger("validator.labor_law_data")


@dataclass
class MinimumWageRate:
    """Minimum wage rate for a specific period."""

    effective_date: date
    monthly_wage: Decimal
    hourly_wage: Decimal
    daily_wage: Decimal  # For 5-day work week

    @classmethod
    def from_monthly(
        cls, effective_date: date, monthly_wage: Decimal, hours_per_month: Decimal = Decimal("182")
    ) -> "MinimumWageRate":
        """Create rate from monthly wage, calculating hourly and daily."""
        hourly = (monthly_wage / hours_per_month).quantize(Decimal("0.01"))
        daily = (monthly_wage / Decimal("21.67")).quantize(Decimal("0.01"))  # Average work days
        return cls(
            effective_date=effective_date,
            monthly_wage=monthly_wage,
            hourly_wage=hourly,
            daily_wage=daily,
        )


# Historical minimum wage rates in Israel
# Source: Ministry of Economy and Industry
# https://www.gov.il/he/departments/general/minimum_wage
MINIMUM_WAGE_HISTORY: list[MinimumWageRate] = [
    # 2025
    MinimumWageRate.from_monthly(date(2025, 4, 1), Decimal("6247.67")),  # ₪34.32/hour
    MinimumWageRate.from_monthly(date(2025, 1, 1), Decimal("5880.02")),  # Same as late 2024
    # 2024
    MinimumWageRate.from_monthly(date(2024, 4, 1), Decimal("5880.02")),  # ₪32.31/hour
    MinimumWageRate.from_monthly(date(2024, 1, 1), Decimal("5571.75")),
    # 2023
    MinimumWageRate.from_monthly(date(2023, 4, 1), Decimal("5571.75")),
    MinimumWageRate.from_monthly(date(2023, 1, 1), Decimal("5300.00")),
    # 2022
    MinimumWageRate.from_monthly(date(2022, 4, 1), Decimal("5300.00")),
    MinimumWageRate.from_monthly(date(2022, 1, 1), Decimal("5300.00")),
    # 2021
    MinimumWageRate.from_monthly(date(2021, 4, 1), Decimal("5300.00")),
    MinimumWageRate.from_monthly(date(2021, 1, 1), Decimal("5300.00")),
    # 2020
    MinimumWageRate.from_monthly(date(2020, 4, 1), Decimal("5300.00")),
    MinimumWageRate.from_monthly(date(2020, 1, 1), Decimal("5300.00")),
    # 2019
    MinimumWageRate.from_monthly(date(2019, 4, 1), Decimal("5300.00")),
    MinimumWageRate.from_monthly(date(2019, 1, 1), Decimal("5300.00")),
    # 2018
    MinimumWageRate.from_monthly(date(2018, 12, 1), Decimal("5300.00")),
    MinimumWageRate.from_monthly(date(2018, 4, 1), Decimal("5000.00")),
    MinimumWageRate.from_monthly(date(2018, 1, 1), Decimal("5000.00")),
    # 2017
    MinimumWageRate.from_monthly(date(2017, 7, 1), Decimal("5000.00")),
    MinimumWageRate.from_monthly(date(2017, 1, 1), Decimal("4825.00")),
    # Fallback for older dates
    MinimumWageRate.from_monthly(date(2016, 1, 1), Decimal("4650.00")),
]


def get_minimum_wage(for_date: date) -> MinimumWageRate:
    """
    Get the minimum wage rate effective for a given date.

    Args:
        for_date: Date to get minimum wage for

    Returns:
        MinimumWageRate effective on that date
    """
    # Sort by effective date descending
    sorted_rates = sorted(MINIMUM_WAGE_HISTORY, key=lambda r: r.effective_date, reverse=True)

    for rate in sorted_rates:
        if for_date >= rate.effective_date:
            logger.debug(f"Minimum wage for {for_date}: ₪{rate.monthly_wage}/month")
            return rate

    # Return oldest rate as fallback
    return sorted_rates[-1]


# Pension contribution rates
@dataclass
class PensionRates:
    """Mandatory pension contribution rates."""

    effective_date: date
    employee_rate: Decimal  # Percentage (e.g., 0.06 for 6%)
    employer_rate: Decimal
    employer_severance_rate: Decimal  # Employer severance component


# Pension rates history (simplified - full rates depend on collective agreements)
# Note: Severance rate is 8.33% (1/12 of salary per year = one month per year)
# This is mandated under Section 14 pension arrangements
PENSION_RATES_HISTORY: list[PensionRates] = [
    # From 2017 onwards (after gradual increase completed)
    PensionRates(
        effective_date=date(2017, 1, 1),
        employee_rate=Decimal("0.06"),  # 6%
        employer_rate=Decimal("0.065"),  # 6.5%
        employer_severance_rate=Decimal("0.0833"),  # 8.33% severance (1/12 monthly)
    ),
    # 2016
    PensionRates(
        effective_date=date(2016, 1, 1),
        employee_rate=Decimal("0.055"),  # 5.5%
        employer_rate=Decimal("0.06"),  # 6%
        employer_severance_rate=Decimal("0.0833"),  # 8.33% severance
    ),
    # 2015
    PensionRates(
        effective_date=date(2015, 1, 1),
        employee_rate=Decimal("0.05"),  # 5%
        employer_rate=Decimal("0.055"),  # 5.5%
        employer_severance_rate=Decimal("0.0833"),  # 8.33% severance
    ),
    # 2014 and earlier
    PensionRates(
        effective_date=date(2014, 1, 1),
        employee_rate=Decimal("0.05"),
        employer_rate=Decimal("0.05"),
        employer_severance_rate=Decimal("0.0833"),  # 8.33% severance
    ),
]


def get_pension_rates(for_date: date) -> PensionRates:
    """
    Get mandatory pension rates for a given date.

    Args:
        for_date: Date to get rates for

    Returns:
        PensionRates effective on that date
    """
    sorted_rates = sorted(PENSION_RATES_HISTORY, key=lambda r: r.effective_date, reverse=True)

    for rate in sorted_rates:
        if for_date >= rate.effective_date:
            return rate

    return sorted_rates[-1]


# Overtime rates
@dataclass
class OvertimeRates:
    """Overtime pay multipliers."""

    # First 2 overtime hours per day
    first_tier_multiplier: Decimal = Decimal("1.25")  # 125%
    # Hours beyond first 2 overtime hours
    second_tier_multiplier: Decimal = Decimal("1.50")  # 150%
    # Weekend/holiday rate
    weekend_multiplier: Decimal = Decimal("1.50")  # 150%
    # Holiday rate (Shabbat, holidays)
    holiday_multiplier: Decimal = Decimal("1.50")  # 150%


OVERTIME_RATES = OvertimeRates()


# Standard working hours
STANDARD_HOURS_PER_DAY = Decimal("8.6")  # For 5-day week (43 hours / 5)
STANDARD_HOURS_PER_WEEK = Decimal("43")  # Since April 2018
STANDARD_HOURS_PER_MONTH = Decimal("182")  # 42 hours * 4.33 weeks (rounded)


# Vacation days entitlement (based on years of service)
def get_vacation_days_entitlement(years_of_service: int) -> int:
    """
    Get minimum annual vacation days based on years of service.

    Args:
        years_of_service: Years employed with current employer

    Returns:
        Minimum vacation days per year
    """
    if years_of_service < 1:
        return 12  # Pro-rated in first year
    elif years_of_service < 2:
        return 12
    elif years_of_service < 3:
        return 13
    elif years_of_service < 4:
        return 14
    elif years_of_service < 5:
        return 15
    elif years_of_service < 6:
        return 16
    elif years_of_service < 7:
        return 18
    elif years_of_service < 8:
        return 19
    elif years_of_service < 9:
        return 20
    elif years_of_service < 10:
        return 21
    elif years_of_service < 11:
        return 22
    elif years_of_service < 12:
        return 23
    elif years_of_service < 13:
        return 24
    else:
        return 28  # Maximum after 14+ years


# Sick days
ANNUAL_SICK_DAYS = 18  # Standard annual sick leave accrual
MAX_ACCUMULATED_SICK_DAYS = 90  # Maximum accumulation


# =============================================================================
# NATIONAL INSURANCE (Bituach Leumi) RATES
# =============================================================================
@dataclass
class NationalInsuranceRates:
    """National Insurance contribution rates."""

    effective_date: date
    # Lower tier (up to 60% of average wage)
    lower_threshold: Decimal  # Income threshold for lower rate
    upper_threshold: Decimal  # Maximum income for contributions
    employee_rate_lower: Decimal  # Rate for income up to lower_threshold
    employee_rate_upper: Decimal  # Rate for income above lower_threshold
    employer_rate_lower: Decimal
    employer_rate_upper: Decimal


# National Insurance rates history
# Source: https://www.btl.gov.il
NATIONAL_INSURANCE_HISTORY: list[NationalInsuranceRates] = [
    # 2025 rates (from January 2025)
    NationalInsuranceRates(
        effective_date=date(2025, 1, 1),
        lower_threshold=Decimal("7522"),  # 60% of average wage
        upper_threshold=Decimal("50695"),  # Maximum insurable income
        employee_rate_lower=Decimal("0.004"),  # 0.4%
        employee_rate_upper=Decimal("0.07"),  # 7%
        employer_rate_lower=Decimal("0.0451"),  # 4.51%
        employer_rate_upper=Decimal("0.076"),  # 7.6%
    ),
    # 2024 rates
    NationalInsuranceRates(
        effective_date=date(2024, 1, 1),
        lower_threshold=Decimal("7122"),
        upper_threshold=Decimal("47465"),
        employee_rate_lower=Decimal("0.004"),
        employee_rate_upper=Decimal("0.07"),
        employer_rate_lower=Decimal("0.0451"),
        employer_rate_upper=Decimal("0.076"),
    ),
    # 2023 rates (fallback)
    NationalInsuranceRates(
        effective_date=date(2023, 1, 1),
        lower_threshold=Decimal("6331"),
        upper_threshold=Decimal("45075"),
        employee_rate_lower=Decimal("0.004"),
        employee_rate_upper=Decimal("0.07"),
        employer_rate_lower=Decimal("0.0451"),
        employer_rate_upper=Decimal("0.076"),
    ),
]


def get_national_insurance_rates(for_date: date) -> NationalInsuranceRates:
    """Get National Insurance rates for a given date."""
    sorted_rates = sorted(NATIONAL_INSURANCE_HISTORY, key=lambda r: r.effective_date, reverse=True)
    for rate in sorted_rates:
        if for_date >= rate.effective_date:
            return rate
    return sorted_rates[-1]


def calculate_expected_national_insurance(gross_salary: Decimal, for_date: date) -> Decimal:
    """Calculate expected employee National Insurance contribution."""
    rates = get_national_insurance_rates(for_date)

    if gross_salary <= rates.lower_threshold:
        return (gross_salary * rates.employee_rate_lower).quantize(Decimal("0.01"))

    lower_portion = rates.lower_threshold * rates.employee_rate_lower
    upper_income = min(gross_salary, rates.upper_threshold) - rates.lower_threshold
    upper_portion = upper_income * rates.employee_rate_upper

    return (lower_portion + upper_portion).quantize(Decimal("0.01"))


# =============================================================================
# HEALTH TAX RATES
# =============================================================================
@dataclass
class HealthTaxRates:
    """Health Tax contribution rates."""

    effective_date: date
    lower_threshold: Decimal  # 60% of average wage
    upper_threshold: Decimal  # Maximum income
    rate_lower: Decimal  # Rate for income up to threshold
    rate_upper: Decimal  # Rate for income above threshold


HEALTH_TAX_HISTORY: list[HealthTaxRates] = [
    # 2025 rates
    HealthTaxRates(
        effective_date=date(2025, 1, 1),
        lower_threshold=Decimal("7522"),
        upper_threshold=Decimal("50695"),
        rate_lower=Decimal("0.031"),  # 3.1%
        rate_upper=Decimal("0.05"),  # 5%
    ),
    # 2024 rates
    HealthTaxRates(
        effective_date=date(2024, 1, 1),
        lower_threshold=Decimal("7122"),
        upper_threshold=Decimal("47465"),
        rate_lower=Decimal("0.031"),
        rate_upper=Decimal("0.05"),
    ),
    # 2023 rates
    HealthTaxRates(
        effective_date=date(2023, 1, 1),
        lower_threshold=Decimal("6331"),
        upper_threshold=Decimal("45075"),
        rate_lower=Decimal("0.031"),
        rate_upper=Decimal("0.05"),
    ),
]


def get_health_tax_rates(for_date: date) -> HealthTaxRates:
    """Get Health Tax rates for a given date."""
    sorted_rates = sorted(HEALTH_TAX_HISTORY, key=lambda r: r.effective_date, reverse=True)
    for rate in sorted_rates:
        if for_date >= rate.effective_date:
            return rate
    return sorted_rates[-1]


def calculate_expected_health_tax(gross_salary: Decimal, for_date: date) -> Decimal:
    """Calculate expected Health Tax contribution."""
    rates = get_health_tax_rates(for_date)

    if gross_salary <= rates.lower_threshold:
        return (gross_salary * rates.rate_lower).quantize(Decimal("0.01"))

    lower_portion = rates.lower_threshold * rates.rate_lower
    upper_income = min(gross_salary, rates.upper_threshold) - rates.lower_threshold
    upper_portion = upper_income * rates.rate_upper

    return (lower_portion + upper_portion).quantize(Decimal("0.01"))


# =============================================================================
# RECUPERATION PAY (דמי הבראה)
# =============================================================================
@dataclass
class RecuperationRates:
    """Recuperation pay rates."""

    effective_date: date
    daily_rate: Decimal  # Amount per recuperation day


RECUPERATION_HISTORY: list[RecuperationRates] = [
    RecuperationRates(effective_date=date(2024, 7, 1), daily_rate=Decimal("418")),
    RecuperationRates(effective_date=date(2023, 7, 1), daily_rate=Decimal("400")),
    RecuperationRates(effective_date=date(2022, 7, 1), daily_rate=Decimal("378")),
    RecuperationRates(effective_date=date(2021, 1, 1), daily_rate=Decimal("378")),
    RecuperationRates(effective_date=date(2020, 1, 1), daily_rate=Decimal("378")),
]


def get_recuperation_rate(for_date: date) -> Decimal:
    """Get recuperation daily rate for a given date."""
    sorted_rates = sorted(RECUPERATION_HISTORY, key=lambda r: r.effective_date, reverse=True)
    for rate in sorted_rates:
        if for_date >= rate.effective_date:
            return rate.daily_rate
    return sorted_rates[-1].daily_rate


def get_recuperation_days_entitlement(years_of_service: int) -> int:
    """
    Get annual recuperation days based on years of service.

    Args:
        years_of_service: Years employed with current employer

    Returns:
        Number of recuperation days per year
    """
    if years_of_service < 1:
        return 5
    elif years_of_service < 2:
        return 5
    elif years_of_service < 3:
        return 5
    elif years_of_service < 4:
        return 6
    elif years_of_service < 10:
        return 6
    elif years_of_service < 15:
        return 7
    elif years_of_service < 19:
        return 8
    elif years_of_service < 24:
        return 9
    else:
        return 10


# =============================================================================
# TRAVEL EXPENSES
# =============================================================================
@dataclass
class TravelExpenseRates:
    """Travel expense reimbursement rates."""

    effective_date: date
    daily_max: Decimal  # Maximum daily reimbursement


TRAVEL_EXPENSE_HISTORY: list[TravelExpenseRates] = [
    TravelExpenseRates(effective_date=date(2024, 1, 1), daily_max=Decimal("26.40")),
    TravelExpenseRates(effective_date=date(2023, 1, 1), daily_max=Decimal("25.40")),
    TravelExpenseRates(effective_date=date(2022, 1, 1), daily_max=Decimal("22.60")),
]


def get_travel_expense_max(for_date: date) -> Decimal:
    """Get maximum daily travel expense reimbursement."""
    sorted_rates = sorted(TRAVEL_EXPENSE_HISTORY, key=lambda r: r.effective_date, reverse=True)
    for rate in sorted_rates:
        if for_date >= rate.effective_date:
            return rate.daily_max
    return sorted_rates[-1].daily_max


# =============================================================================
# SEVERANCE FUND RATE
# =============================================================================
SEVERANCE_FUND_RATE = Decimal("0.0833")  # 8.33% (1/12 of monthly salary)


def get_minimum_hourly_wage(for_date: date) -> Decimal:
    """Convenience function to get minimum hourly wage."""
    return get_minimum_wage(for_date).hourly_wage


def get_minimum_monthly_wage(for_date: date) -> Decimal:
    """Convenience function to get minimum monthly wage."""
    return get_minimum_wage(for_date).monthly_wage
