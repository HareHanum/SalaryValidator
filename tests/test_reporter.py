"""Tests for the reporter module."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.models import AnalysisReport, Deductions, Payslip, PayslipAnalysis, Violation, ViolationType
from src.reporter.formatters import (
    format_currency,
    format_date_hebrew,
    format_hours,
    format_payslip_count,
    format_percentage,
    format_violation_count,
)
from src.reporter.templates import (
    HEBREW_MONTHS,
    get_recommendation,
    get_risk_level_text,
    get_violation_type_name,
)
from src.reporter.json_reporter import JSONReporter, create_json_report
from src.reporter.text_reporter import TextReporter
from src.reporter.html_reporter import HTMLReporter
from src.reporter.report_generator import OutputFormat, ReportGenerator


def create_test_payslip(
    payslip_date: date = date(2024, 1, 1),
    hourly_rate: Decimal = Decimal("30.00"),
) -> Payslip:
    """Create a test payslip."""
    hours = Decimal("182")
    base_salary = hourly_rate * hours

    return Payslip(
        payslip_date=payslip_date,
        base_salary=base_salary,
        hours_worked=hours,
        hourly_rate=hourly_rate,
        gross_salary=base_salary,
        net_salary=base_salary * Decimal("0.8"),
        deductions=Deductions(),
    )


def create_test_violation() -> Violation:
    """Create a test violation."""
    return Violation(
        violation_type=ViolationType.MINIMUM_WAGE,
        description="Below minimum wage",
        description_hebrew="שכר מתחת למינימום",
        expected_value=Decimal("5571.75"),
        actual_value=Decimal("4550.00"),
        missing_amount=Decimal("1021.75"),
        legal_reference="חוק שכר מינימום",
    )


def create_test_report() -> AnalysisReport:
    """Create a test analysis report."""
    # Create payslips and analyses
    analyses = []

    # January - violation
    payslip1 = create_test_payslip(date(2024, 1, 1), Decimal("25.00"))
    analysis1 = PayslipAnalysis(
        payslip=payslip1,
        violations=[create_test_violation()],
    )
    analysis1.calculate_totals()
    analyses.append(analysis1)

    # February - compliant
    payslip2 = create_test_payslip(date(2024, 2, 1), Decimal("35.00"))
    analysis2 = PayslipAnalysis(payslip=payslip2, violations=[])
    analysis2.calculate_totals()
    analyses.append(analysis2)

    # Create report
    report = AnalysisReport(
        payslip_analyses=analyses,
        generated_at=date.today(),
    )
    report.calculate_summary()

    return report


class TestFormatters:
    """Tests for formatting utilities."""

    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(Decimal("1234.56")) == "₪1,234.56"
        assert format_currency(Decimal("1000")) == "₪1,000.00"
        assert format_currency(0) == "₪0.00"

    def test_format_percentage(self):
        """Test percentage formatting."""
        assert format_percentage(85.5) == "85.5%"
        assert format_percentage(100) == "100.0%"

    def test_format_hours(self):
        """Test hours formatting."""
        assert format_hours(Decimal("182")) == "182 שעות"
        assert format_hours(Decimal("182.5")) == "182.5 שעות"

    def test_format_date_hebrew(self):
        """Test Hebrew date formatting."""
        d = date(2024, 1, 15)
        result = format_date_hebrew(d)
        assert "ינואר" in result
        assert "2024" in result

    def test_format_violation_count(self):
        """Test violation count formatting."""
        assert format_violation_count(0) == "אין הפרות"
        assert format_violation_count(1) == "הפרה אחת"
        assert format_violation_count(2) == "2 הפרות"
        assert format_violation_count(5) == "5 הפרות"

    def test_format_payslip_count(self):
        """Test payslip count formatting."""
        assert format_payslip_count(0) == "אין תלושים"
        assert format_payslip_count(1) == "תלוש אחד"
        assert format_payslip_count(2) == "2 תלושים"


class TestTemplates:
    """Tests for template utilities."""

    def test_hebrew_months(self):
        """Test Hebrew month names."""
        assert HEBREW_MONTHS[1] == "ינואר"
        assert HEBREW_MONTHS[12] == "דצמבר"
        assert len(HEBREW_MONTHS) == 12

    def test_get_violation_type_name(self):
        """Test violation type name lookup."""
        assert get_violation_type_name(ViolationType.MINIMUM_WAGE) == "שכר מינימום"
        assert get_violation_type_name(ViolationType.MISSING_PENSION) == "הפרשות פנסיה"

    def test_get_risk_level_text(self):
        """Test risk level text."""
        name, desc = get_risk_level_text("low")
        assert name == "סיכון נמוך"
        assert len(desc) > 0

    def test_get_recommendation(self):
        """Test recommendation lookup."""
        rec = get_recommendation(ViolationType.MINIMUM_WAGE)
        assert "שכר" in rec or "מינימום" in rec


class TestJSONReporter:
    """Tests for JSON report generation."""

    def test_create_json_report(self):
        """Test JSON report creation."""
        report = create_test_report()
        json_data = create_json_report(report)

        assert "report_metadata" in json_data
        assert "summary" in json_data
        assert "monthly_details" in json_data
        assert json_data["summary"]["total_payslips"] == 2

    def test_json_reporter_generate(self):
        """Test JSON reporter generate method."""
        reporter = JSONReporter()
        report = create_test_report()

        json_str = reporter.generate(report)

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert "summary" in parsed

    def test_json_reporter_save(self, tmp_path):
        """Test saving JSON report to file."""
        reporter = JSONReporter()
        report = create_test_report()

        output_path = tmp_path / "report.json"
        saved_path = reporter.save(report, output_path)

        assert saved_path.exists()

        # Verify content
        content = json.loads(saved_path.read_text(encoding="utf-8"))
        assert "summary" in content


class TestTextReporter:
    """Tests for text report generation."""

    def test_text_reporter_generate(self):
        """Test text reporter generate method."""
        reporter = TextReporter()
        report = create_test_report()

        text = reporter.generate(report)

        # Check for Hebrew content
        assert "דוח ניתוח תלושי שכר" in text
        assert "סיכום כללי" in text
        assert "ינואר 2024" in text

    def test_text_reporter_includes_violations(self):
        """Test that violations are included."""
        reporter = TextReporter()
        report = create_test_report()

        text = reporter.generate(report)

        assert "שכר מינימום" in text
        assert "₪" in text

    def test_text_reporter_save(self, tmp_path):
        """Test saving text report to file."""
        reporter = TextReporter()
        report = create_test_report()

        output_path = tmp_path / "report.txt"
        saved_path = reporter.save(report, output_path)

        assert saved_path.exists()

        content = saved_path.read_text(encoding="utf-8")
        assert "דוח" in content


class TestHTMLReporter:
    """Tests for HTML report generation."""

    def test_html_reporter_generate(self):
        """Test HTML reporter generate method."""
        reporter = HTMLReporter()
        report = create_test_report()

        html = reporter.generate(report)

        # Check for HTML structure
        assert "<!DOCTYPE html>" in html
        assert '<html lang="he" dir="rtl">' in html
        assert "דוח ניתוח תלושי שכר" in html

    def test_html_reporter_includes_styles(self):
        """Test that CSS styles are included."""
        reporter = HTMLReporter()
        report = create_test_report()

        html = reporter.generate(report)

        assert "<style>" in html
        assert "summary-card" in html

    def test_html_reporter_save(self, tmp_path):
        """Test saving HTML report to file."""
        reporter = HTMLReporter()
        report = create_test_report()

        output_path = tmp_path / "report.html"
        saved_path = reporter.save(report, output_path)

        assert saved_path.exists()

        content = saved_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content


class TestReportGenerator:
    """Tests for the main report generator."""

    def test_generate_json(self):
        """Test generating JSON format."""
        generator = ReportGenerator()
        report = create_test_report()

        output = generator.generate(report, OutputFormat.JSON)

        # Should be valid JSON
        parsed = json.loads(output)
        assert "summary" in parsed

    def test_generate_text(self):
        """Test generating text format."""
        generator = ReportGenerator()
        report = create_test_report()

        output = generator.generate(report, OutputFormat.TEXT)

        assert "דוח" in output

    def test_generate_html(self):
        """Test generating HTML format."""
        generator = ReportGenerator()
        report = create_test_report()

        output = generator.generate(report, OutputFormat.HTML)

        assert "<!DOCTYPE html>" in output

    def test_save_auto_detect_json(self, tmp_path):
        """Test auto-detecting JSON format from extension."""
        generator = ReportGenerator()
        report = create_test_report()

        output_path = tmp_path / "report.json"
        saved_path = generator.save(report, output_path)

        assert saved_path.exists()
        content = saved_path.read_text(encoding="utf-8")
        json.loads(content)  # Should be valid JSON

    def test_save_auto_detect_html(self, tmp_path):
        """Test auto-detecting HTML format from extension."""
        generator = ReportGenerator()
        report = create_test_report()

        output_path = tmp_path / "report.html"
        saved_path = generator.save(report, output_path)

        assert saved_path.exists()
        content = saved_path.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_generate_all_formats(self, tmp_path):
        """Test generating all formats at once."""
        generator = ReportGenerator()
        report = create_test_report()

        base_path = tmp_path / "report"
        saved_files = generator.generate_all_formats(report, base_path)

        assert len(saved_files) == 3
        assert OutputFormat.JSON in saved_files
        assert OutputFormat.TEXT in saved_files
        assert OutputFormat.HTML in saved_files

        for path in saved_files.values():
            assert path.exists()
