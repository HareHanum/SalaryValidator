"""Reporter module for generating Hebrew-language analysis reports."""

from src.reporter.formatters import (
    create_separator,
    format_currency,
    format_currency_plain,
    format_date_full_hebrew,
    format_date_hebrew,
    format_date_numeric,
    format_hours,
    format_month_count,
    format_month_year,
    format_number,
    format_payslip_count,
    format_percentage,
    format_violation_count,
)
from src.reporter.html_reporter import HTMLReporter
from src.reporter.json_reporter import JSONReporter, create_json_report
from src.reporter.report_generator import (
    OutputFormat,
    ReportGenerator,
    generate_report_from_calculator,
    save_report_from_calculator,
)
from src.reporter.templates import (
    HEBREW_MONTHS,
    LEGAL_NOTICE,
    RISK_LEVEL_DESCRIPTIONS,
    RISK_LEVEL_HE,
    SECTION_HEADERS,
    VIOLATION_TYPE_NAMES_HE,
    get_recommendation,
    get_risk_level_text,
    get_violation_type_name,
)
from src.reporter.text_reporter import TextReporter

__all__ = [
    # Main generator
    "ReportGenerator",
    "OutputFormat",
    "generate_report_from_calculator",
    "save_report_from_calculator",
    # Individual reporters
    "JSONReporter",
    "TextReporter",
    "HTMLReporter",
    "create_json_report",
    # Formatters
    "format_currency",
    "format_currency_plain",
    "format_number",
    "format_percentage",
    "format_hours",
    "format_date_hebrew",
    "format_date_full_hebrew",
    "format_date_numeric",
    "format_month_year",
    "format_violation_count",
    "format_payslip_count",
    "format_month_count",
    "create_separator",
    # Templates
    "HEBREW_MONTHS",
    "VIOLATION_TYPE_NAMES_HE",
    "RISK_LEVEL_HE",
    "RISK_LEVEL_DESCRIPTIONS",
    "SECTION_HEADERS",
    "LEGAL_NOTICE",
    "get_violation_type_name",
    "get_risk_level_text",
    "get_recommendation",
]
