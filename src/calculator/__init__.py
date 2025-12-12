"""Calculator module for computing missing payment amounts."""

from src.calculator.aggregator import (
    AggregatedResults,
    MonthlyBreakdown,
    ResultAggregator,
    ViolationSummary,
    aggregate_analyses,
    create_report,
)
from src.calculator.calculations import (
    calculate_expected_base_salary,
    calculate_expected_overtime,
    calculate_expected_pension_contribution,
    calculate_hours_rate_difference,
    calculate_minimum_wage_difference,
    calculate_overtime_difference,
    calculate_pension_difference,
    calculate_total_expected_pay,
    calculate_total_missing,
    categorize_violation,
    get_violation_amount,
)
from src.calculator.missing_amount_calculator import (
    MissingAmountCalculator,
    calculate_from_files,
    calculate_missing_amounts,
)
from src.calculator.statistics import (
    ComplianceMetrics,
    TrendAnalysis,
    ViolationStatistics,
    analyze_trends,
    calculate_compliance_metrics,
    calculate_statistics,
)

__all__ = [
    # Main calculator
    "MissingAmountCalculator",
    "calculate_missing_amounts",
    "calculate_from_files",
    # Aggregation
    "ResultAggregator",
    "AggregatedResults",
    "ViolationSummary",
    "MonthlyBreakdown",
    "aggregate_analyses",
    "create_report",
    # Calculations
    "calculate_expected_base_salary",
    "calculate_minimum_wage_difference",
    "calculate_hours_rate_difference",
    "calculate_expected_overtime",
    "calculate_overtime_difference",
    "calculate_expected_pension_contribution",
    "calculate_pension_difference",
    "calculate_total_expected_pay",
    "calculate_total_missing",
    "get_violation_amount",
    "categorize_violation",
    # Statistics
    "ViolationStatistics",
    "TrendAnalysis",
    "ComplianceMetrics",
    "calculate_statistics",
    "analyze_trends",
    "calculate_compliance_metrics",
]
