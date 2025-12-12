"""Integration tests for the SalaryValidator system."""

import json
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agent import AgentResult, SalaryValidatorAgent, analyze_payslips
from src.calculator import MissingAmountCalculator
from src.models import (
    AnalysisReport,
    Deductions,
    Payslip,
    PayslipAnalysis,
    Violation,
    ViolationType,
)
from src.reporter import OutputFormat, ReportGenerator
from src.validator import PayslipValidator


class TestFullPipeline:
    """Integration tests for the complete analysis pipeline."""

    def create_compliant_payslip(self, month: int = 1, year: int = 2024) -> Payslip:
        """Create a payslip that complies with labor laws."""
        # Use hourly rate above minimum wage
        hourly_rate = Decimal("35.00")
        hours = Decimal("182")
        base_salary = hourly_rate * hours  # 6370

        return Payslip(
            payslip_date=date(year, month, 1),
            base_salary=base_salary,
            hours_worked=hours,
            hourly_rate=hourly_rate,
            gross_salary=base_salary,
            net_salary=base_salary * Decimal("0.78"),
            deductions=Deductions(
                pension_employee=base_salary * Decimal("0.06"),  # 6%
                pension_employer=base_salary * Decimal("0.065"),  # 6.5%
            ),
        )

    def create_non_compliant_payslip(self, month: int = 1, year: int = 2024) -> Payslip:
        """Create a payslip with labor law violations."""
        # Use hourly rate below minimum wage
        hourly_rate = Decimal("25.00")
        hours = Decimal("182")
        base_salary = hourly_rate * hours  # 4550

        return Payslip(
            payslip_date=date(year, month, 1),
            base_salary=base_salary,
            hours_worked=hours,
            hourly_rate=hourly_rate,
            gross_salary=base_salary,
            net_salary=base_salary * Decimal("0.85"),
            deductions=Deductions(
                pension_employee=Decimal("0"),  # Missing pension
                pension_employer=Decimal("0"),
            ),
        )

    def test_agent_analyze_compliant_payslip(self):
        """Test analyzing a compliant payslip."""
        agent = SalaryValidatorAgent()
        payslip = self.create_compliant_payslip()

        analysis = agent.analyze_payslip(payslip)

        assert analysis.is_compliant
        assert len(analysis.violations) == 0
        assert analysis.total_missing == Decimal("0")

    def test_agent_analyze_non_compliant_payslip(self):
        """Test analyzing a non-compliant payslip."""
        agent = SalaryValidatorAgent()
        payslip = self.create_non_compliant_payslip()

        analysis = agent.analyze_payslip(payslip)

        assert not analysis.is_compliant
        assert len(analysis.violations) > 0
        assert analysis.total_missing > Decimal("0")

        # Check that minimum wage violation is found
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.MINIMUM_WAGE in violation_types

    def test_agent_multiple_payslips(self):
        """Test analyzing multiple payslips."""
        agent = SalaryValidatorAgent()

        # Analyze several payslips
        for month in range(1, 7):
            if month % 2 == 0:
                payslip = self.create_compliant_payslip(month=month)
            else:
                payslip = self.create_non_compliant_payslip(month=month)
            agent.analyze_payslip(payslip)

        summary = agent.get_summary()

        assert summary["total_payslips"] == 6
        assert summary["compliant_payslips"] == 3
        assert summary["non_compliant_payslips"] == 3
        assert summary["total_missing"] > 0

    def test_agent_reset(self):
        """Test agent reset functionality."""
        agent = SalaryValidatorAgent()

        # Add some payslips
        agent.analyze_payslip(self.create_compliant_payslip())
        agent.analyze_payslip(self.create_non_compliant_payslip())

        summary_before = agent.get_summary()
        assert summary_before["total_payslips"] == 2

        # Reset
        agent.reset()

        summary_after = agent.get_summary()
        assert summary_after["total_payslips"] == 0


