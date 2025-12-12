"""Aggregation logic for multiple payslip analyses."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger
from src.models import AnalysisReport, PayslipAnalysis, Violation, ViolationType

logger = get_logger("calculator.aggregator")


@dataclass
class ViolationSummary:
    """Summary of a specific violation type across payslips."""

    violation_type: ViolationType
    occurrence_count: int = 0
    total_missing: Decimal = Decimal("0")
    affected_months: list[str] = field(default_factory=list)
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    avg_amount: Optional[Decimal] = None

    def add_violation(self, violation: Violation, month_str: str) -> None:
        """Add a violation to this summary."""
        self.occurrence_count += 1
        self.total_missing += violation.missing_amount

        if month_str not in self.affected_months:
            self.affected_months.append(month_str)

        # Track min/max
        if self.min_amount is None or violation.missing_amount < self.min_amount:
            self.min_amount = violation.missing_amount
        if self.max_amount is None or violation.missing_amount > self.max_amount:
            self.max_amount = violation.missing_amount

        # Recalculate average
        self.avg_amount = (self.total_missing / self.occurrence_count).quantize(Decimal("0.01"))


@dataclass
class MonthlyBreakdown:
    """Breakdown of violations for a single month."""

    month: date
    month_str: str
    violations: list[Violation] = field(default_factory=list)
    total_missing: Decimal = Decimal("0")
    violation_count: int = 0

    def add_violation(self, violation: Violation) -> None:
        """Add a violation to this month."""
        self.violations.append(violation)
        self.total_missing += violation.missing_amount
        self.violation_count += 1


@dataclass
class AggregatedResults:
    """Aggregated results across multiple payslips."""

    # Overall totals
    total_missing: Decimal = Decimal("0")
    total_payslips: int = 0
    compliant_payslips: int = 0
    non_compliant_payslips: int = 0

    # Violation breakdowns
    by_violation_type: dict[ViolationType, ViolationSummary] = field(default_factory=dict)
    by_month: dict[str, MonthlyBreakdown] = field(default_factory=dict)

    # Lists for quick access
    problem_months: list[str] = field(default_factory=list)
    violation_types_found: list[str] = field(default_factory=list)

    # Individual analyses
    payslip_analyses: list[PayslipAnalysis] = field(default_factory=list)

    @property
    def compliance_rate(self) -> Decimal:
        """Calculate compliance rate as percentage."""
        if self.total_payslips == 0:
            return Decimal("100")
        return (Decimal(self.compliant_payslips) / Decimal(self.total_payslips) * 100).quantize(
            Decimal("0.1")
        )

    @property
    def average_missing_per_month(self) -> Decimal:
        """Calculate average missing amount per non-compliant payslip."""
        if self.non_compliant_payslips == 0:
            return Decimal("0")
        return (self.total_missing / self.non_compliant_payslips).quantize(Decimal("0.01"))


class ResultAggregator:
    """Aggregates validation results across multiple payslips."""

    def __init__(self):
        """Initialize the aggregator."""
        self._results = AggregatedResults()

    def add_analysis(self, analysis: PayslipAnalysis) -> None:
        """
        Add a payslip analysis to the aggregation.

        Args:
            analysis: The PayslipAnalysis to add
        """
        self._results.total_payslips += 1
        self._results.payslip_analyses.append(analysis)

        if analysis.is_compliant:
            self._results.compliant_payslips += 1
        else:
            self._results.non_compliant_payslips += 1
            self._results.total_missing += analysis.total_missing

            # Process violations
            month_str = analysis.payslip.payslip_date.strftime("%B %Y")

            # Ensure month entry exists
            if month_str not in self._results.by_month:
                self._results.by_month[month_str] = MonthlyBreakdown(
                    month=analysis.payslip.payslip_date,
                    month_str=month_str,
                )
                self._results.problem_months.append(month_str)

            for violation in analysis.violations:
                self._add_violation(violation, analysis.payslip.payslip_date, month_str)

    def _add_violation(
        self, violation: Violation, payslip_date: date, month_str: str
    ) -> None:
        """Add a single violation to the aggregation."""
        vtype = violation.violation_type

        # Add to type summary
        if vtype not in self._results.by_violation_type:
            self._results.by_violation_type[vtype] = ViolationSummary(violation_type=vtype)
            self._results.violation_types_found.append(vtype.value)

        self._results.by_violation_type[vtype].add_violation(violation, month_str)

        # Add to monthly breakdown
        self._results.by_month[month_str].add_violation(violation)

    def get_results(self) -> AggregatedResults:
        """Get the aggregated results."""
        # Sort problem months chronologically
        self._results.problem_months.sort(
            key=lambda m: self._results.by_month[m].month
        )
        return self._results

    def to_analysis_report(self) -> AnalysisReport:
        """
        Convert aggregated results to an AnalysisReport.

        Returns:
            AnalysisReport compatible with the models
        """
        results = self.get_results()

        report = AnalysisReport(
            total_missing=results.total_missing,
            problem_months=results.problem_months,
            violation_types=results.violation_types_found,
            payslip_analyses=results.payslip_analyses,
            generated_at=date.today(),
            total_payslips=results.total_payslips,
            compliant_payslips=results.compliant_payslips,
        )

        return report


def aggregate_analyses(analyses: list[PayslipAnalysis]) -> AggregatedResults:
    """
    Convenience function to aggregate multiple analyses.

    Args:
        analyses: List of PayslipAnalysis objects

    Returns:
        AggregatedResults with all statistics
    """
    aggregator = ResultAggregator()
    for analysis in analyses:
        aggregator.add_analysis(analysis)
    return aggregator.get_results()


def create_report(analyses: list[PayslipAnalysis]) -> AnalysisReport:
    """
    Convenience function to create a report from analyses.

    Args:
        analyses: List of PayslipAnalysis objects

    Returns:
        AnalysisReport ready for output
    """
    aggregator = ResultAggregator()
    for analysis in analyses:
        aggregator.add_analysis(analysis)
    return aggregator.to_analysis_report()
