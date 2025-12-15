"""Parser module for extracting structured data from payslip text."""

from src.parser.date_parser import format_hebrew_date, parse_payslip_date
from src.parser.field_extractor import ExtractedFields, FieldExtractor, extract_payslip_fields
from src.parser.llm_extractor import LLMExtractor, extract_with_llm
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
    # LLM extraction
    "LLMExtractor",
    "extract_with_llm",
    # Date parsing
    "parse_payslip_date",
    "format_hebrew_date",
]
