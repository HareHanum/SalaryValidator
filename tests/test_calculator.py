"""Tests for the calculator module."""

from datetime import date
from decimal import Decimal

import pytest

from src.models import Deductions, Payslip, PayslipAnalysis, Violation, ViolationType
from src.calculator.calculations import (
    calculate_expected_base_salary,
    calculate_minimum_wage_difference,
    calculate_hours_rate_difference,
    calculate_expected_overtime,
    calculate_pension_difference,
    calculate_total_missing,
    categorize_violation,
)
from src.calculator.aggregator import (
    ResultAggregator,
    ViolationSummary,
    aggregate_analyses,
)
from src.calculator.statistics import (
    calculate_statistics,
    calculate_compliance_metrics,
    analyze_trends,
)
from src.calculator.missing_amount_calculator import (
    MissingAmountCalculator,
    calculate_missing_amounts,
)


def create_test_payslip(
    payslip_date: date = date(2024, 1, 1),
    hourly_rate: Decimal = Decimal("30.00"),
    hours: Decimal = Decimal("182"),
    gross_salary: Decimal = None,
    pension: Decimal = Decimal("0"),
    overtime_hours: Decimal = Decimal("0"),
    overtime_pay: Decimal = Decimal("0"),
) -> Payslip:
    """Helper to create test payslips."""
    base_salary = hourly_rate * hours
    if gross_salary is None:
        gross_salary = base_salary + overtime_pay

    return Payslip(
        payslip_date=payslip_date,
        base_salary=base_salary,
        hours_worked=hours,
        hourly_rate=hourly_rate,
        overtime_hours=overtime_hours,
        overtime_pay=overtime_pay,
        gross_salary=gross_salary,
        net_salary=gross_salary * Decimal("0.8"),
        deductions=Deductions(pension_employee=pension),
    )


def create_test_analysis(
    payslip: Payslip,
    violations: list[Violation] = None,
) -> PayslipAnalysis:
    """Helper to create test analyses."""
    if violations is None:
        violations = []

    analysis = PayslipAnalysis(
        payslip=payslip,
        violations=violations,
    )
    analysis.calculate_totals()
    return analysis


class TestCalculations:
    """Tests for calculation utilities."""

    def test_calculate_expected_base_salary(self):
        """Test base salary calculation."""
        payslip = create_test_payslip(
            hourly_rate=Decimal("30.00"),
            hours=Decimal("182"),
        )
        expected = calculate_expected_base_salary(payslip)
        assert expected == Decimal("5460.00")

    def test_calculate_minimum_wage_difference_compliant(self):
        """Test minimum wage difference when compliant."""
        payslip = create_test_payslip(
            hourly_rate=Decimal("35.00"),  # Above minimum
            payslip_date=date(2024, 1, 1),
        )
        diff = calculate_minimum_wage_difference(payslip)
        assert diff == Decimal("0")

    def test_calculate_minimum_wage_difference_non_compliant(self):
        """Test minimum wage difference when below minimum."""
        payslip = create_test_payslip(
            hourly_rate=Decimal("25.00"),  # Below minimum
            hours=Decimal("182"),
            payslip_date=date(2024, 1, 1),
        )
        diff = calculate_minimum_wage_difference(payslip)
        # Minimum for Jan 2024 is ~30.61, so diff should be > 0
        assert diff > Decimal("0")
        # (30.61 - 25) * 182 = ~1021
        assert diff > Decimal("1000")

    def test_calculate_hours_rate_difference(self):
        """Test hours × rate difference calculation."""
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("5000.00"),  # Should be 5460
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("30.00"),
            gross_salary=Decimal("5000.00"),
            net_salary=Decimal("4000.00"),
        )
        diff = calculate_hours_rate_difference(payslip)
        assert diff == Decimal("460.00")

    def test_calculate_expected_overtime(self):
        """Test overtime calculation."""
        payslip = create_test_payslip(
            hourly_rate=Decimal("30.00"),
            overtime_hours=Decimal("10"),
        )
        expected_overtime = calculate_expected_overtime(payslip)
        # 30 * 1.25 * 10 = 375
        assert expected_overtime == Decimal("375.00")

    def test_calculate_pension_difference(self):
        """Test pension difference calculation."""
        payslip = create_test_payslip(
            hourly_rate=Decimal("54.95"),  # ~10000 gross
            pension=Decimal("300"),  # Should be ~600 (6%)
        )
        payslip.gross_salary = Decimal("10000.00")

        diff = calculate_pension_difference(payslip)
        # 6% of 10000 = 600, missing 300
        assert diff == Decimal("300.00")

    def test_calculate_total_missing(self):
        """Test total missing calculation."""
        payslip = create_test_payslip(
            hourly_rate=Decimal("25.00"),  # Below minimum
            hours=Decimal("182"),
            pension=Decimal("0"),
        )
        payslip.gross_salary = Decimal("4550.00")

        total = calculate_total_missing(payslip)
        assert total > Decimal("0")

    def test_categorize_violation(self):
        """Test violation categorization."""
        violation = Violation(
            violation_type=ViolationType.MINIMUM_WAGE,
            description="Test",
            description_hebrew="בדיקה",
            expected_value=Decimal("100"),
            actual_value=Decimal("80"),
            missing_amount=Decimal("20"),
        )
        category = categorize_violation(violation)
        assert category == "שכר מינימום"


