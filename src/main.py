"""Main entry point for SalaryValidator CLI."""

import sys
from pathlib import Path
from typing import Optional

import click

from src import __version__
from src.logging_config import setup_logging
from src.agent import SalaryValidatorAgent, AgentResult
from src.reporter import OutputFormat
from src.reporter.formatters import format_currency, format_percentage


def print_summary(result: AgentResult) -> None:
    """Print a summary of analysis results to console."""
    click.echo("")
    click.echo("=" * 60)
    click.echo("תוצאות ניתוח תלושי שכר")
    click.echo("Salary Validation Results")
    click.echo("=" * 60)
    click.echo("")

    # Processing summary
    click.echo(f"Files processed: {result.successful_count}/{result.total_files}")
    if result.failed_count > 0:
        click.echo(click.style(f"Failed: {result.failed_count}", fg="red"))

    if result.report is None:
        click.echo("No payslips were successfully processed.")
        return

    click.echo("")
    click.echo("-" * 40)
    click.echo("Summary / סיכום")
    click.echo("-" * 40)

    # Compliance metrics
    if result.compliance_metrics:
        metrics = result.compliance_metrics
        click.echo(f"Compliance Rate: {format_percentage(metrics.compliance_rate)}")
        click.echo(f"Risk Level: {metrics.risk_level}")

    click.echo("")
    click.echo(f"Total Payslips: {result.report.total_payslips}")
    click.echo(f"Compliant: {result.report.compliant_payslips}")
    click.echo(
        f"With Violations: {result.report.total_payslips - result.report.compliant_payslips}"
    )

    click.echo("")
    total_missing = result.report.total_missing
    if total_missing > 0:
        click.echo(
            click.style(
                f"Total Missing Amount: {format_currency(total_missing)}",
                fg="red",
                bold=True,
            )
        )
        click.echo(f"סה\"כ סכום חסר: {format_currency(total_missing)}")
    else:
        click.echo(click.style("No violations found! ✓", fg="green", bold=True))

    # Problem months
    if result.report.problem_months:
        click.echo("")
        click.echo("Problem Months / חודשים בעייתיים:")
        for month in result.report.problem_months:
            click.echo(f"  • {month}")

    # Violation types
    if result.report.violation_types:
        click.echo("")
        click.echo("Violation Types / סוגי הפרות:")
        for vtype in result.report.violation_types:
            click.echo(f"  • {vtype}")

    click.echo("")
    click.echo("=" * 60)


def print_detailed_results(result: AgentResult) -> None:
    """Print detailed results for each payslip."""
    if result.report is None:
        return

    click.echo("")
    click.echo("Detailed Results / פירוט:")
    click.echo("-" * 40)

    for analysis in result.report.payslip_analyses:
        payslip = analysis.payslip
        month_str = payslip.payslip_date.strftime("%B %Y")

        if analysis.is_compliant:
            status = click.style("✓ Compliant", fg="green")
        else:
            status = click.style(
                f"✗ {len(analysis.violations)} violations", fg="red"
            )

        click.echo(f"\n{month_str}: {status}")
        click.echo(f"  Gross: {format_currency(payslip.gross_salary)}")
        click.echo(f"  Net: {format_currency(payslip.net_salary)}")

        if not analysis.is_compliant:
            click.echo(f"  Missing: {format_currency(analysis.total_missing)}")
            for violation in analysis.violations:
                click.echo(f"    - {violation.description}")


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """
    SalaryValidator - Analyze Israeli payslips for labor law compliance.

    \b
    מערכת לניתוח תלושי שכר ובדיקת עמידה בחוקי העבודה בישראל

    \b
    Examples:
      salary-validator analyze payslip.pdf
      salary-validator analyze *.pdf --output html --save ./reports
      salary-validator analyze payslips/ --all-formats
    """
    pass


