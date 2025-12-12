# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SalaryValidator is an agent that analyzes Israeli payslips (PDF or image) to detect labor law violations and calculate missing payments. The system extracts payslip data via OCR, validates against Israeli labor standards, and generates Hebrew-language reports.

## Core Pipeline

1. **OCR Extraction** - Extract text from payslip files (PDF/image) using Google Cloud Vision API, Amazon Textract, or Tesseract OCR
2. **Payslip Parsing** - Extract structured data: date, base salary, hours, hourly wage, overtime/bonuses, deductions (tax, pension, national insurance), net salary
3. **Rule Validation** - Check against Israeli labor laws: minimum wage compliance, hour×rate calculations, mandatory pension contributions
4. **Missing Amount Calculation** - Compute expected vs actual payments and differences per payslip
5. **Hebrew Summary Generation** - Produce user-friendly explanations in Hebrew

## Output Format

The system produces either JSON with `total_missing`, `problem_months`, `reasons`, and `monthly_details` fields, or a human-readable Hebrew report.

## Initial Scope

Focus on three validation checks:
- Minimum wage violations (rate varies by date)
- Basic hour × rate calculation errors
- Pension contribution presence

## Development Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the CLI
salary-validator analyze <payslip_files>

# Run tests
pytest

# Linting and formatting
ruff check src/
black src/

# Type checking
mypy src/
```

## Project Structure

```
src/
  ocr/        # OCR providers (Google Vision, Textract, Tesseract)
  parser/     # Payslip text parsing and field extraction
  validator/  # Labor law validation rules
  calculator/ # Missing amount calculations
  reporter/   # Hebrew report generation
  config.py   # Settings and environment config
  models.py   # Pydantic data models
  main.py     # CLI entry point
```

## Key Models (src/models.py)

- `Payslip` - Parsed payslip data with all fields
- `Violation` - Single labor law violation with amounts
- `PayslipAnalysis` - Per-payslip analysis results
- `AnalysisReport` - Complete multi-payslip report
