"""Shared test fixtures for SalaryValidator tests."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from src.models import (
    AnalysisReport,
    Deductions,
    Payslip,
    PayslipAnalysis,
    Violation,
    ViolationType,
)
from src.ocr.base import OCRResult


# =============================================================================
# Path Fixtures
# =============================================================================


@pytest.fixture
def test_data_dir() -> Path:
    """Return the test data directory path."""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_payslips_dir(test_data_dir: Path) -> Path:
    """Return the sample payslips directory path."""
    return test_data_dir / "sample_payslips"


# =============================================================================
# Payslip Fixtures
# =============================================================================


@pytest.fixture
def minimal_payslip() -> Payslip:
    """Create a minimal valid payslip."""
    return Payslip(
        payslip_date=date(2024, 1, 1),
        base_salary=Decimal("5571.75"),
        hours_worked=Decimal("182"),
        hourly_rate=Decimal("30.614"),
        gross_salary=Decimal("5571.75"),
        net_salary=Decimal("4571.75"),
        deductions=Deductions(),
    )


@pytest.fixture
def compliant_payslip() -> Payslip:
    """Create a payslip that fully complies with labor laws."""
    base_salary = Decimal("6500")
    return Payslip(
        payslip_date=date(2024, 1, 1),
        base_salary=base_salary,
        hours_worked=Decimal("182"),
        hourly_rate=Decimal("35.71"),
        gross_salary=base_salary,
        net_salary=Decimal("5200"),
        deductions=Deductions(
            income_tax=Decimal("500"),
            national_insurance=Decimal("200"),
            health_insurance=Decimal("150"),
            pension_employee=base_salary * Decimal("0.06"),  # 390
            pension_employer=base_salary * Decimal("0.065"),  # 422.50
        ),
    )


@pytest.fixture
def non_compliant_payslip() -> Payslip:
    """Create a payslip with multiple labor law violations."""
    return Payslip(
        payslip_date=date(2024, 1, 1),
        base_salary=Decimal("4500"),  # Below minimum wage
        hours_worked=Decimal("182"),
        hourly_rate=Decimal("24.73"),  # Below minimum hourly rate
        gross_salary=Decimal("4500"),
        net_salary=Decimal("4200"),
        deductions=Deductions(
            income_tax=Decimal("100"),
            national_insurance=Decimal("100"),
            health_insurance=Decimal("100"),
            pension_employee=Decimal("0"),  # Missing pension
            pension_employer=Decimal("0"),
        ),
    )


@pytest.fixture
def minimum_wage_violation_payslip() -> Payslip:
    """Create a payslip with only minimum wage violation."""
    base_salary = Decimal("5000")
    return Payslip(
        payslip_date=date(2024, 1, 1),
        base_salary=base_salary,
        hours_worked=Decimal("182"),
        hourly_rate=Decimal("27.47"),
        gross_salary=base_salary,
        net_salary=Decimal("4000"),
        deductions=Deductions(
            pension_employee=base_salary * Decimal("0.06"),
            pension_employer=base_salary * Decimal("0.065"),
        ),
    )


@pytest.fixture
def pension_violation_payslip() -> Payslip:
    """Create a payslip with only pension violation."""
    base_salary = Decimal("7000")
    return Payslip(
        payslip_date=date(2024, 1, 1),
        base_salary=base_salary,
        hours_worked=Decimal("182"),
        hourly_rate=Decimal("38.46"),
        gross_salary=base_salary,
        net_salary=Decimal("6500"),
        deductions=Deductions(
            income_tax=Decimal("300"),
            national_insurance=Decimal("100"),
            health_insurance=Decimal("100"),
            pension_employee=Decimal("0"),  # Missing
            pension_employer=Decimal("0"),  # Missing
        ),
    )


@pytest.fixture
def hours_rate_mismatch_payslip() -> Payslip:
    """Create a payslip with hours × rate mismatch."""
    return Payslip(
        payslip_date=date(2024, 1, 1),
        base_salary=Decimal("6000"),  # Should be 6370 for 182×35
        hours_worked=Decimal("182"),
        hourly_rate=Decimal("35.00"),
        gross_salary=Decimal("6000"),
        net_salary=Decimal("4800"),
        deductions=Deductions(
            pension_employee=Decimal("360"),
            pension_employer=Decimal("390"),
        ),
    )


@pytest.fixture
def payslip_with_overtime() -> Payslip:
    """Create a payslip with overtime hours."""
    base_salary = Decimal("6370")
    overtime_pay = Decimal("437.50")  # 10 hours × 35 × 1.25
    return Payslip(
        payslip_date=date(2024, 1, 1),
        base_salary=base_salary,
        hours_worked=Decimal("182"),
        hourly_rate=Decimal("35.00"),
        overtime_hours=Decimal("10"),
        overtime_pay=overtime_pay,
        gross_salary=base_salary + overtime_pay,
        net_salary=Decimal("5400"),
        deductions=Deductions(
            pension_employee=base_salary * Decimal("0.06"),
            pension_employer=base_salary * Decimal("0.065"),
        ),
    )


# =============================================================================
# Violation Fixtures
# =============================================================================


@pytest.fixture
def minimum_wage_violation() -> Violation:
    """Create a minimum wage violation."""
    return Violation(
        violation_type=ViolationType.MINIMUM_WAGE,
        description="Hourly rate below minimum wage",
        description_hebrew="שכר שעתי מתחת למינימום",
        expected_value=Decimal("5571.75"),
        actual_value=Decimal("4500.00"),
        missing_amount=Decimal("1071.75"),
        legal_reference="חוק שכר מינימום, התשמ\"ז-1987",
    )


@pytest.fixture
def pension_violation() -> Violation:
    """Create a pension contribution violation."""
    return Violation(
        violation_type=ViolationType.MISSING_PENSION,
        description="Missing employee pension contribution",
        description_hebrew="חסרה הפרשת עובד לפנסיה",
        expected_value=Decimal("420.00"),
        actual_value=Decimal("0"),
        missing_amount=Decimal("420.00"),
        legal_reference="צו הרחבה לביטוח פנסיוני מקיף",
    )


@pytest.fixture
def hours_rate_violation() -> Violation:
    """Create an hours × rate calculation violation."""
    return Violation(
        violation_type=ViolationType.CALCULATION_ERROR,
        description="Base salary doesn't match hours × rate",
        description_hebrew="השכר הבסיסי לא תואם שעות × תעריף",
        expected_value=Decimal("6370.00"),
        actual_value=Decimal("6000.00"),
        missing_amount=Decimal("370.00"),
    )


# =============================================================================
# Analysis Fixtures
# =============================================================================


@pytest.fixture
def compliant_analysis(compliant_payslip: Payslip) -> PayslipAnalysis:
    """Create an analysis with no violations."""
    analysis = PayslipAnalysis(payslip=compliant_payslip, violations=[])
    analysis.calculate_totals()
    return analysis


@pytest.fixture
def non_compliant_analysis(
    non_compliant_payslip: Payslip,
    minimum_wage_violation: Violation,
    pension_violation: Violation,
) -> PayslipAnalysis:
    """Create an analysis with multiple violations."""
    analysis = PayslipAnalysis(
        payslip=non_compliant_payslip,
        violations=[minimum_wage_violation, pension_violation],
    )
    analysis.calculate_totals()
    return analysis


@pytest.fixture
def sample_report(
    compliant_analysis: PayslipAnalysis,
    non_compliant_analysis: PayslipAnalysis,
) -> AnalysisReport:
    """Create a sample analysis report."""
    report = AnalysisReport(
        payslip_analyses=[compliant_analysis, non_compliant_analysis],
        generated_at=date.today(),
    )
    report.calculate_summary()
    return report


# =============================================================================
# OCR Fixtures
# =============================================================================


@pytest.fixture
def sample_ocr_text() -> str:
    """Return sample OCR text from a payslip."""
    return """
    תלוש שכר לחודש ינואר 2024

    שם העובד: ישראל ישראלי
    ת.ז.: 123456789

    שכר בסיס: 5,571.75 ₪
    שעות עבודה: 182
    שכר שעתי: 30.61 ₪

    שכר ברוטו: 5,571.75 ₪

    ניכויים:
    מס הכנסה: 450.00 ₪
    ביטוח לאומי: 180.00 ₪
    ביטוח בריאות: 120.00 ₪
    פנסיה עובד: 334.31 ₪

    הפרשות מעסיק:
    פנסיה מעסיק: 362.16 ₪

    שכר נטו: 4,487.44 ₪
    """


@pytest.fixture
def sample_ocr_result(sample_ocr_text: str) -> OCRResult:
    """Create a sample OCR result."""
    return OCRResult(
        text=sample_ocr_text,
        confidence=0.95,
        provider="test",
        metadata={"pages": 1},
    )


@pytest.fixture
def mock_ocr_provider(sample_ocr_result: OCRResult):
    """Create a mock OCR provider."""
    mock = MagicMock()
    mock.extract.return_value = sample_ocr_result
    mock.name = "mock_provider"
    return mock


# =============================================================================
# Historical Data Fixtures
# =============================================================================


@pytest.fixture
def historical_payslips() -> list[Payslip]:
    """Create a list of payslips spanning multiple months."""
    payslips = []
    for month in range(1, 13):
        # Alternate between compliant and non-compliant
        if month % 3 == 0:
            # Non-compliant month
            payslip = Payslip(
                payslip_date=date(2024, month, 1),
                base_salary=Decimal("5000"),
                hours_worked=Decimal("182"),
                hourly_rate=Decimal("27.47"),
                gross_salary=Decimal("5000"),
                net_salary=Decimal("4200"),
                deductions=Deductions(
                    pension_employee=Decimal("300"),
                    pension_employer=Decimal("325"),
                ),
            )
        else:
            # Compliant month
            payslip = Payslip(
                payslip_date=date(2024, month, 1),
                base_salary=Decimal("6500"),
                hours_worked=Decimal("182"),
                hourly_rate=Decimal("35.71"),
                gross_salary=Decimal("6500"),
                net_salary=Decimal("5200"),
                deductions=Deductions(
                    pension_employee=Decimal("390"),
                    pension_employer=Decimal("422.50"),
                ),
            )
        payslips.append(payslip)
    return payslips


# =============================================================================
# Date Fixtures
# =============================================================================


@pytest.fixture(params=[
    date(2024, 1, 1),
    date(2023, 6, 15),
    date(2022, 12, 31),
    date(2021, 4, 1),
])
def various_dates(request) -> date:
    """Provide various dates for testing."""
    return request.param


@pytest.fixture(params=[
    (2024, Decimal("5571.75")),  # Current minimum
    (2023, Decimal("5571.75")),
    (2022, Decimal("5300.00")),
    (2021, Decimal("5300.00")),
    (2020, Decimal("5300.00")),
    (2018, Decimal("5300.00")),
    (2017, Decimal("5000.00")),
])
def minimum_wage_by_year(request) -> tuple[int, Decimal]:
    """Provide minimum wage values by year."""
    return request.param


# =============================================================================
# Temporary File Fixtures
# =============================================================================


@pytest.fixture
def temp_pdf_file(tmp_path: Path) -> Path:
    """Create a temporary PDF file for testing."""
    pdf_path = tmp_path / "test_payslip.pdf"
    # Create minimal PDF content (empty but valid structure)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def temp_image_file(tmp_path: Path) -> Path:
    """Create a temporary image file for testing."""
    img_path = tmp_path / "test_payslip.png"
    # Create minimal PNG (1x1 white pixel)
    png_content = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])
    img_path.write_bytes(png_content)
    return img_path


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


# =============================================================================
# JSON Test Data Fixtures
# =============================================================================


@pytest.fixture
def payslip_json_data() -> dict:
    """Return payslip data as JSON-compatible dict."""
    return {
        "payslip_date": "2024-01-01",
        "base_salary": 5571.75,
        "hours_worked": 182,
        "hourly_rate": 30.614,
        "gross_salary": 5571.75,
        "net_salary": 4571.75,
        "overtime_hours": 0,
        "overtime_pay": 0,
        "weekend_hours": 0,
        "weekend_pay": 0,
        "vacation_days": 0,
        "vacation_pay": 0,
        "bonus": 0,
        "deductions": {
            "income_tax": 450,
            "national_insurance": 180,
            "health_insurance": 120,
            "pension_employee": 334.31,
            "pension_employer": 362.16,
        },
    }
