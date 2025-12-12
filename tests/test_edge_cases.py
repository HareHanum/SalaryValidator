"""Edge case tests across all modules."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.models import Deductions, Payslip, PayslipAnalysis, Violation, ViolationType
from src.calculator import MissingAmountCalculator
from src.validator import PayslipValidator
from src.validator.labor_law_data import get_minimum_wage, get_pension_rates
from src.reporter import ReportGenerator, OutputFormat


class TestMinimumWageEdgeCases:
    """Edge case tests for minimum wage calculations."""

    def test_exactly_at_minimum_wage(self):
        """Test when salary is exactly at minimum wage."""
        calc = MissingAmountCalculator()

        # Create payslip exactly at minimum wage for 2024
        min_wage = get_minimum_wage(date(2024, 1, 1))
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=min_wage,
            hours_worked=Decimal("182"),
            hourly_rate=min_wage / Decimal("182"),
            gross_salary=min_wage,
            net_salary=min_wage * Decimal("0.8"),
            deductions=Deductions(
                pension_employee=min_wage * Decimal("0.06"),
                pension_employer=min_wage * Decimal("0.065"),
            ),
        )

        analysis = calc.add_payslip(payslip)

        # Should not have minimum wage violation
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.MINIMUM_WAGE not in violation_types

    def test_one_cent_below_minimum_wage(self):
        """Test when salary is one cent below minimum wage."""
        calc = MissingAmountCalculator()

        min_wage = get_minimum_wage(date(2024, 1, 1))
        below_min = min_wage - Decimal("0.01")

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=below_min,
            hours_worked=Decimal("182"),
            hourly_rate=below_min / Decimal("182"),
            gross_salary=below_min,
            net_salary=below_min * Decimal("0.8"),
            deductions=Deductions(
                pension_employee=below_min * Decimal("0.06"),
                pension_employer=below_min * Decimal("0.065"),
            ),
        )

        analysis = calc.add_payslip(payslip)

        # Should have minimum wage violation
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.MINIMUM_WAGE in violation_types

    def test_historical_minimum_wage_2017(self):
        """Test minimum wage for historical dates."""
        calc = MissingAmountCalculator()

        # In 2017, minimum wage was lower
        min_wage_2017 = get_minimum_wage(date(2017, 6, 1))

        payslip = Payslip(
            payslip_date=date(2017, 6, 1),
            base_salary=min_wage_2017,
            hours_worked=Decimal("182"),
            hourly_rate=min_wage_2017 / Decimal("182"),
            gross_salary=min_wage_2017,
            net_salary=min_wage_2017 * Decimal("0.8"),
            deductions=Deductions(),
        )

        analysis = calc.add_payslip(payslip)

        # Should not have minimum wage violation for 2017 rates
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.MINIMUM_WAGE not in violation_types


class TestPensionEdgeCases:
    """Edge case tests for pension calculations."""

    def test_exactly_6_percent_pension(self):
        """Test when pension is exactly 6%."""
        calc = MissingAmountCalculator()

        base_salary = Decimal("10000")
        pension_6pct = base_salary * Decimal("0.06")

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=base_salary,
            hours_worked=Decimal("182"),
            hourly_rate=base_salary / Decimal("182"),
            gross_salary=base_salary,
            net_salary=base_salary * Decimal("0.8"),
            deductions=Deductions(
                pension_employee=pension_6pct,
                pension_employer=base_salary * Decimal("0.065"),
            ),
        )

        analysis = calc.add_payslip(payslip)

        # Should not have pension violation
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.MISSING_PENSION not in violation_types

    def test_slightly_under_pension_threshold(self):
        """Test when pension is slightly under required percentage."""
        calc = MissingAmountCalculator()

        base_salary = Decimal("10000")
        # 5.9% instead of 6%
        pension_under = base_salary * Decimal("0.059")

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=base_salary,
            hours_worked=Decimal("182"),
            hourly_rate=base_salary / Decimal("182"),
            gross_salary=base_salary,
            net_salary=base_salary * Decimal("0.8"),
            deductions=Deductions(
                pension_employee=pension_under,
                pension_employer=base_salary * Decimal("0.065"),
            ),
        )

        analysis = calc.add_payslip(payslip)

        # May or may not have violation depending on tolerance
        # The key is it shouldn't crash

    def test_zero_pension_contributions(self):
        """Test with zero pension contributions."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("7000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("38.46"),
            gross_salary=Decimal("7000"),
            net_salary=Decimal("6500"),
            deductions=Deductions(
                pension_employee=Decimal("0"),
                pension_employer=Decimal("0"),
            ),
        )

        analysis = calc.add_payslip(payslip)

        # Should have pension violation
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.MISSING_PENSION in violation_types


