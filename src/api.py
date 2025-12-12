"""FastAPI REST API for SalaryValidator."""

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src import __version__
from src.agent import SalaryValidatorAgent
from src.models import Deductions, Payslip
from src.reporter import OutputFormat
from src.validator.labor_law_data import get_minimum_wage, get_pension_rates
from src.reporter.pdf_reporter import generate_pdf_report

# Create FastAPI app
app = FastAPI(
    title="SalaryValidator API",
    description="""
    API for analyzing Israeli payslips for labor law compliance.

    מערכת לניתוח תלושי שכר ובדיקת עמידה בחוקי העבודה בישראל
    """,
    version=__version__,
)

# Get the static files directory
STATIC_DIR = Path(__file__).parent / "static"


# Request/Response models
class PayslipInput(BaseModel):
    """Input model for payslip data."""

    payslip_date: date = Field(..., description="Month/year of the payslip")
    base_salary: Decimal = Field(..., description="Base monthly salary")
    hours_worked: Decimal = Field(..., description="Total hours worked")
    hourly_rate: Decimal = Field(..., description="Hourly wage rate")
    gross_salary: Decimal = Field(..., description="Total gross salary")
    net_salary: Decimal = Field(..., description="Net salary paid")

    # Optional fields
    overtime_hours: Decimal = Field(default=Decimal("0"))
    overtime_pay: Decimal = Field(default=Decimal("0"))
    weekend_hours: Decimal = Field(default=Decimal("0"))
    weekend_pay: Decimal = Field(default=Decimal("0"))
    vacation_days: Decimal = Field(default=Decimal("0"))
    vacation_pay: Decimal = Field(default=Decimal("0"))
    bonus: Decimal = Field(default=Decimal("0"))

    # Deductions
    income_tax: Decimal = Field(default=Decimal("0"))
    national_insurance: Decimal = Field(default=Decimal("0"))
    health_insurance: Decimal = Field(default=Decimal("0"))
    pension_employee: Decimal = Field(default=Decimal("0"))
    pension_employer: Decimal = Field(default=Decimal("0"))

    class Config:
        json_schema_extra = {
            "example": {
                "payslip_date": "2024-01-01",
                "base_salary": 5460.00,
                "hours_worked": 182,
                "hourly_rate": 30.00,
                "gross_salary": 5460.00,
                "net_salary": 4500.00,
                "pension_employee": 327.60,
            }
        }


class ViolationResponse(BaseModel):
    """Response model for a violation."""

    type: str
    type_hebrew: str
    description: str
    description_hebrew: str
    expected_value: float
    actual_value: float
    missing_amount: float


class AnalysisResponse(BaseModel):
    """Response model for payslip analysis."""

    month: str
    is_compliant: bool
    total_missing: float
    violation_count: int
    violations: list[ViolationResponse]


