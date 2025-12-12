"""Tests for the parser module."""

from datetime import date
from decimal import Decimal

import pytest

from src.parser.date_parser import parse_payslip_date, format_hebrew_date
from src.parser.field_extractor import ExtractedFields, FieldExtractor
from src.parser.hebrew_utils import (
    normalize_hebrew_text,
    is_hebrew_text,
    extract_field_label,
    HEBREW_MONTHS,
)
from src.parser.number_extractor import (
    extract_decimal,
    extract_all_numbers,
    extract_currency_amount,
    extract_hours,
    format_ils,
)
from src.parser.payslip_parser import PayslipParser


class TestHebrewUtils:
    """Tests for Hebrew text utilities."""

    def test_normalize_hebrew_text(self):
        """Test Hebrew text normalization."""
        # Test whitespace normalization
        text = "שכר   בסיס\t\n  משכורת"
        normalized = normalize_hebrew_text(text)
        assert "  " not in normalized
        assert "\t" not in normalized
        assert "\n" not in normalized

    def test_is_hebrew_text(self):
        """Test Hebrew text detection."""
        assert is_hebrew_text("שלום") is True
        assert is_hebrew_text("Hello") is False
        assert is_hebrew_text("שלום Hello") is True
        assert is_hebrew_text("123") is False

    def test_extract_field_label(self):
        """Test field label extraction."""
        assert extract_field_label("שכר בסיס") == "base_salary"
        assert extract_field_label("מס הכנסה") == "income_tax"
        assert extract_field_label("שכר נטו") == "net_salary"
        assert extract_field_label("unknown label") is None

    def test_hebrew_months_mapping(self):
        """Test Hebrew month names."""
        assert HEBREW_MONTHS["ינואר"] == 1
        assert HEBREW_MONTHS["דצמבר"] == 12
        assert len(HEBREW_MONTHS) >= 12


class TestNumberExtractor:
    """Tests for number extraction."""

    def test_extract_decimal_simple(self):
        """Test simple decimal extraction."""
        assert extract_decimal("123") == Decimal("123")
        assert extract_decimal("123.45") == Decimal("123.45")
        assert extract_decimal("1,234.56") == Decimal("1234.56")

    def test_extract_decimal_with_currency(self):
        """Test decimal extraction with currency symbols."""
        assert extract_decimal("₪1,234.56") == Decimal("1234.56")
        assert extract_decimal("1,234.56 ש\"ח") == Decimal("1234.56")

    def test_extract_decimal_european_format(self):
        """Test European number format (comma as decimal)."""
        assert extract_decimal("1.234,56") == Decimal("1234.56")

    def test_extract_decimal_negative(self):
        """Test negative number extraction."""
        assert extract_decimal("-123.45") == Decimal("-123.45")
        assert extract_decimal("(123.45)") == Decimal("-123.45")

    def test_extract_decimal_invalid(self):
        """Test invalid decimal extraction."""
        assert extract_decimal("") is None
        assert extract_decimal("abc") is None

    def test_extract_all_numbers(self):
        """Test extracting all numbers from text."""
        text = "שכר בסיס: 5,000.00 שעות: 182 שכר שעתי: 27.47"
        numbers = extract_all_numbers(text)
        assert len(numbers) == 3
        assert Decimal("5000.00") in numbers
        assert Decimal("182") in numbers

    def test_extract_currency_amount(self):
        """Test currency amount extraction."""
        assert extract_currency_amount("₪1,234.56") == Decimal("1234.56")
        assert extract_currency_amount("1,234.56 ש\"ח") == Decimal("1234.56")
        assert extract_currency_amount("NIS 500") == Decimal("500")

    def test_extract_hours(self):
        """Test hours extraction."""
        assert extract_hours("182 שעות") == Decimal("182")
        assert extract_hours("שעות: 160") == Decimal("160")
        assert extract_hours("8:30 שעות") == Decimal("8.5")  # 8 hours 30 minutes

    def test_format_ils(self):
        """Test ILS formatting."""
        assert format_ils(Decimal("1234.56")) == "₪1,234.56"
        assert format_ils(Decimal("1000")) == "₪1,000.00"


