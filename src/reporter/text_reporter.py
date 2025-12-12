"""Plain text Hebrew report generator."""

from datetime import date
from io import StringIO
from pathlib import Path
from typing import Optional, Union

from src.logging_config import get_logger
from src.models import AnalysisReport, PayslipAnalysis, Violation
from src.calculator import AggregatedResults, ComplianceMetrics, ViolationStatistics
from src.reporter.formatters import (
    create_separator,
    format_currency,
    format_date_full_hebrew,
    format_date_hebrew,
    format_hours,
    format_payslip_count,
    format_percentage,
    format_violation_count,
)
from src.reporter.templates import (
    LEGAL_NOTICE,
    REPORT_FOOTER,
    RISK_LEVEL_DESCRIPTIONS,
    RISK_LEVEL_HE,
    SECTION_HEADERS,
    get_recommendation,
    get_risk_level_text,
    get_violation_type_name,
)

logger = get_logger("reporter.text_reporter")


class TextReporter:
    """Reporter for generating plain text Hebrew reports."""

    def __init__(self, line_width: int = 70):
        """
        Initialize text reporter.

        Args:
            line_width: Maximum line width for formatting
        """
        self.line_width = line_width

    def generate(
        self,
        report: AnalysisReport,
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
        include_legal_notice: bool = True,
    ) -> str:
        """
        Generate plain text Hebrew report.

        Args:
            report: The AnalysisReport to convert
            results: Optional aggregated results
            stats: Optional statistics
            metrics: Optional compliance metrics
            include_legal_notice: Whether to include legal notice

        Returns:
            Plain text report string
        """
        output = StringIO()

        # Title
        self._write_title(output)

        # Summary section
        self._write_summary(output, report, metrics)

        # Risk assessment
        if metrics:
            self._write_risk_assessment(output, metrics)

        # Violation breakdown
        if results and results.by_violation_type:
            self._write_violation_breakdown(output, results)

        # Monthly details
        self._write_monthly_details(output, report)

        # Recommendations
        self._write_recommendations(output, report)

        # Legal notice
        if include_legal_notice:
            output.write(LEGAL_NOTICE)
            output.write("\n")

        # Footer
        output.write(REPORT_FOOTER.format(date=format_date_full_hebrew(date.today())))

        return output.getvalue()

    def _write_title(self, output: StringIO) -> None:
        """Write report title."""
        output.write("\n")
        output.write("=" * self.line_width + "\n")
        output.write(f"{SECTION_HEADERS['title']:^{self.line_width}}\n")
        output.write("=" * self.line_width + "\n")
        output.write("\n")

    def _write_summary(
        self,
        output: StringIO,
        report: AnalysisReport,
        metrics: Optional[ComplianceMetrics],
    ) -> None:
        """Write summary section."""
        output.write(f"{SECTION_HEADERS['summary']}\n")
        output.write(create_separator("-", 30) + "\n")

        non_compliant = report.total_payslips - report.compliant_payslips

        output.write(f"תלושים שנותחו: {format_payslip_count(report.total_payslips)}\n")
        output.write(f"תלושים תקינים: {format_payslip_count(report.compliant_payslips)}\n")
        output.write(f"תלושים עם הפרות: {format_payslip_count(non_compliant)}\n")
        output.write("\n")

        output.write(f"סה\"כ סכום חסר: {format_currency(report.total_missing)}\n")

        if metrics:
            output.write(f"שיעור תאימות: {format_percentage(metrics.compliance_rate)}\n")
            output.write(f"חבות שנתית צפויה: {format_currency(metrics.projected_annual_liability)}\n")

        output.write("\n")

        if report.problem_months:
            output.write("חודשים בעייתיים:\n")
            for month in report.problem_months:
                output.write(f"  • {month}\n")
            output.write("\n")

    def _write_risk_assessment(
        self, output: StringIO, metrics: ComplianceMetrics
    ) -> None:
        """Write risk assessment section."""
        risk_name, risk_desc = get_risk_level_text(metrics.risk_level)

        output.write("הערכת סיכון\n")
        output.write(create_separator("-", 30) + "\n")
        output.write(f"רמת סיכון: {risk_name}\n")
        output.write(f"{risk_desc}\n")

        if metrics.primary_risk_area:
            output.write(f"תחום סיכון עיקרי: {metrics.primary_risk_area}\n")

        output.write("\n")

    def _write_violation_breakdown(
        self, output: StringIO, results: AggregatedResults
    ) -> None:
        """Write violation breakdown by type."""
        output.write(f"{SECTION_HEADERS['violations']}\n")
        output.write(create_separator("-", 30) + "\n")

        for vtype, summary in results.by_violation_type.items():
            type_name = get_violation_type_name(vtype)
            output.write(f"\n{type_name}:\n")
            output.write(f"  מספר מקרים: {summary.occurrence_count}\n")
            output.write(f"  סה\"כ חסר: {format_currency(summary.total_missing)}\n")

            if summary.avg_amount:
                output.write(f"  ממוצע למקרה: {format_currency(summary.avg_amount)}\n")

            output.write(f"  חודשים מושפעים: {', '.join(summary.affected_months)}\n")

        output.write("\n")

    def _write_monthly_details(
        self, output: StringIO, report: AnalysisReport
    ) -> None:
        """Write detailed monthly breakdown."""
        output.write(f"{SECTION_HEADERS['monthly_breakdown']}\n")
        output.write(create_separator("-", 30) + "\n")

        for analysis in report.payslip_analyses:
            self._write_payslip_analysis(output, analysis)

    def _write_payslip_analysis(
        self, output: StringIO, analysis: PayslipAnalysis
    ) -> None:
        """Write analysis for a single payslip."""
        payslip = analysis.payslip
        month_str = format_date_hebrew(payslip.payslip_date)

        output.write(f"\n{month_str}\n")
        output.write(create_separator("~", 40) + "\n")

        # Basic info
        output.write(f"שכר ברוטו: {format_currency(payslip.gross_salary)}\n")
        output.write(f"שכר נטו: {format_currency(payslip.net_salary)}\n")
        output.write(f"שעות עבודה: {format_hours(payslip.hours_worked)}\n")
        output.write(f"שכר שעתי: {format_currency(payslip.hourly_rate)}\n")

        if analysis.is_compliant:
            output.write("\n✓ תלוש תקין - לא נמצאו הפרות\n")
        else:
            output.write(f"\n✗ נמצאו {format_violation_count(len(analysis.violations))}\n")
            output.write(f"סכום חסר: {format_currency(analysis.total_missing)}\n\n")

            for violation in analysis.violations:
                self._write_violation(output, violation)

    def _write_violation(self, output: StringIO, violation: Violation) -> None:
        """Write a single violation."""
        type_name = get_violation_type_name(violation.violation_type)

        output.write(f"  [{type_name}]\n")
        output.write(f"  {violation.description_hebrew}\n")
        output.write(f"  צפוי: {format_currency(violation.expected_value)}\n")
        output.write(f"  בפועל: {format_currency(violation.actual_value)}\n")
        output.write(f"  חסר: {format_currency(violation.missing_amount)}\n")

        if violation.legal_reference:
            output.write(f"  מקור חוקי: {violation.legal_reference}\n")

        output.write("\n")

    def _write_recommendations(
        self, output: StringIO, report: AnalysisReport
    ) -> None:
        """Write recommendations section."""
        # Collect unique violation types
        violation_types = set()
        for analysis in report.payslip_analyses:
            for violation in analysis.violations:
                violation_types.add(violation.violation_type)

        if not violation_types:
            return

        output.write(f"{SECTION_HEADERS['recommendations']}\n")
        output.write(create_separator("-", 30) + "\n")

        for vtype in violation_types:
            type_name = get_violation_type_name(vtype)
            recommendation = get_recommendation(vtype)
            output.write(f"\n{type_name}:\n")
            output.write(f"  {recommendation}\n")

        output.write("\n")

    def save(
        self,
        report: AnalysisReport,
        output_path: Union[str, Path],
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
        include_legal_notice: bool = True,
    ) -> Path:
        """
        Save text report to file.

        Args:
            report: The AnalysisReport to save
            output_path: Path to save the file
            results: Optional aggregated results
            stats: Optional statistics
            metrics: Optional compliance metrics
            include_legal_notice: Whether to include legal notice

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)

        text = self.generate(report, results, stats, metrics, include_legal_notice)

        output_path.write_text(text, encoding="utf-8")

        logger.info(f"Text report saved to: {output_path}")
        return output_path
