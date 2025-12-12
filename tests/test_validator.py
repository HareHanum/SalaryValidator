"""Tests for the validator module."""

from datetime import date
from decimal import Decimal

import pytest

from src.models import Deductions, Payslip, ViolationType
from src.validator.labor_law_data import (
    get_minimum_wage,
    get_pension_rates,
    get_vacation_days_entitlement,
)
from src.validator.payslip_validator import PayslipValidator, RuleRegistry, validate_payslip
from src.validator.rules import (
    HoursRateRule,
    MinimumWageRule,
    OvertimeCalculationRule,
    PensionContributionRule,
)


class TestLaborLawData:
    """Tests for labor law data."""

    def test_get_minimum_wage_2024(self):
        """Test minimum wage for 2024."""
        wage = get_minimum_wage(date(2024, 5, 1))
        assert wage.monthly_wage == Decimal("5880.02")
        assert wage.hourly_wage > Decimal("32")  # Should be around 32.31

    def test_get_minimum_wage_2023(self):
        """Test minimum wage for 2023."""
        wage = get_minimum_wage(date(2023, 6, 1))
        assert wage.monthly_wage == Decimal("5571.75")

    def test_get_minimum_wage_historical(self):
        """Test historical minimum wage."""
        wage = get_minimum_wage(date(2018, 6, 1))
        assert wage.monthly_wage == Decimal("5000.00")

    def test_get_pension_rates(self):
        """Test pension rates."""
        rates = get_pension_rates(date(2024, 1, 1))
        assert rates.employee_rate == Decimal("0.06")  # 6%
        assert rates.employer_rate == Decimal("0.065")  # 6.5%

    def test_vacation_days_entitlement(self):
        """Test vacation days based on tenure."""
        assert get_vacation_days_entitlement(0) == 12
        assert get_vacation_days_entitlement(1) == 12
        assert get_vacation_days_entitlement(5) == 16
        assert get_vacation_days_entitlement(14) == 28


class TestMinimumWageRule:
    """Tests for minimum wage validation."""

    def create_payslip(
        self,
        hourly_rate: Decimal,
        hours: Decimal = Decimal("182"),
        payslip_date: date = date(2024, 1, 1),
    ) -> Payslip:
        """Helper to create a test payslip."""
        base_salary = hourly_rate * hours
        return Payslip(
            payslip_date=payslip_date,
            base_salary=base_salary,
            hours_worked=hours,
            hourly_rate=hourly_rate,
            gross_salary=base_salary,
            net_salary=base_salary * Decimal("0.8"),
        )

    def test_compliant_wage(self):
        """Test payslip with compliant wage."""
        rule = MinimumWageRule()
        payslip = self.create_payslip(Decimal("35.00"))  # Above minimum

        violation = rule.validate(payslip)
        assert violation is None

    def test_below_minimum_wage(self):
        """Test payslip with wage below minimum."""
        rule = MinimumWageRule()
        payslip = self.create_payslip(Decimal("25.00"))  # Below minimum

        violation = rule.validate(payslip)
        assert violation is not None
        assert violation.violation_type == ViolationType.MINIMUM_WAGE
        assert violation.missing_amount > 0

    def test_calculates_missing_amount(self):
        """Test that missing amount is calculated correctly."""
        rule = MinimumWageRule()
        # Jan 2024: minimum hourly is ~30.61 (5571.75/182)
        payslip = self.create_payslip(
            Decimal("28.00"),
            hours=Decimal("182"),
            payslip_date=date(2024, 1, 1),
        )

        violation = rule.validate(payslip)
        assert violation is not None

        # Missing amount should be (min_hourly - 28) * 182
        min_wage = get_minimum_wage(date(2024, 1, 1))
        expected_missing = (min_wage.hourly_wage - Decimal("28.00")) * Decimal("182")
        assert abs(violation.missing_amount - expected_missing) < Decimal("1")


class TestHoursRateRule:
    """Tests for hours × rate verification."""

    def create_payslip(
        self,
        base_salary: Decimal,
        hourly_rate: Decimal,
        hours: Decimal = Decimal("182"),
    ) -> Payslip:
        """Helper to create a test payslip."""
        return Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=base_salary,
            hours_worked=hours,
            hourly_rate=hourly_rate,
            gross_salary=base_salary,
            net_salary=base_salary * Decimal("0.8"),
        )

    def test_matching_calculation(self):
        """Test when hours × rate matches base salary."""
        rule = HoursRateRule()
        payslip = self.create_payslip(
            base_salary=Decimal("5460.00"),
            hourly_rate=Decimal("30.00"),
            hours=Decimal("182"),
        )

        violation = rule.validate(payslip)
        assert violation is None

    def test_mismatched_calculation(self):
        """Test when hours × rate doesn't match."""
        rule = HoursRateRule()
        payslip = self.create_payslip(
            base_salary=Decimal("5000.00"),  # Should be 5460
            hourly_rate=Decimal("30.00"),
            hours=Decimal("182"),
        )

        violation = rule.validate(payslip)
        assert violation is not None
        assert violation.violation_type == ViolationType.HOURS_RATE_MISMATCH
        assert violation.missing_amount == Decimal("460.00")

    def test_within_tolerance(self):
        """Test calculation within tolerance."""
        rule = HoursRateRule()
        # 5460 * 0.99 = 5405.40 (within 1% tolerance)
        payslip = self.create_payslip(
            base_salary=Decimal("5450.00"),
            hourly_rate=Decimal("30.00"),
            hours=Decimal("182"),
        )

        violation = rule.validate(payslip)
        assert violation is None  # Within tolerance