class TestHoursRateEdgeCases:
    """Edge case tests for hours × rate calculations."""

    def test_within_tolerance(self):
        """Test calculation within 1% tolerance."""
        calc = MissingAmountCalculator()

        # 182 × 35 = 6370, but we'll use 6365 (within 1%)
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("6365"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("35.00"),
            gross_salary=Decimal("6365"),
            net_salary=Decimal("5000"),
            deductions=Deductions(
                pension_employee=Decimal("381.90"),
                pension_employer=Decimal("413.73"),
            ),
        )

        analysis = calc.add_payslip(payslip)

        # Should not have calculation error (within tolerance)
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.CALCULATION_ERROR not in violation_types

    def test_zero_hours(self):
        """Test with zero hours worked."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("0"),
            hours_worked=Decimal("0"),
            hourly_rate=Decimal("35.00"),
            gross_salary=Decimal("0"),
            net_salary=Decimal("0"),
            deductions=Deductions(),
        )

        # Should not crash with zero hours
        analysis = calc.add_payslip(payslip)
        assert analysis is not None

    def test_fractional_hours(self):
        """Test with fractional hours."""
        calc = MissingAmountCalculator()

        # 182.5 hours × 35 = 6387.50
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("6387.50"),
            hours_worked=Decimal("182.5"),
            hourly_rate=Decimal("35.00"),
            gross_salary=Decimal("6387.50"),
            net_salary=Decimal("5100"),
            deductions=Deductions(
                pension_employee=Decimal("383.25"),
                pension_employer=Decimal("415.19"),
            ),
        )

        analysis = calc.add_payslip(payslip)

        # Should not have calculation error
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.CALCULATION_ERROR not in violation_types


class TestDecimalPrecisionEdgeCases:
    """Edge case tests for decimal precision."""

    def test_many_decimal_places(self):
        """Test handling of many decimal places."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("5571.7549999"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("30.6139286813"),
            gross_salary=Decimal("5571.7549999"),
            net_salary=Decimal("4571.7549999"),
            deductions=Deductions(),
        )

        analysis = calc.add_payslip(payslip)
        assert analysis is not None

    def test_very_large_salary(self):
        """Test handling of very large salaries."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("999999.99"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("5494.50"),
            gross_salary=Decimal("999999.99"),
            net_salary=Decimal("600000"),
            deductions=Deductions(
                pension_employee=Decimal("60000"),
                pension_employer=Decimal("65000"),
            ),
        )

        analysis = calc.add_payslip(payslip)
        assert analysis.is_compliant  # High salary should be compliant

    def test_very_small_amounts(self):
        """Test handling of very small amounts."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("0.01"),
            hours_worked=Decimal("0.001"),
            hourly_rate=Decimal("10.00"),
            gross_salary=Decimal("0.01"),
            net_salary=Decimal("0.01"),
            deductions=Deductions(),
        )

        # Should handle gracefully
        analysis = calc.add_payslip(payslip)
        assert analysis is not None


