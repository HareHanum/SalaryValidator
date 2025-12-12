"""Parser module for extracting structured data from payslip text."""

from src.parser.date_parser import format_hebrew_date, parse_payslip_date
from src.parser.field_extractor import ExtractedFields, FieldExtractor, extract_payslip_fields
from src.parser.hebrew_utils import (
    FIELD_LABELS,
    HEBREW_MONTHS,
    clean_ocr_artifacts,
    extract_field_label,
    is_hebrew_text,
    normalize_hebrew_text,
)
from src.parser.number_extractor import (
    extract_all_numbers,
    extract_currency_amount,
    extract_decimal,
    extract_hours,
    format_ils,
)
from src.parser.payslip_parser import (
    PayslipParseError,
    PayslipParser,
    parse_payslip,
    parse_payslip_text,
)

__all__ = [
    # Main parser
    "PayslipParser",
    "PayslipParseError",
    "parse_payslip",
    "parse_payslip_text",
    # Field extraction
    "FieldExtractor",
    "ExtractedFields",
    "extract_payslip_fields",
    # Hebrew utilities
    "normalize_hebrew_text",
    "is_hebrew_text",
    "clean_ocr_artifacts",
    "extract_field_label",
    "HEBREW_MONTHS",
    "FIELD_LABELS",
    # Number extraction
    "extract_decimal",
    "extract_all_numbers",
    "extract_currency_amount",
    "extract_hours",
    "format_ils",
    # Date parsing
    "parse_payslip_date",
    "format_hebrew_date",
]
