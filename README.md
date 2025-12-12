

## 🎯 Project Requirement – Payslip Analysis Agent for Employees (Israel)

**Goal:**
Build an agent that receives multiple payslip files (PDF or image), extracts and analyzes their content, identifies errors or missing payments according to Israeli labor laws, and returns a clear summary of how much money is missing and why.

---

### 1. **Input:**

* A list of payslip files (PDF or image).
* Each file represents one monthly payslip for a salaried employee.
* Files may be provided as attachments or from local file paths.

---

### 2. **Step 1 – OCR:**

* Use OCR to extract text from each payslip.
* Preferred tools (based on availability):

  * **Google Cloud Vision API**
  * **Amazon Textract**
  * **Tesseract OCR** (open source fallback)

---

### 3. **Step 2 – Payslip Parsing:**

Extract the following values from each payslip:

* Date / Month
* Base salary
* Number of hours
* Hourly wage (explicit or calculated)
* Extra payments: overtime, weekend, vacation, bonuses
* Deductions: income tax, pension, national insurance, provident fund
* Net salary paid

---

### 4. **Step 3 – Rule-Based Validation Engine:**

Write logical rules to validate against labor standards (hardcode for now):

* Hourly wage must be ≥ legal minimum (by date)
* Required benefits for specific industries (e.g., cleaning, security, hospitality)
* Correct calculation: hours × rate
* Mandatory pension contributions (based on tenure)

Each rule violation should include a clear explanation, e.g.:

> “Paid 29.5 ILS/hour – below minimum wage of 32.5 ILS for this month.”

---

### 5. **Step 4 – Missing Amount Calculation:**

* For each payslip:

  * Calculate what should have been paid
  * Compare to actual payment
  * Compute the difference

* At the end, compute total missing amount across all payslips.

---

### 6. **Step 5 – Natural Language Summary:**

Use a GPT-like model or templated logic to explain to the user what’s wrong in plain Hebrew.

Example explanation:

> “In January 2024, you were paid 29.5 ILS/hour. The legal minimum was 32.5 ILS/hour. You worked 168 hours, so the missing amount is 504 ILS.”

---

### 7. **Final Output:**

Return a JSON object or human-readable report:

```json
{
  "total_missing": 1835,
  "problem_months": ["January 2024", "March 2024"],
  "reasons": [
    "Below minimum wage",
    "No weekend bonus",
    "Missing pension contribution"
  ],
  "monthly_details": [
    { "month": "January 2024", "missing": 504, "explanation": "Wage below minimum" }
  ]
}
```

Or alternatively: return an HTML or plain-text report suitable for users.

---

### ⚙️ Constraints:

* Initial version only needs to check for:

  * Minimum wage violations
  * Basic hour × rate issues
  * Pension contribution presence

* No need to handle full legal frameworks (e.g., collective agreements) yet.

* Final explanation output must be **in Hebrew**.

---
