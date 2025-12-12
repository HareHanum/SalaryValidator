# SalaryValidator Implementation Plan

## Phase 1: Project Setup & Infrastructure

### 1.1 Project Initialization
- Initialize Python project with `pyproject.toml` or `requirements.txt`
- Set up project structure:
  ```
  src/
    ocr/
    parser/
    validator/
    calculator/
    reporter/
  tests/
  data/
    sample_payslips/
    labor_laws/
  ```
- Configure linting (ruff/flake8) and formatting (black)
- Set up pytest for testing

### 1.2 Configuration Management
- Create config module for API keys and settings
- Environment variable handling (.env support)
- Logging configuration

### 1.3 Data Models
- Define Pydantic models for:
  - `Payslip` (parsed payslip data)
  - `ValidationResult` (rule violation details)
  - `AnalysisReport` (final output)

---

## Phase 2: OCR Module

### 2.1 OCR Interface
- Create abstract base class `OCRProvider`
- Define common interface: `extract_text(file_path) -> str`

### 2.2 OCR Implementations
- **Google Cloud Vision** adapter (primary)
- **Amazon Textract** adapter (alternative)
- **Tesseract OCR** adapter (offline fallback)

### 2.3 File Handling
- PDF to image conversion (pdf2image/PyMuPDF)
- Image preprocessing for better OCR accuracy
- Multi-page document support

### 2.4 OCR Testing
- Unit tests with sample payslip images
- Accuracy benchmarking between providers

---

## Phase 3: Payslip Parser

### 3.1 Text Analysis
- Hebrew text normalization
- Number extraction (handle Hebrew numerals if present)
- Date parsing for Hebrew date formats

### 3.2 Field Extraction
- Regex patterns for common payslip formats
- Extract: month/date, base salary, hours worked, hourly rate
- Extract: overtime hours, weekend hours, vacation days, bonuses
- Extract: deductions (tax, pension, national insurance, provident fund)
- Extract: net salary

### 3.3 Payslip Format Detection
- Identify common Israeli payslip templates
- Template-specific parsing strategies
- Fallback generic parser

### 3.4 Parser Testing
- Test with various payslip formats
- Validate extraction accuracy

---

## Phase 4: Israeli Labor Law Rules Engine

### 4.1 Minimum Wage Data
- Historical minimum wage table (by effective date):
  - 2017-2024 minimum wage rates
  - Hourly rate calculations (monthly / 182 hours)
- Data structure for easy updates

### 4.2 Validation Rules
- **Rule: Minimum Wage Compliance**
  - Compare hourly rate to legal minimum for that date
  - Calculate underpayment amount

- **Rule: Hours × Rate Verification**
  - Verify base salary = hours × hourly rate
  - Flag calculation discrepancies

- **Rule: Pension Contribution**
  - Check pension deduction presence
  - Validate minimum contribution rates (employer: 6.5%, employee: 6%)
  - Consider tenure-based requirements

### 4.3 Rule Engine Architecture
- Rule interface: `validate(payslip) -> List[Violation]`
- Rule registry for easy addition of new rules
- Violation severity levels

### 4.4 Future Rule Placeholders
- Overtime calculation (125%/150% rates)
- Weekend/holiday premiums
- Industry-specific extensions (cleaning, security, hospitality)

---

## Phase 5: Missing Amount Calculator

### 5.1 Per-Payslip Calculation
- Calculate expected payment based on hours and legal rates
- Compare to actual net salary
- Compute difference per violation type

### 5.2 Aggregation
- Sum missing amounts across all payslips
- Group by violation type
- Track problem months

### 5.3 Calculation Models
- `PayslipAnalysis` - per payslip results
- `AggregatedAnalysis` - cross-payslip summary

---

## Phase 6: Hebrew Report Generator

### 6.1 Template System
- Hebrew text templates for each violation type
- Number formatting (Israeli conventions)
- Date formatting (Hebrew months optional)

### 6.2 Output Formats
- **JSON output** - structured data with all fields
- **Plain text Hebrew report** - user-friendly summary
- **HTML report** - formatted for web display

### 6.3 Explanation Generation
- Per-violation explanations
- Monthly summaries
- Total summary with actionable next steps

---

## Phase 7: Main Agent & Integration

### 7.1 Agent Orchestration
- Main entry point accepting file list
- Pipeline coordination: OCR → Parse → Validate → Calculate → Report
- Error handling and partial results

### 7.2 CLI Interface
- Command-line tool for local usage
- File path input support
- Output format selection

### 7.3 API Interface (Optional)
- FastAPI/Flask REST endpoint
- File upload handling
- Async processing for multiple files

---

## Phase 8: Testing & Validation

### 8.1 Unit Tests
- OCR module tests (mocked)
- Parser tests with sample text
- Validator tests with known violations
- Calculator tests with expected results

### 8.2 Integration Tests
- End-to-end pipeline tests
- Sample payslip processing

### 8.3 Test Data
- Create anonymized sample payslips
- Cover various violation scenarios
- Include edge cases

---

## Phase 9: Documentation & Deployment

### 9.1 Documentation
- API documentation
- Usage examples
- Labor law references

### 9.2 Deployment
- Docker containerization
- Environment configuration
- CI/CD pipeline (GitHub Actions)

---

## Technology Stack (Recommended)

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| OCR | Google Cloud Vision / Tesseract |
| PDF Processing | PyMuPDF (fitz) |
| Data Models | Pydantic |
| CLI | Click or Typer |
| API (optional) | FastAPI |
| Testing | pytest |
| Linting | ruff |

---

## Priority Order

1. **Phase 1** - Foundation (required first)
2. **Phase 2** - OCR (core input)
3. **Phase 3** - Parser (core processing)
4. **Phase 4** - Validator (core logic)
5. **Phase 5** - Calculator (core output)
6. **Phase 6** - Reporter (user-facing)
7. **Phase 7** - Integration (complete system)
8. **Phase 8** - Testing (quality assurance)
9. **Phase 9** - Documentation & Deployment
