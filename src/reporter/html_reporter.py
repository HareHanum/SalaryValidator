"""HTML report generator with Hebrew RTL support."""

from datetime import date
from io import StringIO
from pathlib import Path
from typing import Optional, Union

from src.logging_config import get_logger
from src.models import AnalysisReport, PayslipAnalysis, Violation
from src.calculator import AggregatedResults, ComplianceMetrics, ViolationStatistics
from src.reporter.formatters import (
    format_currency,
    format_date_full_hebrew,
    format_date_hebrew,
    format_hours,
    format_percentage,
)
from src.reporter.templates import (
    RISK_LEVEL_DESCRIPTIONS,
    RISK_LEVEL_HE,
    get_recommendation,
    get_violation_type_name,
)

logger = get_logger("reporter.html_reporter")

# HTML template with RTL support and modern styling
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>דוח ניתוח תלושי שכר</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 30px;
        }}

        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #3498db;
        }}

        h2 {{
            color: #2980b9;
            margin: 25px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #ecf0f1;
        }}

        h3 {{
            color: #34495e;
            margin: 20px 0 10px 0;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}

        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}

        .summary-card.success {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}

        .summary-card.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}

        .summary-card.danger {{
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }}

        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            display: block;
        }}

        .summary-card .label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        .risk-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            color: white;
        }}

        .risk-low {{ background-color: #27ae60; }}
        .risk-medium {{ background-color: #f39c12; }}
        .risk-high {{ background-color: #e74c3c; }}
        .risk-critical {{ background-color: #8e44ad; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}

        th, td {{
            padding: 12px 15px;
            text-align: right;
            border-bottom: 1px solid #ecf0f1;
        }}

        th {{
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }}

        tr:hover {{
            background-color: #f8f9fa;
        }}

        .violation-card {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}

        .violation-card.compliant {{
            background: #d4edda;
            border-color: #28a745;
        }}

        .violation-type {{
            font-weight: bold;
            color: #856404;
        }}

        .compliant .violation-type {{
            color: #155724;
        }}

        .amount {{
            font-weight: bold;
            color: #c0392b;
        }}

        .amount.positive {{
            color: #27ae60;
        }}

        .month-section {{
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-right: 4px solid #3498db;
        }}

        .recommendations {{
            background: #e8f4fd;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}

        .recommendations li {{
            margin: 10px 0;
            padding-right: 20px;
        }}

        .legal-notice {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin: 30px 0;
            font-size: 0.9em;
            color: #6c757d;
        }}

        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""


class HTMLReporter:
    """Reporter for generating HTML reports with Hebrew RTL support."""

    def generate(
        self,
        report: AnalysisReport,
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
        include_legal_notice: bool = True,
    ) -> str:
        """
        Generate HTML report.

        Args:
            report: The AnalysisReport to convert
            results: Optional aggregated results
            stats: Optional statistics
            metrics: Optional compliance metrics
            include_legal_notice: Whether to include legal notice

        Returns:
            HTML string
        """
        content = StringIO()

        # Title
        content.write("<h1>דוח ניתוח תלושי שכר</h1>\n")

        # Summary cards
        self._write_summary_cards(content, report, metrics)

        # Risk assessment
        if metrics:
            self._write_risk_section(content, metrics)

        # Violation breakdown table
        if results and results.by_violation_type:
            self._write_violation_table(content, results)

        # Monthly details
        self._write_monthly_sections(content, report)

        # Recommendations
        self._write_recommendations(content, report)

        # Legal notice
        if include_legal_notice:
            self._write_legal_notice(content)

        # Footer
        content.write(f"""
        <div class="footer">
            דוח זה נוצר אוטומטית על ידי מערכת SalaryValidator<br>
            תאריך הפקה: {format_date_full_hebrew(date.today())}
        </div>
        """)

        return HTML_TEMPLATE.format(content=content.getvalue())

    def _write_summary_cards(
        self,
        content: StringIO,
        report: AnalysisReport,
        metrics: Optional[ComplianceMetrics],
    ) -> None:
        """Write summary cards section."""
        non_compliant = report.total_payslips - report.compliant_payslips

        content.write('<div class="summary-grid">\n')

        # Total missing card
        card_class = "danger" if report.total_missing > 0 else "success"
        content.write(f'''
        <div class="summary-card {card_class}">
            <span class="value">{format_currency(report.total_missing)}</span>
            <span class="label">סה"כ סכום חסר</span>
        </div>
        ''')

        # Payslips analyzed
        content.write(f'''
        <div class="summary-card">
            <span class="value">{report.total_payslips}</span>
            <span class="label">תלושים שנותחו</span>
        </div>
        ''')

        # Compliant payslips
        content.write(f'''
        <div class="summary-card success">
            <span class="value">{report.compliant_payslips}</span>
            <span class="label">תלושים תקינים</span>
        </div>
        ''')

        # Non-compliant payslips
        if non_compliant > 0:
            content.write(f'''
            <div class="summary-card warning">
                <span class="value">{non_compliant}</span>
                <span class="label">תלושים עם הפרות</span>
            </div>
            ''')

        # Compliance rate
        if metrics:
            content.write(f'''
            <div class="summary-card">
                <span class="value">{format_percentage(metrics.compliance_rate)}</span>
                <span class="label">שיעור תאימות</span>
            </div>
            ''')

        content.write('</div>\n')

    def _write_risk_section(
        self, content: StringIO, metrics: ComplianceMetrics
    ) -> None:
        """Write risk assessment section."""
        risk_name = RISK_LEVEL_HE.get(metrics.risk_level, metrics.risk_level)
        risk_desc = RISK_LEVEL_DESCRIPTIONS.get(metrics.risk_level, "")

        content.write("<h2>הערכת סיכון</h2>\n")
        content.write(f'<p><span class="risk-badge risk-{metrics.risk_level}">{risk_name}</span></p>\n')
        content.write(f"<p>{risk_desc}</p>\n")

        if metrics.primary_risk_area:
            content.write(f"<p><strong>תחום סיכון עיקרי:</strong> {metrics.primary_risk_area}</p>\n")

        content.write(f"<p><strong>חבות שנתית צפויה:</strong> {format_currency(metrics.projected_annual_liability)}</p>\n")

    def _write_violation_table(
        self, content: StringIO, results: AggregatedResults
    ) -> None:
        """Write violation breakdown table."""
        content.write("<h2>פירוט הפרות לפי סוג</h2>\n")
        content.write("""
        <table>
            <thead>
                <tr>
                    <th>סוג הפרה</th>
                    <th>מספר מקרים</th>
                    <th>סה"כ חסר</th>
                    <th>ממוצע למקרה</th>
                </tr>
            </thead>
            <tbody>
        """)

        for vtype, summary in results.by_violation_type.items():
            type_name = get_violation_type_name(vtype)
            avg = format_currency(summary.avg_amount) if summary.avg_amount else "-"

            content.write(f"""
            <tr>
                <td>{type_name}</td>
                <td>{summary.occurrence_count}</td>
                <td class="amount">{format_currency(summary.total_missing)}</td>
                <td>{avg}</td>
            </tr>
            """)

        content.write("</tbody></table>\n")

    def _write_monthly_sections(
        self, content: StringIO, report: AnalysisReport
    ) -> None:
        """Write monthly detail sections."""
        content.write("<h2>פירוט חודשי</h2>\n")

        for analysis in report.payslip_analyses:
            self._write_month_section(content, analysis)

    def _write_month_section(
        self, content: StringIO, analysis: PayslipAnalysis
    ) -> None:
        """Write section for a single month."""
        payslip = analysis.payslip
        month_str = format_date_hebrew(payslip.payslip_date)

        content.write(f'<div class="month-section">\n')
        content.write(f"<h3>{month_str}</h3>\n")

        # Basic salary info
        content.write("<p>")
        content.write(f"<strong>שכר ברוטו:</strong> {format_currency(payslip.gross_salary)} | ")
        content.write(f"<strong>שכר נטו:</strong> {format_currency(payslip.net_salary)} | ")
        content.write(f"<strong>שעות:</strong> {format_hours(payslip.hours_worked)} | ")
        content.write(f"<strong>שכר שעתי:</strong> {format_currency(payslip.hourly_rate)}")
        content.write("</p>\n")

        if analysis.is_compliant:
            content.write('<div class="violation-card compliant">\n')
            content.write('<span class="violation-type">✓ תלוש תקין - לא נמצאו הפרות</span>\n')
            content.write('</div>\n')
        else:
            content.write(f'<p class="amount">סה"כ חסר: {format_currency(analysis.total_missing)}</p>\n')

            for violation in analysis.violations:
                self._write_violation_card(content, violation)

        content.write('</div>\n')

    def _write_violation_card(
        self, content: StringIO, violation: Violation
    ) -> None:
        """Write a violation card."""
        type_name = get_violation_type_name(violation.violation_type)

        content.write('<div class="violation-card">\n')
        content.write(f'<p class="violation-type">{type_name}</p>\n')
        content.write(f"<p>{violation.description_hebrew}</p>\n")
        content.write(f"<p>צפוי: {format_currency(violation.expected_value)} | ")
        content.write(f"בפועל: {format_currency(violation.actual_value)} | ")
        content.write(f'<span class="amount">חסר: {format_currency(violation.missing_amount)}</span></p>\n')

        if violation.legal_reference:
            content.write(f"<p><small>מקור: {violation.legal_reference}</small></p>\n")

        content.write('</div>\n')

    def _write_recommendations(
        self, content: StringIO, report: AnalysisReport
    ) -> None:
        """Write recommendations section."""
        violation_types = set()
        for analysis in report.payslip_analyses:
            for violation in analysis.violations:
                violation_types.add(violation.violation_type)

        if not violation_types:
            return

        content.write("<h2>המלצות</h2>\n")
        content.write('<div class="recommendations">\n')
        content.write("<ul>\n")

        for vtype in violation_types:
            type_name = get_violation_type_name(vtype)
            recommendation = get_recommendation(vtype)
            content.write(f"<li><strong>{type_name}:</strong> {recommendation}</li>\n")

        content.write("</ul>\n")
        content.write('</div>\n')

    def _write_legal_notice(self, content: StringIO) -> None:
        """Write legal notice section."""
        content.write('<div class="legal-notice">\n')
        content.write("<h3>הערה משפטית חשובה</h3>\n")
        content.write("""
        <p>דוח זה נועד לסייע בזיהוי חריגות אפשריות מדיני העבודה בישראל.
        הדוח אינו מהווה ייעוץ משפטי ואינו מחליף התייעצות עם עורך דין.</p>
        <p>במקרה של חשד להפרת זכויות עבודה, מומלץ:</p>
        <ul>
            <li>לפנות למעסיק בכתב לבירור הנושא</li>
            <li>לשמור את כל תלושי השכר והמסמכים הרלוונטיים</li>
            <li>להתייעץ עם עורך דין המתמחה בדיני עבודה</li>
            <li>לשקול פנייה למשרד העבודה או לבית הדין לעבודה</li>
        </ul>
        """)
        content.write('</div>\n')

    def save(
        self,
        report: AnalysisReport,
        output_path: Union[str, Path],
        results: Optional[AggregatedResults] = None,
        stats: Optional[ViolationStatistics] = None,
        metrics: Optional[ComplianceMetrics] = None,
        include_legal_notice: bool = True,
    ) -> Path:
        """
        Save HTML report to file.

        Args:
            report: The AnalysisReport to save
            output_path: Path to save the file
            results: Optional aggregated results
            stats: Optional statistics
            metrics: Optional compliance metrics
            include_legal_notice: Whether to include legal notice

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)

        html = self.generate(report, results, stats, metrics, include_legal_notice)

        output_path.write_text(html, encoding="utf-8")

        logger.info(f"HTML report saved to: {output_path}")
        return output_path
