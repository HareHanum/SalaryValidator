"""Main calculator for missing payment amounts."""

from decimal import Decimal
from pathlib import Path
from typing import Optional

from src.logging_config import get_logger
from src.models import AnalysisReport, Payslip, PayslipAnalysis
from src.parser import parse_payslip
from src.validator import validate_payslip
from src.calculator.aggregator import (
    AggregatedResults,
    ResultAggregator,
    aggregate_analyses,
    create_report,
)
from src.calculator.calculations import (
    calculate_expected_base_salary,
    calculate_minimum_wage_difference,
    calculate_pension_difference,
    calculate_total_missing,
)
from src.calculator.statistics import (
    ComplianceMetrics,
    TrendAnalysis,
    ViolationStatistics,
    analyze_trends,
    calculate_compliance_metrics,
    calculate_statistics,
)

logger = get_logger("calculator.missing_amount_calculator")


class MissingAmountCalculator:
    """
    Calculator for determining missing payment amounts from payslips.

    This class orchestrates the full pipeline:
    1. Parse payslips from files
    2. Validate against labor laws
    3. Calculate missing amounts
    4. Aggregate results
    5. Generate statistics
    """

    def __init__(self):
        """Initialize the calculator."""
        self._aggregator = ResultAggregator()
        self._analyses: list[PayslipAnalysis] = []

    def add_payslip(self, payslip: Payslip) -> PayslipAnalysis:
        """
        Add a payslip and calculate missing amounts.

        Args:
            payslip: Parsed Payslip object

        Returns:
            PayslipAnalysis with violations and missing amounts
        """
        # Validate the payslip
        analysis = validate_payslip(payslip)

        # Add to aggregator
        self._aggregator.add_analysis(analysis)
        self._analyses.append(analysis)

        logger.info(
            f"Added payslip {payslip.payslip_date}: "
            f"{len(analysis.violations)} violations, "
            f"₪{analysis.total_missing} missing"
        )

        return analysis

    def add_payslip_file(self, file_path: Path) -> PayslipAnalysis:
        """
        Add a payslip from file (OCR + parse + validate).

        Args:
            file_path: Path to payslip image or PDF

        Returns:
            PayslipAnalysis with violations and missing amounts
        """
        logger.info(f"Processing payslip file: {file_path}")

        # Parse the payslip
        payslip = parse_payslip(file_path)

        # Add and validate
        return self.add_payslip(payslip)

    def add_multiple_files(self, file_paths: list[Path]) -> list[PayslipAnalysis]:
        """
        Add multiple payslip files.

        Args:
            file_paths: List of paths to payslip files

        Returns:
            List of PayslipAnalysis objects
        """
        analyses = []
        for path in file_paths:
            try:
                analysis = self.add_payslip_file(path)
                analyses.append(analysis)
            except Exception as e:
                logger.error(f"Failed to process {path}: {e}")

        return analyses

    def get_total_missing(self) -> Decimal:
        """Get total missing amount across all payslips."""
        return self._aggregator.get_results().total_missing

    def get_aggregated_results(self) -> AggregatedResults:
        """Get aggregated results with all statistics."""
        return self._aggregator.get_results()

    def get_statistics(self) -> ViolationStatistics:
        """Get detailed violation statistics."""
        return calculate_statistics(self._aggregator.get_results())

    def get_trends(self) -> TrendAnalysis:
        """Get trend analysis over time."""
        return analyze_trends(self._aggregator.get_results())

    def get_compliance_metrics(self) -> ComplianceMetrics:
        """Get compliance-focused metrics."""
        return calculate_compliance_metrics(self._aggregator.get_results())

    def generate_report(self) -> AnalysisReport:
        """
        Generate a complete analysis report.

        Returns:
            AnalysisReport ready for output
        """
        return self._aggregator.to_analysis_report()

    def get_summary(self) -> dict:
        """
        Get a summary dictionary suitable for JSON output.

        Returns:
            Dictionary with summary information
        """
        results = self._aggregator.get_results()
        stats = self.get_statistics()
        metrics = self.get_compliance_metrics()

        return {
            "total_missing": float(results.total_missing),
            "total_payslips": results.total_payslips,
            "compliant_payslips": results.compliant_payslips,
            "non_compliant_payslips": results.non_compliant_payslips,
            "compliance_rate": float(metrics.compliance_rate),
            "risk_level": metrics.risk_level,
            "problem_months": results.problem_months,
            "violation_types": results.violation_types_found,
            "total_violations": stats.total_violations,
            "projected_annual_liability": float(metrics.projected_annual_liability),
            "monthly_details": [
                {
                    "month": month_str,
                    "missing": float(breakdown.total_missing),
                    "violation_count": breakdown.violation_count,
                }
                for month_str, breakdown in results.by_month.items()
            ],
        }

    def reset(self) -> None:
        """Reset the calculator for new analysis."""
        self._aggregator = ResultAggregator()
        self._analyses = []


def calculate_missing_amounts(payslips: list[Payslip]) -> AnalysisReport:
    """
    Convenience function to calculate missing amounts for multiple payslips.

    Args:
        payslips: List of Payslip objects

    Returns:
        AnalysisReport with all results
    """
    calculator = MissingAmountCalculator()
    for payslip in payslips:
        calculator.add_payslip(payslip)
    return calculator.generate_report()


def calculate_from_files(file_paths: list[Path]) -> AnalysisReport:
    """
    Convenience function to calculate missing amounts from files.

    Args:
        file_paths: List of paths to payslip files

    Returns:
        AnalysisReport with all results
    """
    calculator = MissingAmountCalculator()
    calculator.add_multiple_files(file_paths)
    return calculator.generate_report()