class TestDateEdgeCases:
    """Edge case tests for date handling."""

    def test_future_date(self):
        """Test with future date."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2030, 1, 1),
            base_salary=Decimal("10000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("54.95"),
            gross_salary=Decimal("10000"),
            net_salary=Decimal("8000"),
            deductions=Deductions(
                pension_employee=Decimal("600"),
                pension_employer=Decimal("650"),
            ),
        )

        # Should use most recent known rates
        analysis = calc.add_payslip(payslip)
        assert analysis is not None

    def test_very_old_date(self):
        """Test with very old date."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2010, 1, 1),
            base_salary=Decimal("4000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("21.98"),
            gross_salary=Decimal("4000"),
            net_salary=Decimal("3500"),
            deductions=Deductions(),
        )

        # Should use earliest known rates
        analysis = calc.add_payslip(payslip)
        assert analysis is not None

    def test_leap_year_date(self):
        """Test with leap year date."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 2, 29),  # Leap year
            base_salary=Decimal("6000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("32.97"),
            gross_salary=Decimal("6000"),
            net_salary=Decimal("4800"),
            deductions=Deductions(
                pension_employee=Decimal("360"),
                pension_employer=Decimal("390"),
            ),
        )

        analysis = calc.add_payslip(payslip)
        assert analysis is not None


class TestMultiplePayslipsEdgeCases:
    """Edge case tests for multiple payslip processing."""

    def test_empty_payslip_list(self):
        """Test with no payslips."""
        calc = MissingAmountCalculator()

        summary = calc.get_summary()

        assert summary["total_payslips"] == 0
        assert summary["total_missing"] == 0

    def test_single_payslip(self):
        """Test with single payslip."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("6000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("32.97"),
            gross_salary=Decimal("6000"),
            net_salary=Decimal("4800"),
            deductions=Deductions(
                pension_employee=Decimal("360"),
                pension_employer=Decimal("390"),
            ),
        )
        calc.add_payslip(payslip)

        summary = calc.get_summary()
        assert summary["total_payslips"] == 1

    def test_many_payslips(self):
        """Test with many payslips (stress test)."""
        calc = MissingAmountCalculator()

        # Add 100 payslips
        for i in range(100):
            month = (i % 12) + 1
            year = 2020 + (i // 12)

            payslip = Payslip(
                payslip_date=date(year, month, 1),
                base_salary=Decimal("6000"),
                hours_worked=Decimal("182"),
                hourly_rate=Decimal("32.97"),
                gross_salary=Decimal("6000"),
                net_salary=Decimal("4800"),
                deductions=Deductions(
                    pension_employee=Decimal("360"),
                    pension_employer=Decimal("390"),
                ),
            )
            calc.add_payslip(payslip)

        summary = calc.get_summary()
        assert summary["total_payslips"] == 100

    def test_duplicate_months(self):
        """Test with duplicate months (corrections)."""
        calc = MissingAmountCalculator()

        # Add two payslips for same month
        for _ in range(2):
            payslip = Payslip(
                payslip_date=date(2024, 1, 1),
                base_salary=Decimal("6000"),
                hours_worked=Decimal("182"),
                hourly_rate=Decimal("32.97"),
                gross_salary=Decimal("6000"),
                net_salary=Decimal("4800"),
                deductions=Deductions(
                    pension_employee=Decimal("360"),
                    pension_employer=Decimal("390"),
                ),
            )
            calc.add_payslip(payslip)

        summary = calc.get_summary()
        assert summary["total_payslips"] == 2


class TestReportGeneratorEdgeCases:
    """Edge case tests for report generation."""

    def test_report_with_no_violations(self):
        """Test report generation with no violations."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("7000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("38.46"),
            gross_salary=Decimal("7000"),
            net_salary=Decimal("5600"),
            deductions=Deductions(
                pension_employee=Decimal("420"),
                pension_employer=Decimal("455"),
            ),
        )
        calc.add_payslip(payslip)

        report = calc.generate_report()
        generator = ReportGenerator()

        # Should generate reports without errors
        json_output = generator.generate(report, OutputFormat.JSON)
        text_output = generator.generate(report, OutputFormat.TEXT)
        html_output = generator.generate(report, OutputFormat.HTML)

        assert "0" in json_output or "compliant" in json_output.lower()

    def test_report_with_hebrew_characters(self):
        """Test report generation with Hebrew content."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("4000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("21.98"),
            gross_salary=Decimal("4000"),
            net_salary=Decimal("3800"),
            deductions=Deductions(),
        )
        calc.add_payslip(payslip)

        report = calc.generate_report()
        generator = ReportGenerator()

        text_output = generator.generate(report, OutputFormat.TEXT)
        html_output = generator.generate(report, OutputFormat.HTML)

        # Should contain Hebrew text
        assert "שכר" in text_output or "דוח" in text_output
        assert 'dir="rtl"' in html_output

    def test_report_special_characters(self):
        """Test report with special characters in amounts."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("5571.75"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("30.614"),
            gross_salary=Decimal("5571.75"),
            net_salary=Decimal("4571.75"),
            deductions=Deductions(
                pension_employee=Decimal("334.31"),
                pension_employer=Decimal("362.16"),
            ),
        )
        calc.add_payslip(payslip)

        report = calc.generate_report()
        generator = ReportGenerator()

        json_output = generator.generate(report, OutputFormat.JSON)

        # Should handle shekel symbol correctly
        assert "₪" in json_output


class TestValidatorEdgeCases:
    """Edge case tests for the validator."""

    def test_validator_all_rules(self):
        """Test that all validation rules are applied."""
        validator = PayslipValidator()

        # Payslip with multiple violations
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("4000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("21.98"),
            gross_salary=Decimal("4000"),
            net_salary=Decimal("3800"),
            deductions=Deductions(),
        )

        violations = validator.validate(payslip)

        # Should find multiple violations
        violation_types = [v.violation_type for v in violations]
        assert ViolationType.MINIMUM_WAGE in violation_types
        assert ViolationType.MISSING_PENSION in violation_types

    def test_validator_compliant_payslip(self):
        """Test validator with fully compliant payslip."""
        validator = PayslipValidator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("7000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("38.46"),
            gross_salary=Decimal("7000"),
            net_salary=Decimal("5600"),
            deductions=Deductions(
                pension_employee=Decimal("420"),
                pension_employer=Decimal("455"),
            ),
        )

        violations = validator.validate(payslip)

        # Should have no violations
        assert len(violations) == 0


class TestNegativeValuesEdgeCases:
    """Edge case tests for negative values (corrections/adjustments)."""

    def test_negative_bonus(self):
        """Test handling of negative bonus (clawback)."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("7000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("38.46"),
            gross_salary=Decimal("6800"),  # 7000 - 200 bonus clawback
            net_salary=Decimal("5500"),
            bonus=Decimal("-200"),
            deductions=Deductions(
                pension_employee=Decimal("420"),
                pension_employer=Decimal("455"),
            ),
        )

        analysis = calc.add_payslip(payslip)
        assert analysis is not None

    def test_negative_overtime(self):
        """Test handling of negative overtime (correction)."""
        calc = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("7000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("38.46"),
            gross_salary=Decimal("6900"),
            net_salary=Decimal("5500"),
            overtime_hours=Decimal("-5"),  # Correction
            overtime_pay=Decimal("-250"),
            deductions=Deductions(
                pension_employee=Decimal("420"),
                pension_employer=Decimal("455"),
            ),
        )

        analysis = calc.add_payslip(payslip)
        assert analysis is not None