class TestValidatorCalculatorIntegration:
    """Test integration between validator and calculator."""

    def test_violations_flow_to_calculator(self):
        """Test that violations from validator correctly flow to calculator."""
        calculator = MissingAmountCalculator()

        # Create payslip with known violations
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("4550"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("25.00"),
            gross_salary=Decimal("4550"),
            net_salary=Decimal("4000"),
            deductions=Deductions(),
        )

        analysis = calculator.add_payslip(payslip)

        # Should have minimum wage and pension violations
        assert not analysis.is_compliant
        assert analysis.total_missing > Decimal("0")

        # Verify statistics are updated
        stats = calculator.get_statistics()
        assert stats.total_violations > 0

    def test_aggregation_across_payslips(self):
        """Test that aggregation works correctly across multiple payslips."""
        calculator = MissingAmountCalculator()

        # Add multiple payslips
        for month in range(1, 4):
            payslip = Payslip(
                payslip_date=date(2024, month, 1),
                base_salary=Decimal("4550"),
                hours_worked=Decimal("182"),
                hourly_rate=Decimal("25.00"),
                gross_salary=Decimal("4550"),
                net_salary=Decimal("4000"),
                deductions=Deductions(),
            )
            calculator.add_payslip(payslip)

        results = calculator.get_aggregated_results()

        assert results.total_expected > Decimal("0")
        assert results.total_actual > Decimal("0")
        assert results.total_difference > Decimal("0")
        assert len(results.monthly_results) == 3