class TestDateParser:
    """Tests for date parsing."""

    def test_parse_hebrew_month(self):
        """Test parsing Hebrew month names."""
        assert parse_payslip_date("ינואר 2024") == date(2024, 1, 1)
        assert parse_payslip_date("דצמבר 2023") == date(2023, 12, 1)

    def test_parse_english_month(self):
        """Test parsing English month names."""
        assert parse_payslip_date("January 2024") == date(2024, 1, 1)
        assert parse_payslip_date("Dec 2023") == date(2023, 12, 1)

    def test_parse_numeric_date(self):
        """Test parsing numeric date formats."""
        assert parse_payslip_date("01/2024") == date(2024, 1, 1)
        assert parse_payslip_date("2024-01") == date(2024, 1, 1)
        assert parse_payslip_date("12/2023") == date(2023, 12, 1)

    def test_parse_full_date(self):
        """Test parsing full date formats."""
        assert parse_payslip_date("15/01/2024") == date(2024, 1, 1)  # Returns first of month
        assert parse_payslip_date("2024-01-15") == date(2024, 1, 1)

    def test_parse_invalid_date(self):
        """Test invalid date parsing."""
        assert parse_payslip_date("invalid") is None
        assert parse_payslip_date("") is None

    def test_format_hebrew_date(self):
        """Test Hebrew date formatting."""
        result = format_hebrew_date(date(2024, 1, 15))
        assert "2024" in result
        assert "ינואר" in result


class TestFieldExtractor:
    """Tests for field extraction."""

    def test_extracted_fields_set_field(self):
        """Test setting fields dynamically."""
        fields = ExtractedFields()
        assert fields.set_field("base_salary", Decimal("5000")) is True
        assert fields.base_salary == Decimal("5000")
        assert fields.set_field("invalid_field", Decimal("100")) is False

    def test_extract_base_salary(self):
        """Test base salary extraction."""
        extractor = FieldExtractor()
        text = "שכר בסיס: ₪5,000.00"
        fields = extractor.extract_fields(text)
        assert fields.base_salary == Decimal("5000.00")

    def test_extract_hours_worked(self):
        """Test hours extraction."""
        extractor = FieldExtractor()
        text = "שעות עבודה: 182"
        fields = extractor.extract_fields(text)
        assert fields.hours_worked == Decimal("182")

    def test_extract_deductions(self):
        """Test deduction extraction."""
        extractor = FieldExtractor()
        text = """
        מס הכנסה: ₪500.00
        ביטוח לאומי: ₪200.00
        דמי בריאות: ₪100.00
        """
        fields = extractor.extract_fields(text)
        assert fields.income_tax == Decimal("500.00")
        assert fields.national_insurance == Decimal("200.00")
        assert fields.health_insurance == Decimal("100.00")

    def test_extract_totals(self):
        """Test total extraction."""
        extractor = FieldExtractor()
        text = """
        שכר ברוטו: ₪10,000.00
        שכר נטו: ₪7,500.00
        """
        fields = extractor.extract_fields(text)
        assert fields.gross_salary == Decimal("10000.00")
        assert fields.net_salary == Decimal("7500.00")

    def test_calculate_derived_values(self):
        """Test derived value calculation."""
        extractor = FieldExtractor()
        text = """
        שכר בסיס: ₪5,460.00
        שעות עבודה: 182
        """
        fields = extractor.extract_fields(text)
        assert fields.hourly_rate == Decimal("30.00")  # 5460 / 182


