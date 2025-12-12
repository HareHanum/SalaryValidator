"""JSON report generator."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional, Union

from src.logging_config import get_logger
from src.models import AnalysisReport, PayslipAnalysis, Violation
from src.calculator import AggregatedResults, ComplianceMetrics, ViolationStatistics
from src.reporter.formatters import format_date_hebrew
from src.reporter.templates import get_violation_type_name, RISK_LEVEL_HE

logger = get_logger("reporter.json_reporter")


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


def violation_to_dict(violation: Violation) -> dict:
    """Convert a Violation to a dictionary."""
    return {
        "type": violation.violation_type.value,
        "type_hebrew": get_violation_type_name(violation.violation_type),
        "description": violation.description,
        "description_hebrew": violation.description_hebrew,
        "expected_value": float(violation.expected_value),
        "actual_value": float(violation.actual_value),
        "missing_amount": float(violation.missing_amount),
        "legal_reference": violation.legal_reference,
    }


def analysis_to_dict(analysis: PayslipAnalysis) -> dict:
    """Convert a PayslipAnalysis to a dictionary."""
    payslip = analysis.payslip

    return {
        "month": format_date_hebrew(payslip.payslip_date),
        "month_date": payslip.payslip_date.isoformat(),
        "employee_name": payslip.employee_name,
        "employer_name": payslip.employer_name,
        "is_compliant": analysis.is_compliant,
        "total_missing": float(analysis.total_missing),
        "violation_count": len(analysis.violations),
        "salary_details": {
            "base_salary": float(payslip.base_salary),
            "hours_worked": float(payslip.hours_worked),
            "hourly_rate": float(payslip.hourly_rate),
            "overtime_hours": float(payslip.overtime_hours),
            "overtime_pay": float(payslip.overtime_pay),
            "gross_salary": float(payslip.gross_salary),
            "net_salary": float(payslip.net_salary),
        },
        "deductions": {
            "income_tax": float(payslip.deductions.income_tax),
            "national_insurance": float(payslip.deductions.national_insurance),
            "health_insurance": float(payslip.deductions.health_insurance),
            "pension_employee": float(payslip.deductions.pension_employee),
            "pension_employer": float(payslip.deductions.pension_employer),
        },
        "violations": [violation_to_dict(v) for v in analysis.violations],
    }


def create_json_report(
    report: AnalysisReport,
    results: Optional[AggregatedResults] = None,
    stats: Optional[ViolationStatistics] = None,
    metrics: Optional[ComplianceMetrics] = None,
) -> dict:
    """
    Create a complete JSON report structure.

    Args:
        report: The AnalysisReport to convert
        results: Optional aggregated results for additional data
        stats: Optional statistics for additional data
        metrics: Optional compliance metrics

    Returns:
        Dictionary suitable for JSON serialization
    """
    # Basic report structure
    json_report = {
        "report_metadata": {
            "generated_at": date.today().isoformat(),
            "total_payslips": report.total_payslips,
            "report_type": "salary_validation",
            "language": "he",
        },
        "summary": {
            "total_missing": float(report.total_missing),
            "total_missing_formatted": f"₪{report.total_missing:,.2f}",
            "compliant_payslips": report.compliant_payslips,
            "non_compliant_payslips": report.total_payslips - report.compliant_payslips,
            "problem_months": report.problem_months,
            "violation_types": report.violation_types,
        },
        "monthly_details": [
            analysis_to_dict(analysis) for analysis in report.payslip_analyses
        ],
    }

    # Add compliance metrics if available
    if metrics:
        json_report["compliance"] = {
            "rate": float(metrics.compliance_rate),
            "rate_formatted": f"{metrics.compliance_rate:.1f}%",
            "risk_level": metrics.risk_level,
            "risk_level_hebrew": RISK_LEVEL_HE.get(metrics.risk_level, metrics.risk_level),
            "primary_risk_area": metrics.primary_risk_area,
            "total_liability": float(metrics.total_liability),
            "monthly_average_liability": float(metrics.monthly_average_liability),
            "projected_annual_liability": float(metrics.projected_annual_liability),
        }

    # Add statistics if available
    if stats:
        json_report["statistics"] = {
            "total_violations": stats.total_violations,
            "unique_violation_types": stats.unique_violation_types,
            "min_violation_amount": float(stats.min_single_violation) if stats.min_single_violation else None,
            "max_violation_amount": float(stats.max_single_violation) if stats.max_single_violation else None,
            "avg_violation_amount": float(stats.avg_violation_amount) if stats.avg_violation_amount else None,
            "most_common_type": stats.most_common_type,
            "most_costly_type": stats.most_costly_type,
            "violations_by_type": stats.violations_by_type,
            "amounts_by_type": {k: float(v) for k, v in (stats.amounts_by_type or {}).items()},
        }

    # Add violation type breakdown if results available
    if results and results.by_violation_type:
        json_report["violation_breakdown"] = {}
        for vtype, summary in results.by_violation_type.items():
            json_report["violation_breakdown"][vtype.value] = {
                "type_hebrew": get_violation_type_name(vtype),
                "occurrence_count": summary.occurrence_count,
                "total_missing": float(summary.total_missing),
                "affected_months": summary.affected_months,
                "min_amount": float(summary.min_amount) if summary.min_amount else None,
                "max_amount": float(summary.max_amount) if summary.max_amount else None,
                "avg_amount": float(summary.avg_amount) if summary.avg_amount else None,
            }

    return json_report


class JSONReporter:
    """Reporter for generating JSON output."""

    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        """
        Initialize JSON reporter.

        Args:
            indent: JSON indentation level
            ensure_ascii: Whether to escape non-ASCII characters
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def generate(
        self,
        report: AnalysisReport,
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
    ) -> str:
        """
        Generate JSON report string.

        Args:
            report: The AnalysisReport to convert
            results: Optional aggregated results
            stats: Optional statistics
            metrics: Optional compliance metrics

        Returns:
            JSON string
        """
        json_data = create_json_report(report, results, stats, metrics)

        return json.dumps(
            json_data,
            cls=DecimalEncoder,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
        )

    def save(
        self,
        report: AnalysisReport,
        output_path: Union[str, Path],
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
    ) -> Path:
        """
        Save JSON report to file.

        Args:
            report: The AnalysisReport to save
            output_path: Path to save the file
            results: Optional aggregated results
            stats: Optional statistics
            metrics: Optional compliance metrics

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)

        json_str = self.generate(report, results, stats, metrics)

        output_path.write_text(json_str, encoding="utf-8")

        logger.info(f"JSON report saved to: {output_path}")
        return output_path