class SummaryResponse(BaseModel):
    """Response model for analysis summary."""

    total_missing: float
    total_payslips: int
    compliant_payslips: int
    non_compliant_payslips: int
    compliance_rate: float
    risk_level: str
    problem_months: list[str]
    violation_types: list[str]


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - serves the web UI."""
    html_file = STATIC_DIR / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
    return """
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head>
        <title>SalaryValidator API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #2c3e50; }
            a { color: #3498db; }
        </style>
    </head>
    <body>
        <h1>SalaryValidator API</h1>
        <p>מערכת לניתוח תלושי שכר ובדיקת עמידה בחוקי העבודה בישראל</p>
        <p>API for analyzing Israeli payslips for labor law compliance.</p>
        <ul>
            <li><a href="/docs">API Documentation (Swagger UI)</a></li>
            <li><a href="/redoc">API Documentation (ReDoc)</a></li>
            <li><a href="/health">Health Check</a></li>
        </ul>
    </body>
    </html>
    """


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version=__version__)


@app.post("/analyze/payslip", response_model=AnalysisResponse)
async def analyze_payslip(payslip_input: PayslipInput):
    """
    Analyze a single payslip for labor law violations.

    Accepts payslip data and returns analysis with any violations found.
    """
    # Convert input to Payslip model
    payslip = Payslip(
        payslip_date=payslip_input.payslip_date,
        base_salary=payslip_input.base_salary,
        hours_worked=payslip_input.hours_worked,
        hourly_rate=payslip_input.hourly_rate,
        gross_salary=payslip_input.gross_salary,
        net_salary=payslip_input.net_salary,
        overtime_hours=payslip_input.overtime_hours,
        overtime_pay=payslip_input.overtime_pay,
        weekend_hours=payslip_input.weekend_hours,
        weekend_pay=payslip_input.weekend_pay,
        vacation_days=payslip_input.vacation_days,
        vacation_pay=payslip_input.vacation_pay,
        bonus=payslip_input.bonus,
        deductions=Deductions(
            income_tax=payslip_input.income_tax,
            national_insurance=payslip_input.national_insurance,
            health_insurance=payslip_input.health_insurance,
            pension_employee=payslip_input.pension_employee,
            pension_employer=payslip_input.pension_employer,
        ),
    )

    # Analyze
    agent = SalaryValidatorAgent()
    analysis = agent.analyze_payslip(payslip)

    # Build response
    violations = []
    for v in analysis.violations:
        violations.append(
            ViolationResponse(
                type=v.violation_type.value,
                type_hebrew=v.violation_type.value,  # Would use template lookup
                description=v.description,
                description_hebrew=v.description_hebrew,
                expected_value=float(v.expected_value),
                actual_value=float(v.actual_value),
                missing_amount=float(v.missing_amount),
            )
        )

    return AnalysisResponse(
        month=payslip.payslip_date.strftime("%B %Y"),
        is_compliant=analysis.is_compliant,
        total_missing=float(analysis.total_missing),
        violation_count=len(analysis.violations),
        violations=violations,
    )


@app.post("/analyze/payslips", response_model=SummaryResponse)
async def analyze_multiple_payslips(payslips: list[PayslipInput]):
    """
    Analyze multiple payslips for labor law violations.

    Accepts a list of payslip data and returns aggregated analysis.
    """
    if not payslips:
        raise HTTPException(status_code=400, detail="No payslips provided")

    agent = SalaryValidatorAgent()

    for payslip_input in payslips:
        payslip = Payslip(
            payslip_date=payslip_input.payslip_date,
            base_salary=payslip_input.base_salary,
            hours_worked=payslip_input.hours_worked,
            hourly_rate=payslip_input.hourly_rate,
            gross_salary=payslip_input.gross_salary,
            net_salary=payslip_input.net_salary,
            overtime_hours=payslip_input.overtime_hours,
            overtime_pay=payslip_input.overtime_pay,
            deductions=Deductions(
                income_tax=payslip_input.income_tax,
                national_insurance=payslip_input.national_insurance,
                health_insurance=payslip_input.health_insurance,
                pension_employee=payslip_input.pension_employee,
                pension_employer=payslip_input.pension_employer,
            ),
        )
        agent.analyze_payslip(payslip)

    summary = agent.get_summary()

    return SummaryResponse(
        total_missing=summary["total_missing"],
        total_payslips=summary["total_payslips"],
        compliant_payslips=summary["compliant_payslips"],
        non_compliant_payslips=summary["non_compliant_payslips"],
        compliance_rate=summary["compliance_rate"],
        risk_level=summary["risk_level"],
        problem_months=summary["problem_months"],
        violation_types=summary["violation_types"],
    )


@app.post("/analyze/file")
async def analyze_file(
    file: UploadFile = File(...),
    output_format: str = "json",
):
    """
    Analyze a payslip file (PDF or image).

    Uploads a file, performs OCR, parses, validates, and returns results.
    """
    # Validate file type
    allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}",
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Analyze
        agent = SalaryValidatorAgent()
        result = agent.analyze_files([tmp_path])

        if result.failed_count > 0:
            error_msg = result.processed_files[0].error if result.processed_files else "Unknown error"
            raise HTTPException(status_code=422, detail=f"Failed to process file: {error_msg}")

        # Return results based on format
        summary = agent.get_summary()

        # Enhance with detailed payslip data and validation info
        if result.report and result.report.payslip_analyses:
            payslip_details = []
            checks_performed = []

            for analysis in result.report.payslip_analyses:
                payslip = analysis.payslip
                payslip_date = payslip.payslip_date

                # Get legal requirements for this date
                min_wage = get_minimum_wage(payslip_date)
                pension_rates = get_pension_rates(payslip_date)

                # Build detailed payslip info
                detail = {
                    "month": payslip_date.strftime("%m/%Y"),
                    "month_name": payslip_date.strftime("%B %Y"),
                    "extracted_data": {
                        "gross_salary": float(payslip.gross_salary),
                        "net_salary": float(payslip.net_salary),
                        "base_salary": float(payslip.base_salary),
                        "hours_worked": float(payslip.hours_worked),
                        "hourly_rate": float(payslip.hourly_rate),
                        "overtime_hours": float(payslip.overtime_hours),
                        "overtime_pay": float(payslip.overtime_pay),
                        "pension_employee": float(payslip.deductions.pension_employee),
                        "pension_employer": float(payslip.deductions.pension_employer),
                        "income_tax": float(payslip.deductions.income_tax),
                        "national_insurance": float(payslip.deductions.national_insurance),
                    },
                    "legal_requirements": {
                        "minimum_hourly_wage": float(min_wage.hourly_wage),
                        "minimum_monthly_wage": float(min_wage.monthly_wage),
                        "pension_employee_rate": f"{float(pension_rates.employee_rate) * 100}%",
                        "pension_employer_rate": f"{float(pension_rates.employer_rate) * 100}%",
                        "expected_pension_employee": float(payslip.gross_salary * pension_rates.employee_rate),
                        "expected_pension_employer": float(payslip.gross_salary * pension_rates.employer_rate),
                    },
                    "validation_results": {
                        "is_compliant": analysis.is_compliant,
                        "total_missing": float(analysis.total_missing),
                        "violation_count": len(analysis.violations),
                    },
                    "checks": []
                }

                # Add check results
                hourly_check = {
                    "name": "minimum_wage",
                    "name_hebrew": "שכר מינימום",
                    "passed": float(payslip.hourly_rate) >= float(min_wage.hourly_wage),
                    "actual": float(payslip.hourly_rate),
                    "required": float(min_wage.hourly_wage),
                    "description": f"שכר שעתי ₪{float(payslip.hourly_rate):.2f} {'עומד' if float(payslip.hourly_rate) >= float(min_wage.hourly_wage) else 'לא עומד'} בשכר מינימום ₪{float(min_wage.hourly_wage):.2f}",
                }
                detail["checks"].append(hourly_check)

                # Hours x Rate check
                calculated_base = float(payslip.hours_worked * payslip.hourly_rate)
                hours_check = {
                    "name": "hours_calculation",
                    "name_hebrew": "חישוב שעות × תעריף",
                    "passed": abs(calculated_base - float(payslip.base_salary)) < 1,
                    "actual": float(payslip.base_salary),
                    "calculated": calculated_base,
                    "description": f"שעות ({float(payslip.hours_worked):.1f}) × תעריף (₪{float(payslip.hourly_rate):.2f}) = ₪{calculated_base:.2f}",
                }
                detail["checks"].append(hours_check)

                # Pension check
                expected_pension = float(payslip.gross_salary * pension_rates.employee_rate)
                actual_pension = float(payslip.deductions.pension_employee)
                pension_check = {
                    "name": "pension_contribution",
                    "name_hebrew": "הפרשות פנסיה",
                    "passed": actual_pension >= expected_pension * 0.95,  # 5% tolerance
                    "actual": actual_pension,
                    "required": expected_pension,
                    "description": f"הפרשת עובד ₪{actual_pension:.2f} {'תקינה' if actual_pension >= expected_pension * 0.95 else 'חסרה'} (נדרש: ₪{expected_pension:.2f})",
                }
                detail["checks"].append(pension_check)

                # Add violations if any
                if analysis.violations:
                    detail["violations"] = [
                        {
                            "type": v.violation_type.value,
                            "type_hebrew": v.description_hebrew.split(':')[0] if ':' in v.description_hebrew else v.description_hebrew[:30],
                            "description": v.description,
                            "description_hebrew": v.description_hebrew,
                            "expected": float(v.expected_value),
                            "actual": float(v.actual_value),
                            "missing": float(v.missing_amount),
                        }
                        for v in analysis.violations
                    ]

                payslip_details.append(detail)

            # Build checks summary
            all_checks = ["minimum_wage", "hours_calculation", "pension_contribution"]
            checks_summary = {
                "total_checks_per_payslip": len(all_checks),
                "checks_list": [
                    {"id": "minimum_wage", "name_hebrew": "בדיקת שכר מינימום", "description": "וידוא שהשכר השעתי עומד בשכר המינימום לפי החוק"},
                    {"id": "hours_calculation", "name_hebrew": "חישוב שעות × תעריף", "description": "בדיקת התאמה בין שעות עבודה, תעריף ושכר בסיס"},
                    {"id": "pension_contribution", "name_hebrew": "הפרשות פנסיה", "description": "בדיקת הפרשות חובה לפנסיה (6% עובד, 6.5% מעסיק)"},
                ],
            }

            summary["payslip_details"] = payslip_details
            summary["checks_summary"] = checks_summary
            summary["analysis_info"] = {
                "total_checks_performed": len(payslip_details) * len(all_checks),
                "methodology": "הניתוח מבוסס על חוקי העבודה בישראל, כולל חוק שכר מינימום וצו ההרחבה לפנסיה",
                "data_source": "נתוני השכר חולצו מהתלוש באמצעות OCR ונותחו אוטומטית",
            }

        if output_format == "json":
            return JSONResponse(content=summary)
        else:
            return JSONResponse(content=summary)

    finally:
        # Clean up temp file
        tmp_path.unlink(missing_ok=True)


@app.get("/info")
async def get_info():
    """Get information about the API and supported features."""
    return {
        "name": "SalaryValidator API",
        "version": __version__,
        "description": "API for analyzing Israeli payslips for labor law compliance",
        "supported_formats": {
            "input": ["PDF", "PNG", "JPG", "JPEG", "TIFF"],
            "output": ["JSON", "Text", "HTML", "PDF"],
        },
        "validation_rules": [
            "Minimum wage compliance",
            "Hours × rate calculation",
            "Pension contribution",
            "Overtime pay",
        ],
        "ocr_providers": ["Google Cloud Vision", "Amazon Textract", "Tesseract"],
    }


@app.post("/report/pdf")
async def generate_pdf(data: dict):
    """
    Generate a comprehensive PDF report from analysis data.

    Accepts JSON analysis data and returns a downloadable PDF report.
    """
    try:
        pdf_bytes = generate_pdf_report(data)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=salary_compliance_report.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


# Run with: uvicorn src.api:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