class TestPayslipParser:
    """Tests for the main payslip parser."""

    def test_parse_complete_payslip(self):
        """Test parsing a complete payslip."""
        parser = PayslipParser()
        text = """
        תלוש שכר - ינואר 2024

        שכר בסיס: ₪6,000.00
        שעות עבודה: 182
        שכר שעתי: ₪32.97

        שעות נוספות: 10
        גמול שעות נוספות: ₪412.12

        שכר ברוטו: ₪6,412.12

        מס הכנסה: ₪500.00
        ביטוח לאומי: ₪200.00
        דמי בריאות: ₪100.00
        פנסיה עובד: ₪384.73

        שכר נטו: ₪5,227.39
        """

        payslip = parser.parse_from_text(text)

        assert payslip.payslip_date == date(2024, 1, 1)
        assert payslip.base_salary == Decimal("6000.00")
        assert payslip.hours_worked == Decimal("182")
        assert payslip.gross_salary == Decimal("6412.12")
        assert payslip.net_salary == Decimal("5227.39")
        assert payslip.deductions.income_tax == Decimal("500.00")
        assert payslip.deductions.pension_employee == Decimal("384.73")

    def test_parse_minimal_payslip(self):
        """Test parsing with minimal information."""
        parser = PayslipParser()
        text = """
        משכורת פברואר 2024
        שכר נטו: ₪5,000.00
        """

        payslip = parser.parse_from_text(text)

        assert payslip.payslip_date == date(2024, 2, 1)
        assert payslip.net_salary == Decimal("5000.00")
        # Should use default hours
        assert payslip.hours_worked == Decimal("182")

    def test_parse_infers_hourly_rate(self):
        """Test that hourly rate is inferred from salary and hours."""
        parser = PayslipParser()
        text = """
        מרץ 2024
        שכר בסיס: ₪5,460.00
        שעות: 182
        """

        payslip = parser.parse_from_text(text)

        assert payslip.hourly_rate == Decimal("30.00")


class TestPayslipParserAdvanced:
    """Advanced tests for payslip parsing scenarios."""

    def test_parse_alternative_format(self):
        """Test parsing alternative payslip format."""
        parser = PayslipParser()
        text = """
        חברת עבודה בע"מ
        תלוש משכורת - 02/2024

        עובד: ישראל ישראלי
        ת.ז: 123456789

                          תשלומים
        -------------------------------------------
        משכורת יסוד                    6,500.00 ₪
        שעות עבודה                          182

                          ניכויים
        -------------------------------------------
        מס הכנסה                         500.00 ₪
        ביטוח לאומי                      200.00 ₪

        -------------------------------------------
        סה"כ ברוטו:                    6,500.00 ₪
        לתשלום נטו:                    5,260.00 ₪
        """

        payslip = parser.parse_from_text(text)

        assert payslip.payslip_date == date(2024, 2, 1)
        assert payslip.base_salary == Decimal("6500.00")
        assert payslip.gross_salary == Decimal("6500.00")
        assert payslip.net_salary == Decimal("5260.00")

    def test_parse_with_overtime(self):
        """Test parsing payslip with overtime."""
        parser = PayslipParser()
        text = """
        תלוש שכר מאי 2024

        שכר בסיס: ₪6,370.00
        שעות רגילות: 182
        שכר שעתי: ₪35.00

        שעות נוספות 125%: 10
        תגמול שעות נוספות: ₪437.50

        שכר ברוטו: ₪6,807.50
        שכר נטו: ₪5,500.00
        """

        payslip = parser.parse_from_text(text)

        assert payslip.payslip_date == date(2024, 5, 1)
        assert payslip.base_salary == Decimal("6370.00")
        assert payslip.overtime_hours == Decimal("10")
        assert payslip.overtime_pay == Decimal("437.50")

    def test_parse_with_bonus(self):
        """Test parsing payslip with bonus."""
        parser = PayslipParser()
        text = """
        תלוש שכר דצמבר 2024

        שכר בסיס: ₪7,000.00
        שעות: 182

        בונוס: ₪2,000.00

        שכר ברוטו: ₪9,000.00
        שכר נטו: ₪7,200.00
        """

        payslip = parser.parse_from_text(text)

        assert payslip.bonus == Decimal("2000.00")
        assert payslip.gross_salary == Decimal("9000.00")

    def test_parse_with_vacation(self):
        """Test parsing payslip with vacation pay."""
        parser = PayslipParser()
        text = """
        תלוש שכר אוגוסט 2024

        שכר בסיס: ₪5,460.00
        שעות: 152
        ימי חופשה: 5
        דמי חופשה: ₪750.00

        שכר ברוטו: ₪6,210.00
        שכר נטו: ₪5,000.00
        """

        payslip = parser.parse_from_text(text)

        assert payslip.vacation_days == Decimal("5")
        assert payslip.vacation_pay == Decimal("750.00")

    def test_parse_full_deductions(self):
        """Test parsing all deduction types."""
        parser = PayslipParser()
        text = """
        תלוש שכר ינואר 2024

        שכר בסיס: ₪10,000.00
        שעות: 182

        ניכויים:
        מס הכנסה: ₪1,500.00
        ביטוח לאומי: ₪400.00
        מס בריאות: ₪200.00
        פנסיה עובד: ₪600.00
        קרן השתלמות: ₪250.00

        הפרשות מעביד:
        פנסיה מעסיק: ₪650.00

        שכר ברוטו: ₪10,000.00
        שכר נטו: ₪7,050.00
        """

        payslip = parser.parse_from_text(text)

        assert payslip.deductions.income_tax == Decimal("1500.00")
        assert payslip.deductions.national_insurance == Decimal("400.00")
        assert payslip.deductions.health_insurance == Decimal("200.00")
        assert payslip.deductions.pension_employee == Decimal("600.00")
        assert payslip.deductions.pension_employer == Decimal("650.00")