class TestAggregator:
    """Tests for result aggregation."""

    def test_empty_aggregator(self):
        """Test aggregator with no analyses."""
        aggregator = ResultAggregator()
        results = aggregator.get_results()

        assert results.total_payslips == 0
        assert results.total_missing == Decimal("0")

    def test_add_compliant_analysis(self):
        """Test adding a compliant payslip."""
        aggregator = ResultAggregator()
        payslip = create_test_payslip(hourly_rate=Decimal("35.00"))
        analysis = create_test_analysis(payslip, violations=[])

        aggregator.add_analysis(analysis)
        results = aggregator.get_results()

        assert results.total_payslips == 1
        assert results.compliant_payslips == 1
        assert results.non_compliant_payslips == 0

    def test_add_non_compliant_analysis(self):
        """Test adding a non-compliant payslip."""
        aggregator = ResultAggregator()
        payslip = create_test_payslip(
            hourly_rate=Decimal("25.00"),
            payslip_date=date(2024, 1, 1),
        )

        violation = Violation(
            violation_type=ViolationType.MINIMUM_WAGE,
            description="Below minimum wage",
            description_hebrew="שכר מתחת למינימום",
            expected_value=Decimal("5571"),
            actual_value=Decimal("4550"),
            missing_amount=Decimal("1021"),
        )

        analysis = create_test_analysis(payslip, violations=[violation])
        aggregator.add_analysis(analysis)
        results = aggregator.get_results()

        assert results.total_payslips == 1
        assert results.non_compliant_payslips == 1
        assert results.total_missing == Decimal("1021")
        assert "January 2024" in results.problem_months

    def test_aggregate_multiple_payslips(self):
        """Test aggregating multiple payslips."""
        analyses = []

        # January - violation
        payslip1 = create_test_payslip(
            payslip_date=date(2024, 1, 1),
            hourly_rate=Decimal("25.00"),
        )
        violation1 = Violation(
            violation_type=ViolationType.MINIMUM_WAGE,
            description="Test",
            description_hebrew="בדיקה",
            expected_value=Decimal("100"),
            actual_value=Decimal("80"),
            missing_amount=Decimal("500"),
        )
        analyses.append(create_test_analysis(payslip1, [violation1]))

        # February - compliant
        payslip2 = create_test_payslip(
            payslip_date=date(2024, 2, 1),
            hourly_rate=Decimal("35.00"),
        )
        analyses.append(create_test_analysis(payslip2, []))

        # March - violation
        payslip3 = create_test_payslip(
            payslip_date=date(2024, 3, 1),
            hourly_rate=Decimal("25.00"),
        )
        violation3 = Violation(
            violation_type=ViolationType.MISSING_PENSION,
            description="Test",
            description_hebrew="בדיקה",
            expected_value=Decimal("100"),
            actual_value=Decimal("0"),
            missing_amount=Decimal("300"),
        )
        analyses.append(create_test_analysis(payslip3, [violation3]))

        results = aggregate_analyses(analyses)

        assert results.total_payslips == 3
        assert results.compliant_payslips == 1
        assert results.non_compliant_payslips == 2
        assert results.total_missing == Decimal("800")
        assert len(results.problem_months) == 2

    def test_violation_summary(self):
        """Test violation summary tracking."""
        summary = ViolationSummary(violation_type=ViolationType.MINIMUM_WAGE)

        violation1 = Violation(
            violation_type=ViolationType.MINIMUM_WAGE,
            description="Test",
            description_hebrew="בדיקה",
            expected_value=Decimal("100"),
            actual_value=Decimal("80"),
            missing_amount=Decimal("100"),
        )
        violation2 = Violation(
            violation_type=ViolationType.MINIMUM_WAGE,
            description="Test",
            description_hebrew="בדיקה",
            expected_value=Decimal("100"),
            actual_value=Decimal("70"),
            missing_amount=Decimal("200"),
        )

        summary.add_violation(violation1, "January 2024")
        summary.add_violation(violation2, "February 2024")

        assert summary.occurrence_count == 2
        assert summary.total_missing == Decimal("300")
        assert summary.min_amount == Decimal("100")
        assert summary.max_amount == Decimal("200")
        assert summary.avg_amount == Decimal("150.00")


