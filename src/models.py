"""Data models for SalaryValidator."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ViolationType(str, Enum):
    """Types of labor law violations."""

    MINIMUM_WAGE = "minimum_wage"
    HOURS_RATE_MISMATCH = "hours_rate_mismatch"
    MISSING_PENSION = "missing_pension"
    OVERTIME_UNDERPAID = "overtime_underpaid"
    WEEKEND_UNDERPAID = "weekend_underpaid"
    MISSING_VACATION = "missing_vacation"
    NATIONAL_INSURANCE_MISMATCH = "national_insurance_mismatch"
    HEALTH_TAX_MISMATCH = "health_tax_mismatch"
    MISSING_SEVERANCE_FUND = "missing_severance_fund"
    MISSING_RECUPERATION = "missing_recuperation"
    TRAVEL_EXPENSES_MISSING = "travel_expenses_missing"


class Deductions(BaseModel):
    """Deductions from salary."""

    income_tax: Decimal = Field(default=Decimal("0"), description="Income tax deduction")
    national_insurance: Decimal = Field(
        default=Decimal("0"), description="National insurance (Bituach Leumi)"
    )
    health_insurance: Decimal = Field(default=Decimal("0"), description="Health insurance")
    pension_employee: Decimal = Field(
        default=Decimal("0"), description="Employee pension contribution"
    )
    pension_employer: Decimal = Field(
        default=Decimal("0"), description="Employer pension contribution"
    )
    provident_fund: Decimal = Field(default=Decimal("0"), description="Provident fund (Keren Hishtalmut)")
    other: Decimal = Field(default=Decimal("0"), description="Other deductions")

    @property
    def total(self) -> Decimal:
        """Calculate total deductions."""
        return (
            self.income_tax
            + self.national_insurance
            + self.health_insurance
            + self.pension_employee
            + self.other
        )


class Payslip(BaseModel):
    """Parsed payslip data."""

    # Identification
    payslip_date: date = Field(description="Month/year of the payslip")
    employee_name: Optional[str] = Field(default=None, description="Employee name if extracted")
    employer_name: Optional[str] = Field(default=None, description="Employer name if extracted")

    # Base Compensation
    base_salary: Decimal = Field(description="Base monthly salary")
    hours_worked: Decimal = Field(description="Total regular hours worked")
    hourly_rate: Decimal = Field(description="Hourly wage rate")

    # Additional Compensation
    overtime_hours: Decimal = Field(default=Decimal("0"), description="Overtime hours")
    overtime_pay: Decimal = Field(default=Decimal("0"), description="Overtime payment")
    weekend_hours: Decimal = Field(default=Decimal("0"), description="Weekend/holiday hours")
    weekend_pay: Decimal = Field(default=Decimal("0"), description="Weekend/holiday payment")
    vacation_days: Decimal = Field(default=Decimal("0"), description="Vacation days taken")
    vacation_pay: Decimal = Field(default=Decimal("0"), description="Vacation payment")
    recuperation_pay: Decimal = Field(default=Decimal("0"), description="Recuperation pay (דמי הבראה)")
    travel_expenses: Decimal = Field(default=Decimal("0"), description="Travel expenses reimbursement")
    bonus: Decimal = Field(default=Decimal("0"), description="Bonuses")
    other_additions: Decimal = Field(default=Decimal("0"), description="Other additions")

    # Employer contributions (shown on payslip but not deducted)
    severance_fund: Decimal = Field(default=Decimal("0"), description="Employer severance fund contribution")

    # Deductions
    deductions: Deductions = Field(default_factory=Deductions)

    # Totals
    gross_salary: Decimal = Field(description="Total gross salary")
    net_salary: Decimal = Field(description="Net salary paid")

    # Metadata
    source_file: Optional[str] = Field(default=None, description="Source file path")
    raw_text: Optional[str] = Field(default=None, description="Raw OCR text")
    confidence_score: float = Field(default=1.0, description="Parsing confidence 0-1")

    @property
    def calculated_base(self) -> Decimal:
        """Calculate expected base salary from hours and rate."""
        return self.hours_worked * self.hourly_rate


class Violation(BaseModel):
    """A single labor law violation."""

    violation_type: ViolationType = Field(description="Type of violation")
    description: str = Field(description="Human-readable description")
    description_hebrew: str = Field(description="Hebrew description for user")
    expected_value: Decimal = Field(description="What should have been paid")
    actual_value: Decimal = Field(description="What was actually paid")
    missing_amount: Decimal = Field(description="Difference (expected - actual)")
    legal_reference: Optional[str] = Field(default=None, description="Relevant law reference")


class PayslipAnalysis(BaseModel):
    """Analysis results for a single payslip."""

    payslip: Payslip = Field(description="The analyzed payslip")
    violations: list[Violation] = Field(default_factory=list, description="Found violations")
    total_missing: Decimal = Field(default=Decimal("0"), description="Total missing amount")
    is_compliant: bool = Field(default=True, description="Whether payslip is fully compliant")

    def calculate_totals(self) -> None:
        """Calculate total missing amount from violations."""
        self.total_missing = sum(v.missing_amount for v in self.violations)
        self.is_compliant = len(self.violations) == 0


class AnalysisReport(BaseModel):
    """Complete analysis report for multiple payslips."""

    # Summary
    total_missing: Decimal = Field(default=Decimal("0"), description="Total missing across all payslips")
    problem_months: list[str] = Field(default_factory=list, description="Months with violations")
    violation_types: list[str] = Field(default_factory=list, description="Types of violations found")

    # Detailed Results
    payslip_analyses: list[PayslipAnalysis] = Field(
        default_factory=list, description="Per-payslip analysis"
    )

    # Report Metadata
    generated_at: Optional[date] = Field(default=None, description="Report generation date")
    total_payslips: int = Field(default=0, description="Number of payslips analyzed")
    compliant_payslips: int = Field(default=0, description="Number of compliant payslips")

    def calculate_summary(self) -> None:
        """Calculate summary statistics from analyses."""
        self.total_payslips = len(self.payslip_analyses)
        self.compliant_payslips = sum(1 for a in self.payslip_analyses if a.is_compliant)
        self.total_missing = sum(a.total_missing for a in self.payslip_analyses)

        # Collect unique problem months
        problem_months_set: set[str] = set()
        violation_types_set: set[str] = set()

        for analysis in self.payslip_analyses:
            if not analysis.is_compliant:
                month_str = analysis.payslip.payslip_date.strftime("%B %Y")
                problem_months_set.add(month_str)
                for violation in analysis.violations:
                    violation_types_set.add(violation.violation_type.value)

        self.problem_months = sorted(problem_months_set)
        self.violation_types = sorted(violation_types_set)