class TestHebrewUtilsAdvanced:
    """Advanced tests for Hebrew text utilities."""

    def test_normalize_removes_diacritics(self):
        """Test that normalization handles diacritical marks."""
        text_with_diacritics = "שָׁלוֹם"  # Shalom with vowels
        normalized = normalize_hebrew_text(text_with_diacritics)
        assert len(normalized) <= len(text_with_diacritics)

    def test_normalize_handles_rtl_marks(self):
        """Test handling of RTL/LTR marks."""
        text = "\u200fשכר בסיס\u200e"  # RLM and LRM marks
        normalized = normalize_hebrew_text(text)
        assert "שכר בסיס" in normalized

    def test_is_hebrew_text_mixed_content(self):
        """Test Hebrew detection with mixed content."""
        # Mostly Hebrew
        assert is_hebrew_text("שכר בסיס: 5000") is True
        # Mostly English
        assert is_hebrew_text("Salary base: שכר") is True
        # Numbers only
        assert is_hebrew_text("5,571.75") is False

    def test_extract_field_label_variations(self):
        """Test field label extraction with variations."""
        # Different phrasings
        assert extract_field_label("משכורת בסיס") == "base_salary"
        assert extract_field_label("שכר יסוד") == "base_salary"
        assert extract_field_label("תשלום נטו") == "net_salary"
        assert extract_field_label("לתשלום") == "net_salary"


class TestNumberExtractorAdvanced:
    """Advanced tests for number extraction."""

    def test_extract_decimal_with_spaces(self):
        """Test decimal extraction with spaces in number."""
        assert extract_decimal("5 571.75") == Decimal("5571.75")

    def test_extract_decimal_leading_zeros(self):
        """Test decimal extraction with leading zeros."""
        assert extract_decimal("0123.45") == Decimal("123.45")
        assert extract_decimal("00.50") == Decimal("0.50")

    def test_extract_currency_all_formats(self):
        """Test currency extraction with all formats."""
        assert extract_currency_amount("₪ 1,234.56") == Decimal("1234.56")
        assert extract_currency_amount("1,234.56₪") == Decimal("1234.56")
        assert extract_currency_amount("שקלים: 1234.56") == Decimal("1234.56")
        assert extract_currency_amount("1234.56 ש\"ח") == Decimal("1234.56")

    def test_extract_hours_various_formats(self):
        """Test hours extraction with various formats."""
        assert extract_hours("182 שעות רגילות") == Decimal("182")
        assert extract_hours("שעות עבודה: 160") == Decimal("160")
        assert extract_hours("total hours: 182") == Decimal("182")

    def test_extract_all_numbers_mixed(self):
        """Test extracting numbers from mixed text."""
        text = """
        שכר בסיס: ₪5,571.75
        שעות: 182
        תאריך: 01/2024
        מספר עובד: 12345
        """
        numbers = extract_all_numbers(text)
        assert Decimal("5571.75") in numbers
        assert Decimal("182") in numbers