class TestStatistics:
    """Tests for statistical calculations."""

    def test_calculate_statistics(self):
        """Test statistics calculation."""
        analyses = []

        for i in range(3):
            payslip = create_test_payslip(
                payslip_date=date(2024, i + 1, 1),
                hourly_rate=Decimal("25.00"),
            )
            violation = Violation(
                violation_type=ViolationType.MINIMUM_WAGE,
                description="Test",
                description_hebrew="בדיקה",
                expected_value=Decimal("100"),
                actual_value=Decimal("80"),
                missing_amount=Decimal(str(100 * (i + 1))),
            )
            analyses.append(create_test_analysis(payslip, [violation]))

        results = aggregate_analyses(analyses)
        stats = calculate_statistics(results)

        assert stats.total_violations == 3
        assert stats.unique_violation_types == 1
        assert stats.total_missing == Decimal("600")  # 100 + 200 + 300

    def test_compliance_metrics(self):
        """Test compliance metrics calculation."""
        analyses = []

        # 2 compliant
        for _ in range(2):
            payslip = create_test_payslip(hourly_rate=Decimal("35.00"))
            analyses.append(create_test_analysis(payslip, []))

        # 1 non-compliant
        payslip = create_test_payslip(hourly_rate=Decimal("25.00"))
        violation = Violation(
            violation_type=ViolationType.MINIMUM_WAGE,
            description="Test",
            description_hebrew="בדיקה",
            expected_value=Decimal("100"),
            actual_value=Decimal("80"),
            missing_amount=Decimal("1000"),
        )
        analyses.append(create_test_analysis(payslip, [violation]))

        results = aggregate_analyses(analyses)
        metrics = calculate_compliance_metrics(results)

        assert metrics.total_payslips == 3
        assert metrics.compliant_payslips == 2
        # 66.7% compliance
        assert metrics.compliance_rate >= Decimal("66")
        assert metrics.compliance_rate <= Decimal("67")


class TestMissingAmountCalculator:
    """Tests for the main calculator class."""

    def test_calculator_initialization(self):
        """Test calculator initialization."""
        calc = MissingAmountCalculator()
        assert calc.get_total_missing() == Decimal("0")

    def test_add_compliant_payslip(self):
        """Test adding a compliant payslip."""
        calc = MissingAmountCalculator()
        payslip = create_test_payslip(
            hourly_rate=Decimal("35.00"),
            pension=Decimal("360"),  # 6% of ~6000
        )

        analysis = calc.add_payslip(payslip)

        assert analysis.is_compliant
        assert calc.get_total_missing() == Decimal("0")

    def test_add_non_compliant_payslip(self):
        """Test adding a non-compliant payslip."""
        calc = MissingAmountCalculator()
        payslip = create_test_payslip(
            hourly_rate=Decimal("25.00"),  # Below minimum
            pension=Decimal("0"),  # No pension
        )

        analysis = calc.add_payslip(payslip)

        assert not analysis.is_compliant
        assert calc.get_total_missing() > Decimal("0")

    def test_get_summary(self):
        """Test getting summary dictionary."""
        calc = MissingAmountCalculator()
        payslip = create_test_payslip(
            hourly_rate=Decimal("25.00"),
            payslip_date=date(2024, 1, 1),
        )
        calc.add_payslip(payslip)

        summary = calc.get_summary()

        assert "total_missing" in summary
        assert "total_payslips" in summary
        assert "compliance_rate" in summary
        assert "problem_months" in summary
        assert summary["total_payslips"] == 1

    def test_reset(self):
        """Test calculator reset."""
        calc = MissingAmountCalculator()
        payslip = create_test_payslip(hourly_rate=Decimal("25.00"))
        calc.add_payslip(payslip)

        assert calc.get_total_missing() > Decimal("0")

        calc.reset()

        assert calc.get_total_missing() == Decimal("0")

    def test_generate_report(self):
        """Test report generation."""
        calc = MissingAmountCalculator()
        payslip = create_test_payslip(
            hourly_rate=Decimal("25.00"),
            payslip_date=date(2024, 1, 1),
        )
        calc.add_payslip(payslip)

        report = calc.generate_report()

        assert report.total_payslips == 1
        assert len(report.payslip_analyses) == 1
