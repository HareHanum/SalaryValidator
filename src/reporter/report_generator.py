"""Main report generator combining all output formats."""

from enum import Enum
from pathlib import Path
from typing import Optional, Union

from src.logging_config import get_logger
from src.models import AnalysisReport
from src.calculator import (
    AggregatedResults,
    ComplianceMetrics,
    MissingAmountCalculator,
    ViolationStatistics,
)
from src.reporter.html_reporter import HTMLReporter
from src.reporter.json_reporter import JSONReporter
from src.reporter.text_reporter import TextReporter

logger = get_logger("reporter.report_generator")


class OutputFormat(str, Enum):
    """Supported output formats."""

    JSON = "json"
    TEXT = "text"
    HTML = "html"


class ReportGenerator:
    """
    Main report generator supporting multiple output formats.

    This class provides a unified interface for generating reports
    in JSON, plain text, or HTML format.
    """

    def __init__(self):
        """Initialize report generator with all formatters."""
        self.json_reporter = JSONReporter()
        self.text_reporter = TextReporter()
        self.html_reporter = HTMLReporter()

    def generate(
        self,
        report: AnalysisReport,
        format: OutputFormat = OutputFormat.JSON,
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
        include_legal_notice: bool = True,
    ) -> str:
        """
        Generate report in specified format.

        Args:
            report: The AnalysisReport to convert
            format: Output format (json, text, or html)
            results: Optional aggregated results for additional data
            stats: Optional statistics for additional data
            metrics: Optional compliance metrics
            include_legal_notice: Whether to include legal notice (text/html only)

        Returns:
            Formatted report string
        """
        if format == OutputFormat.JSON:
            return self.json_reporter.generate(report, results, stats, metrics)
        elif format == OutputFormat.TEXT:
            return self.text_reporter.generate(
                report, results, stats, metrics, include_legal_notice
            )
        elif format == OutputFormat.HTML:
            return self.html_reporter.generate(
                report, results, stats, metrics, include_legal_notice
            )
        else:
            raise ValueError(f"Unsupported format: {format}")

    def save(
        self,
        report: AnalysisReport,
        output_path: Union[str, Path],
        format: Optional[OutputFormat] = None,
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
        include_legal_notice: bool = True,
    ) -> Path:
        """
        Save report to file.

        Args:
            report: The AnalysisReport to save
            output_path: Path to save the file
            format: Output format (auto-detected from extension if not specified)
            results: Optional aggregated results
            stats: Optional statistics
            metrics: Optional compliance metrics
            include_legal_notice: Whether to include legal notice

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)

        # Auto-detect format from extension if not specified
        if format is None:
            format = self._detect_format(output_path)

        # Generate and save
        if format == OutputFormat.JSON:
            return self.json_reporter.save(
                report, output_path, results, stats, metrics
            )
        elif format == OutputFormat.TEXT:
            return self.text_reporter.save(
                report, output_path, results, stats, metrics, include_legal_notice
            )
        elif format == OutputFormat.HTML:
            return self.html_reporter.save(
                report, output_path, results, stats, metrics, include_legal_notice
            )
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _detect_format(self, path: Path) -> OutputFormat:
        """Detect output format from file extension."""
        suffix = path.suffix.lower()

        if suffix == ".json":
            return OutputFormat.JSON
        elif suffix in [".txt", ".text"]:
            return OutputFormat.TEXT
        elif suffix in [".html", ".htm"]:
            return OutputFormat.HTML
        else:
            # Default to JSON
            logger.warning(f"Unknown extension {suffix}, defaulting to JSON")
            return OutputFormat.JSON

    def generate_all_formats(
        self,
        report: AnalysisReport,
        base_path: Union[str, Path],
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
    ) -> dict[OutputFormat, Path]:
        """
        Generate report in all formats and save to files.

        Args:
            report: The AnalysisReport to save
            base_path: Base path without extension (e.g., "reports/salary_report")
            results: Optional aggregated results
            stats: Optional statistics
            metrics: Optional compliance metrics

        Returns:
            Dictionary mapping format to saved file path
        """
        base_path = Path(base_path)
        saved_files = {}

        # JSON
        json_path = base_path.with_suffix(".json")
        saved_files[OutputFormat.JSON] = self.json_reporter.save(
            report, json_path, results, stats, metrics
        )

        # Text
        text_path = base_path.with_suffix(".txt")
        saved_files[OutputFormat.TEXT] = self.text_reporter.save(
            report, text_path, results, stats, metrics
        )

        # HTML
        html_path = base_path.with_suffix(".html")
        saved_files[OutputFormat.HTML] = self.html_reporter.save(
            report, html_path, results, stats, metrics
        )

        logger.info(f"Generated reports in {len(saved_files)} formats")
        return saved_files


def generate_report_from_calculator(
    calculator: MissingAmountCalculator,
    format: OutputFormat = OutputFormat.JSON,
    include_legal_notice: bool = True,
) -> str:
    """
    Convenience function to generate report from a calculator.

    Args:
        calculator: MissingAmountCalculator with processed payslips
        format: Output format
        include_legal_notice: Whether to include legal notice

    Returns:
        Formatted report string
    """
    report = calculator.generate_report()
    results = calculator.get_aggregated_results()
    stats = calculator.get_statistics()
    metrics = calculator.get_compliance_metrics()

    generator = ReportGenerator()
    return generator.generate(
        report, format, results, stats, metrics, include_legal_notice
    )


def save_report_from_calculator(
    calculator: MissingAmountCalculator,
    output_path: Union[str, Path],
    format: Optional[OutputFormat] = None,
    include_legal_notice: bool = True,
) -> Path:
    """
    Convenience function to save report from a calculator.

    Args:
        calculator: MissingAmountCalculator with processed payslips
        output_path: Path to save the file
        format: Output format (auto-detected if not specified)
        include_legal_notice: Whether to include legal notice

    Returns:
        Path to saved file
    """
    report = calculator.generate_report()
    results = calculator.get_aggregated_results()
    stats = calculator.get_statistics()
    metrics = calculator.get_compliance_metrics()

    generator = ReportGenerator()
    return generator.save(
        report, output_path, format, results, stats, metrics, include_legal_notice
    )