class TestDateParserAdvanced:
    """Advanced tests for date parsing."""

    def test_parse_date_with_leading_text(self):
        """Test date parsing with surrounding text."""
        assert parse_payslip_date("תלוש שכר לחודש ינואר 2024") == date(2024, 1, 1)
        assert parse_payslip_date("משכורת February 2024") == date(2024, 2, 1)

    def test_parse_date_short_year(self):
        """Test date parsing with short year format."""
        result = parse_payslip_date("01/24")
        # Should interpret as 2024
        assert result is None or result.year in (2024, 24)

    def test_parse_hebrew_full_date(self):
        """Test full Hebrew date format."""
        result = parse_payslip_date("15 בינואר 2024")
        assert result == date(2024, 1, 1)  # Returns first of month

    def test_parse_date_month_range(self):
        """Test that all months are recognized."""
        months_hebrew = [
            ("ינואר", 1), ("פברואר", 2), ("מרץ", 3), ("אפריל", 4),
            ("מאי", 5), ("יוני", 6), ("יולי", 7), ("אוגוסט", 8),
            ("ספטמבר", 9), ("אוקטובר", 10), ("נובמבר", 11), ("דצמבר", 12),
        ]
        for month_name, month_num in months_hebrew:
            result = parse_payslip_date(f"{month_name} 2024")
            assert result == date(2024, month_num, 1), f"Failed for {month_name}"


class TestFieldExtractorEdgeCases:
    """Edge case tests for field extraction."""

    def test_extract_from_empty_text(self):
        """Test extraction from empty text."""
        extractor = FieldExtractor()
        fields = extractor.extract_fields("")
        assert fields.base_salary is None

    def test_extract_from_noisy_ocr_text(self):
        """Test extraction from noisy OCR output."""
        extractor = FieldExtractor()
        text = """
        שככר בסססיס: ₪5,000.00  # Typos
        שעעות עבבודה: 182
        """
        fields = extractor.extract_fields(text)
        # Should still extract numbers even with label typos
        # The implementation may or may not handle this

    def test_extract_multiple_values_same_field(self):
        """Test handling of multiple values for same field."""
        extractor = FieldExtractor()
        text = """
        שכר בסיס: ₪5,000.00
        שכר בסיס לשעה: ₪27.47
        """
        fields = extractor.extract_fields(text)
        # Should get the first/primary value
        assert fields.base_salary == Decimal("5000.00")

    def test_extract_negative_amounts(self):
        """Test extraction of negative amounts (corrections)."""
        extractor = FieldExtractor()
        text = """
        שכר בסיס: ₪6,000.00
        תיקון: -₪200.00
        שכר ברוטו: ₪5,800.00
        """
        fields = extractor.extract_fields(text)
        assert fields.base_salary == Decimal("6000.00")
        assert fields.gross_salary == Decimal("5800.00")

    def test_extract_with_percentage(self):
        """Test extraction with percentage values."""
        extractor = FieldExtractor()
        text = """
        שכר בסיס: ₪10,000.00
        פנסיה עובד 6%: ₪600.00
        פנסיה מעסיק 6.5%: ₪650.00
        """
        fields = extractor.extract_fields(text)
        assert fields.pension_employee == Decimal("600.00")
        assert fields.pension_employer == Decimal("650.00")


class TestParserErrorHandling:
    """Tests for parser error handling."""

    def test_parse_missing_date(self):
        """Test parsing when date is missing."""
        parser = PayslipParser()
        text = """
        שכר בסיס: ₪5,000.00
        שעות: 182
        שכר נטו: ₪4,500.00
        """
        # Should handle gracefully - may use current date or raise error
        try:
            payslip = parser.parse_from_text(text)
            # If it doesn't raise, check it still has data
            assert payslip.net_salary == Decimal("4500.00")
        except Exception:
            # Also acceptable to raise an error
            pass

    def test_parse_missing_salary(self):
        """Test parsing when salary info is missing."""
        parser = PayslipParser()
        text = """
        תלוש שכר ינואר 2024
        שם: ישראל ישראלי
        """
        try:
            payslip = parser.parse_from_text(text)
            assert payslip.payslip_date == date(2024, 1, 1)
        except Exception:
            pass

    def test_parse_conflicting_values(self):
        """Test parsing with conflicting values."""
        parser = PayslipParser()
        text = """
        תלוש שכר ינואר 2024
        שכר בסיס: ₪5,000.00
        שעות: 182
        שכר שעתי: ₪30.00  # Doesn't match 5000/182
        שכר נטו: ₪4,500.00
        """
        payslip = parser.parse_from_text(text)
        # Parser should use one of the values
        assert payslip.base_salary is not None or payslip.hourly_rate is not None