class TestPensionRule:
    """Tests for pension contribution validation."""

    def create_payslip(
        self,
        gross_salary: Decimal,
        pension_employee: Decimal = Decimal("0"),
    ) -> Payslip:
        """Helper to create a test payslip."""
        return Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=gross_salary,
            hours_worked=Decimal("182"),
            hourly_rate=gross_salary / Decimal("182"),
            gross_salary=gross_salary,
            net_salary=gross_salary * Decimal("0.8"),
            deductions=Deductions(pension_employee=pension_employee),
        )

    def test_no_pension_contribution(self):
        """Test when no pension is contributed."""
        rule = PensionContributionRule()
        payslip = self.create_payslip(
            gross_salary=Decimal("10000.00"),
            pension_employee=Decimal("0"),
        )

        violation = rule.validate(payslip)
        assert violation is not None
        assert violation.violation_type == ViolationType.MISSING_PENSION

    def test_sufficient_pension(self):
        """Test when pension meets requirements."""
        rule = PensionContributionRule()
        # 6% of 10000 = 600
        payslip = self.create_payslip(
            gross_salary=Decimal("10000.00"),
            pension_employee=Decimal("600.00"),
        )

        violation = rule.validate(payslip)
        assert violation is None

    def test_insufficient_pension(self):
        """Test when pension is below required rate."""
        rule = PensionContributionRule()
        # 6% of 10000 = 600, but only 300 contributed
        payslip = self.create_payslip(
            gross_salary=Decimal("10000.00"),
            pension_employee=Decimal("300.00"),
        )

        violation = rule.validate(payslip)
        assert violation is not None
        assert violation.missing_amount > Decimal("290")  # ~300 missing


class TestOvertimeRule:
    """Tests for overtime calculation validation."""

    def test_correct_overtime(self):
        """Test when overtime is calculated correctly."""
        rule = OvertimeCalculationRule()
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("5460.00"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("30.00"),
            overtime_hours=Decimal("10"),
            overtime_pay=Decimal("375.00"),  # 10 * 30 * 1.25 = 375
            gross_salary=Decimal("5835.00"),
            net_salary=Decimal("5000.00"),
        )

        violation = rule.validate(payslip)
        assert violation is None

    def test_underpaid_overtime(self):
        """Test when overtime is underpaid."""
        rule = OvertimeCalculationRule()
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("5460.00"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("30.00"),
            overtime_hours=Decimal("10"),
            overtime_pay=Decimal("300.00"),  # Should be at least 375 (10 * 30 * 1.25)
            gross_salary=Decimal("5760.00"),
            net_salary=Decimal("5000.00"),
        )

        violation = rule.validate(payslip)
        assert violation is not None
        assert violation.violation_type == ViolationType.OVERTIME_UNDERPAID


class TestPayslipValidator:
    """Tests for the main validator."""

    def create_valid_payslip(self) -> Payslip:
        """Create a fully compliant payslip."""
        gross = Decimal("10000.00")
        return Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("5950.00"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("32.69"),  # 5950/182 ≈ 32.69
            gross_salary=gross,
            net_salary=Decimal("7500.00"),
            deductions=Deductions(
                income_tax=Decimal("1000.00"),
                national_insurance=Decimal("500.00"),
                pension_employee=Decimal("600.00"),  # 6% of 10000
            ),
        )

    def create_invalid_payslip(self) -> Payslip:
        """Create a payslip with violations."""
        gross = Decimal("5000.00")
        return Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=gross,
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("25.00"),  # Below minimum wage
            gross_salary=gross,
            net_salary=Decimal("4000.00"),
            deductions=Deductions(
                pension_employee=Decimal("0"),  # No pension
            ),
        )

    def test_validate_compliant_payslip(self):
        """Test validation of compliant payslip."""
        validator = PayslipValidator()
        payslip = self.create_valid_payslip()

        analysis = validator.validate(payslip)

        assert analysis.is_compliant
        assert len(analysis.violations) == 0
        assert analysis.total_missing == Decimal("0")

    def test_validate_non_compliant_payslip(self):
        """Test validation of non-compliant payslip."""
        validator = PayslipValidator()
        payslip = self.create_invalid_payslip()

        analysis = validator.validate(payslip)

        assert not analysis.is_compliant
        assert len(analysis.violations) > 0
        assert analysis.total_missing > Decimal("0")

    def test_validate_convenience_function(self):
        """Test the validate_payslip convenience function."""
        payslip = self.create_invalid_payslip()

        analysis = validate_payslip(payslip)

        assert not analysis.is_compliant

    def test_rule_registry(self):
        """Test rule registry operations."""
        registry = RuleRegistry()

        assert len(registry.get_rules()) == 0

        registry.register(MinimumWageRule())
        assert len(registry.get_rules()) == 1

        registry.register(HoursRateRule())
        assert len(registry.get_rules()) == 2

        registry.unregister("Minimum Wage Compliance")
        assert len(registry.get_rules()) == 1

        registry.clear()
        assert len(registry.get_rules()) == 0

    def test_get_rule_names(self):
        """Test getting rule names from validator."""
        validator = PayslipValidator()
        names = validator.get_rule_names()

        assert "Minimum Wage Compliance" in names
        assert "Hours × Rate Verification" in names
        assert "Pension Contribution" in names