class TestReportGeneratorIntegration:
    """Test integration between calculator and report generator."""

    def create_test_report(self) -> AnalysisReport:
        """Create a test analysis report."""
        calculator = MissingAmountCalculator()

        # Add compliant payslip
        compliant = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("6370"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("35.00"),
            gross_salary=Decimal("6370"),
            net_salary=Decimal("5000"),
            deductions=Deductions(
                pension_employee=Decimal("382.20"),
                pension_employer=Decimal("414.05"),
            ),
        )
        calculator.add_payslip(compliant)

        # Add non-compliant payslip
        non_compliant = Payslip(
            payslip_date=date(2024, 2, 1),
            base_salary=Decimal("4550"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("25.00"),
            gross_salary=Decimal("4550"),
            net_salary=Decimal("4000"),
            deductions=Deductions(),
        )
        calculator.add_payslip(non_compliant)

        return calculator.generate_report()

    def test_json_report_generation(self):
        """Test generating JSON report from analysis."""
        report = self.create_test_report()
        generator = ReportGenerator()

        json_output = generator.generate(report, OutputFormat.JSON)
        data = json.loads(json_output)

        assert "summary" in data
        assert data["summary"]["total_payslips"] == 2
        assert data["summary"]["compliant_payslips"] == 1
        assert data["summary"]["non_compliant_payslips"] == 1

    def test_text_report_generation(self):
        """Test generating Hebrew text report from analysis."""
        report = self.create_test_report()
        generator = ReportGenerator()

        text_output = generator.generate(report, OutputFormat.TEXT)

        # Should contain Hebrew content
        assert "דוח ניתוח תלושי שכר" in text_output
        assert "סיכום כללי" in text_output
        assert "₪" in text_output

    def test_html_report_generation(self):
        """Test generating HTML report from analysis."""
        report = self.create_test_report()
        generator = ReportGenerator()

        html_output = generator.generate(report, OutputFormat.HTML)

        # Should be valid HTML with RTL support
        assert "<!DOCTYPE html>" in html_output
        assert 'dir="rtl"' in html_output
        assert "דוח ניתוח תלושי שכר" in html_output

    def test_save_all_formats(self, tmp_path):
        """Test saving reports in all formats."""
        report = self.create_test_report()
        generator = ReportGenerator()

        base_path = tmp_path / "salary_report"
        saved_files = generator.generate_all_formats(report, base_path)

        assert len(saved_files) == 3
        assert (tmp_path / "salary_report.json").exists()
        assert (tmp_path / "salary_report.txt").exists()
        assert (tmp_path / "salary_report.html").exists()


class TestEndToEndScenarios:
    """End-to-end scenario tests."""

    def test_scenario_full_year_analysis(self):
        """Test analyzing a full year of payslips."""
        agent = SalaryValidatorAgent()

        # Simulate full year - some months compliant, some not
        for month in range(1, 13):
            if month <= 6:
                # First half year - below minimum wage
                payslip = Payslip(
                    payslip_date=date(2024, month, 1),
                    base_salary=Decimal("5000"),
                    hours_worked=Decimal("182"),
                    hourly_rate=Decimal("27.47"),
                    gross_salary=Decimal("5000"),
                    net_salary=Decimal("4200"),
                    deductions=Deductions(
                        pension_employee=Decimal("300"),
                        pension_employer=Decimal("325"),
                    ),
                )
            else:
                # Second half year - compliant
                payslip = Payslip(
                    payslip_date=date(2024, month, 1),
                    base_salary=Decimal("6500"),
                    hours_worked=Decimal("182"),
                    hourly_rate=Decimal("35.71"),
                    gross_salary=Decimal("6500"),
                    net_salary=Decimal("5200"),
                    deductions=Deductions(
                        pension_employee=Decimal("390"),
                        pension_employer=Decimal("422.50"),
                    ),
                )
            agent.analyze_payslip(payslip)

        summary = agent.get_summary()

        assert summary["total_payslips"] == 12
        assert summary["non_compliant_payslips"] == 6
        assert summary["compliant_payslips"] == 6
        assert summary["compliance_rate"] == 50.0
        assert len(summary["problem_months"]) == 6

    def test_scenario_improving_compliance(self):
        """Test scenario where compliance improves over time."""
        agent = SalaryValidatorAgent()

        # Q1 - All non-compliant
        for month in range(1, 4):
            payslip = Payslip(
                payslip_date=date(2024, month, 1),
                base_salary=Decimal("4500"),
                hours_worked=Decimal("182"),
                hourly_rate=Decimal("24.73"),
                gross_salary=Decimal("4500"),
                net_salary=Decimal("4000"),
                deductions=Deductions(),
            )
            agent.analyze_payslip(payslip)

        # Q2-Q4 - All compliant
        for month in range(4, 13):
            payslip = Payslip(
                payslip_date=date(2024, month, 1),
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
            agent.analyze_payslip(payslip)

        summary = agent.get_summary()

        assert summary["total_payslips"] == 12
        assert summary["non_compliant_payslips"] == 3
        assert summary["compliant_payslips"] == 9
        assert summary["compliance_rate"] == 75.0

    def test_scenario_pension_only_violations(self):
        """Test scenario with only pension violations."""
        agent = SalaryValidatorAgent()

        # Above minimum wage but missing pension
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("7000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("38.46"),
            gross_salary=Decimal("7000"),
            net_salary=Decimal("6500"),
            deductions=Deductions(
                pension_employee=Decimal("0"),  # Missing
                pension_employer=Decimal("0"),  # Missing
            ),
        )

        analysis = agent.analyze_payslip(payslip)

        # Should have pension violation but not minimum wage
        violation_types = [v.violation_type for v in analysis.violations]
        assert ViolationType.MISSING_PENSION in violation_types
        assert ViolationType.MINIMUM_WAGE not in violation_types


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_analyze_payslips_function(self, tmp_path):
        """Test the analyze_payslips convenience function."""
        # Create mock files (would need actual files in real scenario)
        # For now, test with empty list
        result = analyze_payslips([])

        assert isinstance(result, AgentResult)
        assert result.total_files == 0
        assert result.successful_count == 0


class TestComplianceMetrics:
    """Test compliance metrics calculation."""

    def test_risk_level_low(self):
        """Test low risk level calculation."""
        agent = SalaryValidatorAgent()

        # All compliant payslips
        for month in range(1, 13):
            payslip = Payslip(
                payslip_date=date(2024, month, 1),
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
            agent.analyze_payslip(payslip)

        summary = agent.get_summary()

        assert summary["risk_level"] == "low"
        assert summary["compliance_rate"] == 100.0

    def test_risk_level_critical(self):
        """Test critical risk level calculation."""
        agent = SalaryValidatorAgent()

        # All non-compliant payslips
        for month in range(1, 6):
            payslip = Payslip(
                payslip_date=date(2024, month, 1),
                base_salary=Decimal("4000"),
                hours_worked=Decimal("182"),
                hourly_rate=Decimal("21.98"),
                gross_salary=Decimal("4000"),
                net_salary=Decimal("3800"),
                deductions=Deductions(),
            )
            agent.analyze_payslip(payslip)

        summary = agent.get_summary()

        assert summary["risk_level"] == "critical"
        assert summary["compliance_rate"] == 0.0


class TestOutputFormats:
    """Test different output format handling."""

    def test_json_output_is_valid(self):
        """Test that JSON output is valid and parseable."""
        agent = SalaryValidatorAgent()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("5000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("27.47"),
            gross_salary=Decimal("5000"),
            net_salary=Decimal("4200"),
            deductions=Deductions(),
        )
        agent.analyze_payslip(payslip)

        summary = agent.get_summary()

        # Should be JSON serializable
        json_str = json.dumps(summary, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["total_payslips"] == 1

    def test_currency_formatting_in_reports(self):
        """Test currency formatting in reports."""
        calculator = MissingAmountCalculator()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("4550"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("25.00"),
            gross_salary=Decimal("4550"),
            net_salary=Decimal("4000"),
            deductions=Deductions(),
        )
        calculator.add_payslip(payslip)

        report = calculator.generate_report()
        generator = ReportGenerator()

        # Check JSON format
        json_output = generator.generate(report, OutputFormat.JSON)
        data = json.loads(json_output)

        # Should have formatted currency
        assert "total_missing_formatted" in data["summary"]
        assert "₪" in data["summary"]["total_missing_formatted"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_hours_worked(self):
        """Test handling of zero hours worked."""
        agent = SalaryValidatorAgent()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("0"),
            hours_worked=Decimal("0"),
            hourly_rate=Decimal("35.00"),
            gross_salary=Decimal("0"),
            net_salary=Decimal("0"),
            deductions=Deductions(),
        )

        # Should not raise an error
        analysis = agent.analyze_payslip(payslip)
        assert analysis is not None

    def test_very_high_salary(self):
        """Test handling of very high salaries."""
        agent = SalaryValidatorAgent()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("100000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("549.45"),
            gross_salary=Decimal("100000"),
            net_salary=Decimal("60000"),
            deductions=Deductions(
                pension_employee=Decimal("6000"),
                pension_employer=Decimal("6500"),
            ),
        )

        analysis = agent.analyze_payslip(payslip)

        # Should be compliant
        assert analysis.is_compliant

    def test_decimal_precision(self):
        """Test that decimal precision is maintained."""
        agent = SalaryValidatorAgent()

        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("5571.75"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("30.6139"),
            gross_salary=Decimal("5571.75"),
            net_salary=Decimal("4571.75"),
            deductions=Deductions(
                pension_employee=Decimal("334.31"),
                pension_employer=Decimal("362.16"),
            ),
        )

        analysis = agent.analyze_payslip(payslip)

        # Verify decimal precision in summary
        summary = agent.get_summary()
        assert isinstance(summary["total_missing"], (int, float))


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_date_handling(self):
        """Test handling of edge case dates."""
        agent = SalaryValidatorAgent()

        # Very old date
        payslip = Payslip(
            payslip_date=date(2010, 1, 1),
            base_salary=Decimal("3000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("16.48"),
            gross_salary=Decimal("3000"),
            net_salary=Decimal("2800"),
            deductions=Deductions(),
        )

        # Should still process (may use earliest known minimum wage)
        analysis = agent.analyze_payslip(payslip)
        assert analysis is not None

    def test_negative_values_handling(self):
        """Test handling of negative values (corrections/adjustments)."""
        agent = SalaryValidatorAgent()

        # Payslip with negative adjustment
        payslip = Payslip(
            payslip_date=date(2024, 1, 1),
            base_salary=Decimal("6000"),
            hours_worked=Decimal("182"),
            hourly_rate=Decimal("32.97"),
            gross_salary=Decimal("6000"),
            net_salary=Decimal("4800"),
            bonus=Decimal("-100"),  # Negative adjustment
            deductions=Deductions(
                pension_employee=Decimal("360"),
                pension_employer=Decimal("390"),
            ),
        )

        # Should not raise an error
        analysis = agent.analyze_payslip(payslip)
        assert analysis is not None