@main.command()
@click.argument("files", nargs=-1, type=click.Path())
@click.option(
    "--output",
    "-o",
    type=click.Choice(["json", "text", "html"]),
    default="json",
    help="Output format for reports",
)
@click.option(
    "--save",
    "-s",
    type=click.Path(),
    default=None,
    help="Directory to save report files",
)
@click.option(
    "--all-formats",
    is_flag=True,
    help="Generate reports in all formats (JSON, text, HTML)",
)
@click.option(
    "--detailed",
    "-d",
    is_flag=True,
    help="Show detailed per-payslip results",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Minimal output (only show summary)",
)
@click.option(
    "--json-output",
    is_flag=True,
    help="Output results as JSON to stdout",
)
def analyze(
    files: tuple[str, ...],
    output: str,
    save: Optional[str],
    all_formats: bool,
    detailed: bool,
    verbose: bool,
    quiet: bool,
    json_output: bool,
) -> None:
    """
    Analyze payslip files for labor law violations.

    \b
    FILES can be:
      - Individual PDF or image files
      - Multiple files (payslip1.pdf payslip2.pdf)
      - Glob patterns (*.pdf)
      - A directory containing payslip files

    \b
    Examples:
      salary-validator analyze payslip.pdf
      salary-validator analyze january.pdf february.pdf march.pdf
      salary-validator analyze ./payslips/*.pdf --save ./reports
      salary-validator analyze ./payslips/ --all-formats --detailed
    """
    if verbose:
        setup_logging("DEBUG")
    elif quiet:
        setup_logging("WARNING")
    else:
        setup_logging("INFO")

    # Collect files
    file_paths = []
    for file_arg in files:
        path = Path(file_arg)
        if path.is_dir():
            # Find all PDFs and images in directory
            file_paths.extend(path.glob("*.pdf"))
            file_paths.extend(path.glob("*.png"))
            file_paths.extend(path.glob("*.jpg"))
            file_paths.extend(path.glob("*.jpeg"))
        elif path.exists():
            file_paths.append(path)
        else:
            # Try as glob pattern
            matches = list(Path(".").glob(file_arg))
            if matches:
                file_paths.extend(matches)
            else:
                click.echo(f"Warning: File not found: {file_arg}", err=True)

    if not file_paths:
        click.echo("Error: No valid files provided.", err=True)
        click.echo("Use --help for usage information.", err=True)
        sys.exit(1)

    if not quiet:
        click.echo(f"Analyzing {len(file_paths)} payslip file(s)...")

    # Convert output format
    format_map = {
        "json": OutputFormat.JSON,
        "text": OutputFormat.TEXT,
        "html": OutputFormat.HTML,
    }
    output_format = format_map[output]

    # Run analysis
    agent = SalaryValidatorAgent(verbose=verbose)
    result = agent.analyze_files(
        file_paths,
        output_dir=save,
        output_format=output_format,
        generate_all_formats=all_formats,
    )

    # Output results
    if json_output:
        import json
        summary = agent.get_summary()
        click.echo(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        if not quiet:
            print_summary(result)

            if detailed:
                print_detailed_results(result)

        # Show saved files
        if result.output_files:
            click.echo("\nReports saved:")
            for fmt, path in result.output_files.items():
                click.echo(f"  {fmt.value}: {path}")

    # Exit with error code if there were failures
    if result.failed_count > 0:
        sys.exit(1)


@main.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output directory for reports",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "text", "html", "all"]),
    default="all",
    help="Output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
def batch(
    directory: str,
    output: str,
    format: str,
    verbose: bool,
) -> None:
    """
    Batch process all payslips in a directory.

    Scans DIRECTORY for PDF and image files, analyzes them,
    and saves reports to OUTPUT directory.

    \b
    Example:
      salary-validator batch ./payslips/ --output ./reports/
    """
    if verbose:
        setup_logging("DEBUG")

    directory_path = Path(directory)
    output_path = Path(output)

    # Find all payslip files
    file_paths = []
    for ext in ["*.pdf", "*.png", "*.jpg", "*.jpeg", "*.tiff"]:
        file_paths.extend(directory_path.glob(ext))
        file_paths.extend(directory_path.glob(f"**/{ext}"))  # Recursive

    if not file_paths:
        click.echo(f"No payslip files found in {directory}")
        sys.exit(1)

    click.echo(f"Found {len(file_paths)} payslip files")

    # Determine output format
    generate_all = format == "all"
    format_map = {
        "json": OutputFormat.JSON,
        "text": OutputFormat.TEXT,
        "html": OutputFormat.HTML,
        "all": OutputFormat.JSON,
    }
    output_format = format_map[format]

    # Run analysis
    agent = SalaryValidatorAgent(verbose=verbose)
    result = agent.analyze_files(
        file_paths,
        output_dir=output_path,
        output_format=output_format,
        generate_all_formats=generate_all,
    )

    print_summary(result)

    if result.output_files:
        click.echo("\nReports saved:")
        for fmt, path in result.output_files.items():
            click.echo(f"  {fmt.value}: {path}")


@main.command()
def info() -> None:
    """Show information about the tool and supported features."""
    click.echo(f"""
SalaryValidator v{__version__}
מערכת לניתוח תלושי שכר ובדיקת עמידה בחוקי העבודה בישראל

Supported Input Formats:
  • PDF files
  • Image files (PNG, JPG, JPEG, TIFF)

OCR Providers:
  • Google Cloud Vision (recommended)
  • Amazon Textract
  • Tesseract OCR (offline)

Validation Rules:
  • Minimum wage compliance
  • Hours × rate calculation
  • Pension contribution (6% employee, 6.5% employer)
  • Overtime pay (125%/150%)

Output Formats:
  • JSON (structured data)
  • Plain text (Hebrew)
  • HTML (formatted report with RTL support)

For more information:
  https://github.com/your-repo/salary-validator
""")


@main.command()
def version() -> None:
    """Show version information."""
    click.echo(f"SalaryValidator v{__version__}")


if __name__ == "__main__":
    main()
