"""Statistics and analytics for payslip violations."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from src.logging_config import get_logger
from src.models import PayslipAnalysis, ViolationType
from src.calculator.aggregator import AggregatedResults

logger = get_logger("calculator.statistics")


@dataclass
class ViolationStatistics:
    """Statistical analysis of violations."""

    # Counts
    total_violations: int = 0
    unique_violation_types: int = 0

    # Amounts
    total_missing: Decimal = Decimal("0")
    min_single_violation: Optional[Decimal] = None
    max_single_violation: Optional[Decimal] = None
    avg_violation_amount: Optional[Decimal] = None
    median_violation_amount: Optional[Decimal] = None

    # By type breakdown
    violations_by_type: dict[str, int] = None
    amounts_by_type: dict[str, Decimal] = None

    # Most common
    most_common_type: Optional[str] = None
    most_costly_type: Optional[str] = None


def calculate_statistics(results: AggregatedResults) -> ViolationStatistics:
    """
    Calculate detailed statistics from aggregated results.

    Args:
        results: AggregatedResults from aggregation

    Returns:
        ViolationStatistics with detailed analysis
    """
    stats = ViolationStatistics()
    stats.violations_by_type = {}
    stats.amounts_by_type = {}

    all_amounts: list[Decimal] = []

    # Process each violation type summary
    for vtype, summary in results.by_violation_type.items():
        type_name = vtype.value
        stats.violations_by_type[type_name] = summary.occurrence_count
        stats.amounts_by_type[type_name] = summary.total_missing
        stats.total_violations += summary.occurrence_count

        # Track min/max across all types
        if summary.min_amount is not None:
            if stats.min_single_violation is None:
                stats.min_single_violation = summary.min_amount
            else:
                stats.min_single_violation = min(stats.min_single_violation, summary.min_amount)

        if summary.max_amount is not None:
            if stats.max_single_violation is None:
                stats.max_single_violation = summary.max_amount
            else:
                stats.max_single_violation = max(stats.max_single_violation, summary.max_amount)

    stats.unique_violation_types = len(results.by_violation_type)
    stats.total_missing = results.total_missing

    # Calculate average
    if stats.total_violations > 0:
        stats.avg_violation_amount = (stats.total_missing / stats.total_violations).quantize(
            Decimal("0.01")
        )

    # Find most common and most costly types
    if stats.violations_by_type:
        stats.most_common_type = max(stats.violations_by_type, key=stats.violations_by_type.get)
    if stats.amounts_by_type:
        stats.most_costly_type = max(stats.amounts_by_type, key=stats.amounts_by_type.get)

    # Calculate median from all violations
    for analysis in results.payslip_analyses:
        for violation in analysis.violations:
            if violation.missing_amount > 0:
                all_amounts.append(violation.missing_amount)

    if all_amounts:
        sorted_amounts = sorted(all_amounts)
        mid = len(sorted_amounts) // 2
        if len(sorted_amounts) % 2 == 0:
            stats.median_violation_amount = (
                (sorted_amounts[mid - 1] + sorted_amounts[mid]) / 2
            ).quantize(Decimal("0.01"))
        else:
            stats.median_violation_amount = sorted_amounts[mid]

    return stats


@dataclass
class TrendAnalysis:
    """Trend analysis over time."""

    # Monthly trend
    monthly_totals: dict[str, Decimal] = None
    trend_direction: str = "stable"  # "increasing", "decreasing", "stable"

    # Improvement tracking
    best_month: Optional[str] = None
    worst_month: Optional[str] = None
    best_month_amount: Optional[Decimal] = None
    worst_month_amount: Optional[Decimal] = None


def analyze_trends(results: AggregatedResults) -> TrendAnalysis:
    """
    Analyze trends in violations over time.

    Args:
        results: AggregatedResults from aggregation

    Returns:
        TrendAnalysis with trend information
    """
    trend = TrendAnalysis()
    trend.monthly_totals = {}

    if not results.by_month:
        return trend

    # Extract monthly totals
    for month_str, breakdown in results.by_month.items():
        trend.monthly_totals[month_str] = breakdown.total_missing

    # Find best and worst months
    if trend.monthly_totals:
        trend.worst_month = max(trend.monthly_totals, key=trend.monthly_totals.get)
        trend.worst_month_amount = trend.monthly_totals[trend.worst_month]

        # Best is the one with least violations (but still has some)
        non_zero_months = {k: v for k, v in trend.monthly_totals.items() if v > 0}
        if non_zero_months:
            trend.best_month = min(non_zero_months, key=non_zero_months.get)
            trend.best_month_amount = non_zero_months[trend.best_month]

    # Determine trend direction
    if len(results.problem_months) >= 3:
        # Compare first third to last third
        months_sorted = sorted(
            results.by_month.items(),
            key=lambda x: x[1].month
        )

        third = len(months_sorted) // 3
        if third > 0:
            first_third_avg = sum(
                m[1].total_missing for m in months_sorted[:third]
            ) / third
            last_third_avg = sum(
                m[1].total_missing for m in months_sorted[-third:]
            ) / third

            if last_third_avg > first_third_avg * Decimal("1.1"):
                trend.trend_direction = "increasing"
            elif last_third_avg < first_third_avg * Decimal("0.9"):
                trend.trend_direction = "decreasing"

    return trend


@dataclass
class ComplianceMetrics:
    """Compliance-focused metrics."""

    compliance_rate: Decimal = Decimal("100")
    total_payslips: int = 0
    compliant_payslips: int = 0
    non_compliant_payslips: int = 0

    # Risk assessment
    risk_level: str = "low"  # "low", "medium", "high", "critical"
    primary_risk_area: Optional[str] = None

    # Financial impact
    total_liability: Decimal = Decimal("0")
    monthly_average_liability: Decimal = Decimal("0")
    projected_annual_liability: Decimal = Decimal("0")


def calculate_compliance_metrics(results: AggregatedResults) -> ComplianceMetrics:
    """
    Calculate compliance-focused metrics.

    Args:
        results: AggregatedResults from aggregation

    Returns:
        ComplianceMetrics with compliance analysis
    """
    metrics = ComplianceMetrics()

    metrics.total_payslips = results.total_payslips
    metrics.compliant_payslips = results.compliant_payslips
    metrics.non_compliant_payslips = results.non_compliant_payslips
    metrics.compliance_rate = results.compliance_rate
    metrics.total_liability = results.total_missing

    # Calculate monthly average and projection
    if results.total_payslips > 0:
        metrics.monthly_average_liability = (
            results.total_missing / results.total_payslips
        ).quantize(Decimal("0.01"))
        metrics.projected_annual_liability = (
            metrics.monthly_average_liability * 12
        ).quantize(Decimal("0.01"))

    # Determine risk level
    if results.compliance_rate >= Decimal("95"):
        metrics.risk_level = "low"
    elif results.compliance_rate >= Decimal("80"):
        metrics.risk_level = "medium"
    elif results.compliance_rate >= Decimal("50"):
        metrics.risk_level = "high"
    else:
        metrics.risk_level = "critical"

    # Identify primary risk area
    if results.by_violation_type:
        # Find the type with highest total missing amount
        max_type = max(
            results.by_violation_type.items(),
            key=lambda x: x[1].total_missing
        )
        metrics.primary_risk_area = max_type[0].value

    return metrics
