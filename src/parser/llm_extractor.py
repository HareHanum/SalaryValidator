"""LLM-based payslip field extraction using Claude."""

import json
import os
from dataclasses import asdict
from decimal import Decimal
from typing import Optional

from anthropic import Anthropic

from src.logging_config import get_logger
from src.parser.field_extractor import ExtractedFields

logger = get_logger("parser.llm_extractor")

# Extraction prompt for Claude
EXTRACTION_PROMPT = """You are an expert at extracting structured data from Israeli payslips (תלושי שכר).

Analyze the following OCR text from an Israeli payslip and extract the relevant fields.
The text may have OCR errors, spaces in the middle of words, or be in mixed Hebrew/English.

Extract the following fields (use null if not found or unclear):

1. **payslip_date**: The month/year of the payslip (format: "YYYY-MM-01")
2. **employee_name**: Employee's name
3. **employer_name**: Employer/company name
4. **base_salary**: Base monthly salary (שכר בסיס/משכורת)
5. **gross_salary**: Total gross salary (שכר ברוטו/סה"כ תשלומים)
6. **net_salary**: Net salary to be paid (שכר נטו/לתשלום)
7. **hours_worked**: Total hours worked (שעות עבודה)
8. **hourly_rate**: Hourly wage rate (שכר שעתי)
9. **overtime_hours**: Overtime hours (שעות נוספות)
10. **overtime_pay**: Overtime payment (תשלום שעות נוספות/ש"נ גלובלי)
11. **income_tax**: Income tax deducted (מס הכנסה)
12. **national_insurance**: National insurance deducted (ביטוח לאומי/ב. לאומי)
13. **health_insurance**: Health insurance deducted (מס בריאות/דמי בריאות)
14. **pension_employee**: Employee pension contribution (פנסיה עובד - look for pension provider names like אלטשולר, מגדל, מנורה, הראל, כלל, פניקס followed by פנסיה)
15. **pension_employer**: Employer pension contribution (פנסיה מעביד/גמל מעסיק)
16. **provident_fund**: Provident fund/Keren Hishtalmut (קרן השתלמות/קרה"ש)

IMPORTANT NOTES:
- Look for the MONTHLY deduction values, not cumulative (מצטבר) values
- Deductions section usually appears near the end with labels like "ניכויי חובה"
- Values are in Israeli Shekels (₪)
- Return numbers as plain numbers without currency symbols or commas
- For dates, look for patterns like "תלוש שכר לחודש MM/YYYY" or "חודש MM/YYYY"

Return ONLY a valid JSON object with these exact field names. Example:
{
  "payslip_date": "2024-01-01",
  "employee_name": "ישראל ישראלי",
  "employer_name": "חברה בע\"מ",
  "base_salary": 10000.00,
  "gross_salary": 12000.00,
  "net_salary": 9500.00,
  "hours_worked": 182,
  "hourly_rate": 54.95,
  "overtime_hours": 10,
  "overtime_pay": 500.00,
  "income_tax": 1200.00,
  "national_insurance": 400.00,
  "health_insurance": 300.00,
  "pension_employee": 600.00,
  "pension_employer": 650.00,
  "provident_fund": 250.00
}

OCR TEXT:
"""


class LLMExtractor:
    """Extract payslip fields using Claude LLM."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the LLM extractor.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client: Optional[Anthropic] = None

    @property
    def client(self) -> Anthropic:
        """Get or create Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                    "or pass api_key to LLMExtractor."
                )
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        """Check if LLM extraction is available (API key configured)."""
        return bool(self.api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def extract_fields(self, ocr_text: str) -> ExtractedFields:
        """
        Extract payslip fields from OCR text using Claude.

        Args:
            ocr_text: Raw OCR text from payslip

        Returns:
            ExtractedFields with populated values
        """
        logger.info("Extracting fields using LLM")

        # Call Claude API
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT + ocr_text
                }
            ]
        )

        # Parse response
        response_text = message.content[0].text
        logger.debug(f"LLM response: {response_text}")

        # Extract JSON from response
        try:
            # Try to parse as JSON directly
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.error(f"Failed to parse LLM response as JSON: {response_text}")
                return ExtractedFields()

        # Convert to ExtractedFields
        fields = ExtractedFields()

        # Map JSON fields to ExtractedFields
        field_mapping = {
            "base_salary": "base_salary",
            "gross_salary": "gross_salary",
            "net_salary": "net_salary",
            "hours_worked": "hours_worked",
            "hourly_rate": "hourly_rate",
            "overtime_hours": "overtime_hours",
            "overtime_pay": "overtime_pay",
            "income_tax": "income_tax",
            "national_insurance": "national_insurance",
            "health_insurance": "health_insurance",
            "pension_employee": "pension_employee",
            "pension_employer": "pension_employer",
            "provident_fund": "provident_fund",
            "employee_name": "employee_name",
            "employer_name": "employer_name",
        }

        for json_field, attr_name in field_mapping.items():
            value = data.get(json_field)
            if value is not None:
                # Convert numeric fields to Decimal
                if attr_name not in ["employee_name", "employer_name", "employee_id"]:
                    try:
                        value = Decimal(str(value))
                    except (ValueError, TypeError):
                        continue
                setattr(fields, attr_name, value)
                fields.raw_extractions[f"{attr_name}_llm"] = data.get(json_field)

        # Store the payslip date separately (will be parsed by the main parser)
        if data.get("payslip_date"):
            fields.raw_extractions["payslip_date_llm"] = data["payslip_date"]

        logger.info(
            f"LLM extracted - gross: {fields.gross_salary}, net: {fields.net_salary}, "
            f"base: {fields.base_salary}, tax: {fields.income_tax}"
        )

        return fields


def extract_with_llm(ocr_text: str, api_key: Optional[str] = None) -> ExtractedFields:
    """
    Convenience function to extract fields using LLM.

    Args:
        ocr_text: Raw OCR text from payslip
        api_key: Optional Anthropic API key

    Returns:
        ExtractedFields with populated values
    """
    extractor = LLMExtractor(api_key=api_key)
    return extractor.extract_fields(ocr_text)
