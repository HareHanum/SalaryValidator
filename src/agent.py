"""Main agent orchestrating the full payslip analysis pipeline."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

from src.logging_config import get_logger, setup_logging
from src.models import AnalysisReport, Payslip, PayslipAnalysis
from src.calculator import (
    AggregatedResults,
    ComplianceMetrics,
    MissingAmountCalculator,
    ViolationStatistics,
)
from src.parser import PayslipParseError, parse_payslip
from src.reporter import OutputFormat, ReportGenerator

logger = get_logger("agent")


@dataclass
class ProcessingResult:
    """Result of processing a single payslip file."""

    file_path: Path
    success: bool
    analysis: Optional[PayslipAnalysis] = None
    error: Optional[str] = None


@dataclass
class AgentResult:
    """Complete result from the agent."""

    # Processing results
    processed_files: list[ProcessingResult] = field(default_factory=list)
    successful_count: int = 0
    failed_count: int = 0

    # Analysis results
    report: Optional[AnalysisReport] = None
    aggregated_results: Optional[AggregatedResults] = None
    statistics: Optional[ViolationStatistics] = None
    compliance_metrics: Optional[ComplianceMetrics] = None

    # Output
    output_files: dict[OutputFormat, Path] = field(default_factory=dict)

    @property
    def total_files(self) -> int:
        return len(self.processed_files)

    @property
    def success_rate(self) -> float:
        if self.total_files == 0:
            return 0.0
        return self.successful_count / self.total_files * 100


class SalaryValidatorAgent:
    """
    Main agent for analyzing Israeli payslips.

    This agent orchestrates the complete pipeline:
    1. OCR extraction from files
    2. Parsing payslip data
    3. Validating against labor laws
    4. Calculating missing amounts
    5. Generating reports

    Example:
        agent = SalaryValidatorAgent()
        result = agent.analyze_files([
            Path("payslip_jan.pdf"),
            Path("payslip_feb.pdf"),
        ])
        print(f"Total missing: ₪{result.report.total_missing}")
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the agent.

        Args:
            verbose: Enable verbose logging
        """
        if verbose:
            setup_logging("DEBUG")

        self._calculator = MissingAmountCalculator()
        self._report_generator = ReportGenerator()

    def analyze_files(
        self,
        file_paths: list[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
        output_format: OutputFormat = OutputFormat.JSON,
        generate_all_formats: bool = False,
    ) -> AgentResult:
        """
        Analyze multiple payslip files.

        Args:
            file_paths: List of paths to payslip files (PDF or images)
            output_dir: Optional directory to save reports
            output_format: Output format for reports
            generate_all_formats: Generate reports in all formats

        Returns:
            AgentResult with all analysis data
        """
        result = AgentResult()

        logger.info(f"Starting analysis of {len(file_paths)} files")

        # Process each file
        for file_path in file_paths:
            file_path = Path(file_path)
            processing_result = self._process_file(file_path)
            result.processed_files.append(processing_result)

            if processing_result.success:
                result.successful_count += 1
            else:
                result.failed_count += 1

        logger.info(
            f"Processed {result.successful_count}/{result.total_files} files successfully"
        )

        # Generate report and statistics
        if result.successful_count > 0:
            result.report = self._calculator.generate_report()
            result.aggregated_results = self._calculator.get_aggregated_results()
            result.statistics = self._calculator.get_statistics()
            result.compliance_metrics = self._calculator.get_compliance_metrics()

            # Save reports if output directory specified
            if output_dir:
                result.output_files = self._save_reports(
                    output_dir, output_format, generate_all_formats
                )

        return result

    def analyze_single_file(self, file_path: Union[str, Path]) -> ProcessingResult:
        """
        Analyze a single payslip file.

        Args:
            file_path: Path to payslip file

        Returns:
            ProcessingResult for the file
        """
        return self._process_file(Path(file_path))

    def analyze_payslip(self, payslip: Payslip) -> PayslipAnalysis:
        """
        Analyze an already-parsed payslip.

        Args:
            payslip: Parsed Payslip object

        Returns:
            PayslipAnalysis with violations
        """
        return self._calculator.add_payslip(payslip)

    def _process_file(self, file_path: Path) -> ProcessingResult:
        """Process a single payslip file."""
        logger.debug(f"Processing: {file_path}")

        if not file_path.exists():
            return ProcessingResult(
                file_path=file_path,
                success=False,
                error=f"File not found: {file_path}",
            )

        try:
            # Parse the payslip (includes OCR)
            payslip = parse_payslip(file_path)

            # Add to calculator (validates and calculates)
            analysis = self._calculator.add_payslip(payslip)

            return ProcessingResult(
                file_path=file_path,
                success=True,
                analysis=analysis,
            )

        except PayslipParseError as e:
            logger.error(f"Parse error for {file_path}: {e}")
            return ProcessingResult(
                file_path=file_path,
                success=False,
                error=f"Parse error: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error for {file_path}: {e}")
            return ProcessingResult(
                file_path=file_path,
                success=False,
                error=f"Error: {str(e)}",
            )

    def _save_reports(
        self,
        output_dir: Union[str, Path],
        output_format: OutputFormat,
        generate_all: bool,
    ) -> dict[OutputFormat, Path]:
        """Save reports to output directory."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        report = self._calculator.generate_report()
        results = self._calculator.get_aggregated_results()
        stats = self._calculator.get_statistics()
        metrics = self._calculator.get_compliance_metrics()

        saved_files = {}

        if generate_all:
            base_path = output_dir / "salary_report"
            saved_files = self._report_generator.generate_all_formats(
                report, base_path, results, stats, metrics
            )
        else:
            # Determine extension
            ext_map = {
                OutputFormat.JSON: ".json",
                OutputFormat.TEXT: ".txt",
                OutputFormat.HTML: ".html",
            }
            ext = ext_map.get(output_format, ".json")
            output_path = output_dir / f"salary_report{ext}"

            saved_path = self._report_generator.save(
                report, output_path, output_format, results, stats, metrics
            )
            saved_files[output_format] = saved_path

        logger.info(f"Reports saved to: {output_dir}")
        return saved_files

    def get_summary(self) -> dict:
        """Get a summary dictionary of results."""
        return self._calculator.get_summary()

    def reset(self) -> None:
        """Reset the agent for new analysis."""
        self._calculator.reset()


def analyze_payslips(
    file_paths: list[Union[str, Path]],
    output_dir: Optional[Union[str, Path]] = None,
    output_format: OutputFormat = OutputFormat.JSON,
    verbose: bool = False,
) -> AgentResult:
    """
    Convenience function to analyze payslip files.

    Args:
        file_paths: List of paths to payslip files
        output_dir: Optional directory to save reports
        output_format: Output format for reports
        verbose: Enable verbose logging

    Returns:
        AgentResult with all analysis data
    """
    agent = SalaryValidatorAgent(verbose=verbose)
    return agent.analyze_files(file_paths, output_dir, output_format)
