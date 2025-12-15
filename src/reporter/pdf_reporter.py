"""PDF Report Generator for SalaryValidator."""

import io
import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Violation type translations
VIOLATION_TYPE_TRANSLATIONS = {
    'en': {
        'missing_pension': 'Pension Contribution Shortage',
        'minimum_wage': 'Minimum Wage Violation',
        'hours_calculation': 'Hours Calculation Error',
        'national_insurance_mismatch': 'National Insurance Discrepancy',
        'health_tax_mismatch': 'Health Tax Discrepancy',
        'overtime_underpaid': 'Overtime Underpayment',
        'employer_pension': 'Employer Pension Shortage',
        'severance_fund': 'Severance Fund Issue',
    },
    'he': {
        'missing_pension': 'חוסר בהפרשת פנסיה',
        'minimum_wage': 'הפרת שכר מינימום',
        'hours_calculation': 'שגיאה בחישוב שעות',
        'national_insurance_mismatch': 'אי התאמה בביטוח לאומי',
        'health_tax_mismatch': 'אי התאמה במס בריאות',
        'overtime_underpaid': 'תשלום חסר בשעות נוספות',
        'employer_pension': 'חוסר בהפרשת מעסיק לפנסיה',
        'severance_fund': 'בעיה בקרן פיצויים',
    }
}

# Report text translations
REPORT_TRANSLATIONS = {
    'en': {
        'title': 'Payslip Compliance Analysis Report',
        'generated_on': 'Generated on',
        'executive_summary': 'Executive Summary',
        'overall_status': 'Overall Status',
        'compliant': 'COMPLIANT',
        'violations_found': 'VIOLATIONS FOUND',
        'key_findings': 'Key Findings',
        'total_payslips': 'Total payslips analyzed',
        'compliant_payslips': 'Compliant payslips',
        'non_compliant_payslips': 'Non-compliant payslips',
        'compliance_rate': 'Overall compliance rate',
        'risk_assessment': 'Risk assessment',
        'total_missing': 'Total missing amount',
        'methodology': 'Analysis Methodology',
        'methodology_intro': 'This analysis was conducted using automated payslip validation technology. The following process was applied to each payslip:',
        'data_extraction': 'Data Extraction',
        'data_extraction_text': 'Payslip data was extracted using Optical Character Recognition (OCR) technology. Key fields extracted include: gross salary, net salary, hours worked, hourly rate, overtime hours and pay, pension contributions, income tax, and national insurance deductions.',
        'validation_checks': 'Validation Checks Performed',
        'check': 'Check',
        'description': 'Description',
        'legal_basis': 'Legal Basis',
        'minimum_wage_check': 'Minimum Wage',
        'minimum_wage_desc': 'Verifies hourly rate meets legal minimum',
        'minimum_wage_law': 'Minimum Wage Law 5747-1987',
        'hours_rate_check': 'Hours × Rate',
        'hours_rate_desc': 'Validates salary calculation accuracy',
        'hours_rate_law': 'Protection of Wages Law 5718-1958',
        'pension_check': 'Pension',
        'pension_desc': 'Checks mandatory pension deductions (6% employee, 6.5% employer)',
        'pension_law': 'Pension Extension Order 2008',
        'legal_framework': 'Legal Framework',
        'legal_framework_text': 'All validations are based on current Israeli labor laws and regulations. Minimum wage rates are date-specific, accounting for historical changes in the legal minimum wage.',
        'analysis_summary': 'Analysis Summary',
        'metric': 'Metric',
        'value': 'Value',
        'total_checks': 'Total Validation Checks Performed',
        'risk_level': 'Risk Level',
        'projected_liability': 'Projected Annual Liability',
        'detailed_analysis': 'Detailed Payslip Analysis',
        'validation_results': 'Validation Results',
        'pass': 'PASS',
        'fail': 'FAIL',
        'hourly_rate_vs_min': 'Hourly rate {actual} vs minimum {required}',
        'hours_calc_desc': 'Hours ({hours}) x Rate = Base salary matches',
        'pension_desc_detail': 'Employee pension {actual} (required: {required})',
        'violations_summary': 'Violations Summary',
        'no_violations': 'No violations were found during the analysis. All payslips are compliant with Israeli labor laws.',
        'types_found': 'Types of violations found',
        'type': 'Type',
        'expected': 'Expected',
        'actual': 'Actual',
        'missing': 'Missing',
        'conclusions': 'Conclusions and Recommendations',
        'conclusion_compliant': 'Based on our comprehensive analysis, all reviewed payslips are in full compliance with Israeli labor laws. No corrective actions are required at this time.',
        'recommendations_compliant': 'Recommendations:\n• Continue maintaining current payroll practices\n• Perform regular audits to ensure ongoing compliance\n• Stay informed about changes to minimum wage and pension regulations',
        'conclusion_violations': 'Our analysis identified compliance issues totaling {amount} in missing payments. The overall compliance rate is {rate}%, with a risk level assessed as {level}.',
        'recommendations_violations': 'Recommendations:\n• Review and rectify identified underpayments promptly\n• Consult with a labor law attorney regarding potential liabilities\n• Implement payroll system checks to prevent future violations\n• Consider voluntary disclosure to reduce potential penalties\n• Document all corrective actions taken',
        'disclaimer': 'Disclaimer: This report is generated automatically based on data extracted from uploaded payslip documents using OCR technology. While every effort is made to ensure accuracy, the analysis should be verified by a qualified professional. This report does not constitute legal advice.',
        'currency': 'NIS ',
        'field': 'Field',
        'extracted_value': 'Extracted Value',
        'legal_requirement': 'Legal Requirement',
        'status': 'Status',
        'gross_salary': 'Gross Salary',
        'net_salary': 'Net Salary',
        'hours_worked': 'Hours Worked',
        'hourly_rate': 'Hourly Rate',
        'pension_employee': 'Pension (Employee)',
        'min_label': 'min',
    },
    'he': {
        'title': 'דוח ניתוח תלושי שכר',
        'generated_on': 'נוצר בתאריך',
        'executive_summary': 'תקציר מנהלים',
        'overall_status': 'סטטוס כללי',
        'compliant': 'תקין',
        'violations_found': 'נמצאו הפרות',
        'key_findings': 'ממצאים עיקריים',
        'total_payslips': 'סה"כ תלושים שנותחו',
        'compliant_payslips': 'תלושים תקינים',
        'non_compliant_payslips': 'תלושים עם הפרות',
        'compliance_rate': 'שיעור התאימות',
        'risk_assessment': 'הערכת סיכון',
        'total_missing': 'סה"כ סכום חסר',
        'methodology': 'מתודולוגיית הניתוח',
        'methodology_intro': 'ניתוח זה בוצע באמצעות טכנולוגיית בדיקת תלושי שכר אוטומטית. התהליך הבא הופעל על כל תלוש:',
        'data_extraction': 'חילוץ נתונים',
        'data_extraction_text': 'נתוני התלוש חולצו באמצעות טכנולוגיית זיהוי תווים אופטי (OCR). שדות מפתח שחולצו כוללים: שכר ברוטו, שכר נטו, שעות עבודה, שכר שעתי, שעות נוספות, הפרשות פנסיה, מס הכנסה וביטוח לאומי.',
        'validation_checks': 'בדיקות שבוצעו',
        'check': 'בדיקה',
        'description': 'תיאור',
        'legal_basis': 'בסיס חוקי',
        'minimum_wage_check': 'שכר מינימום',
        'minimum_wage_desc': 'אימות שהשכר השעתי עומד במינימום החוקי',
        'minimum_wage_law': 'חוק שכר מינימום, תשמ"ז-1987',
        'hours_rate_check': 'שעות × תעריף',
        'hours_rate_desc': 'אימות נכונות חישוב השכר',
        'hours_rate_law': 'חוק הגנת השכר, תשי"ח-1958',
        'pension_check': 'פנסיה',
        'pension_desc': 'בדיקת הפרשות פנסיה חובה (6% עובד, 6.5% מעסיק)',
        'pension_law': 'צו הרחבה לפנסיה 2008',
        'legal_framework': 'מסגרת חוקית',
        'legal_framework_text': 'כל הבדיקות מבוססות על חוקי העבודה הישראליים הנוכחיים. שיעורי שכר המינימום תלויים בתאריך ומתעדכנים בהתאם לשינויים בחוק.',
        'analysis_summary': 'סיכום הניתוח',
        'metric': 'מדד',
        'value': 'ערך',
        'total_checks': 'סה"כ בדיקות שבוצעו',
        'risk_level': 'רמת סיכון',
        'projected_liability': 'חבות שנתית משוערת',
        'detailed_analysis': 'ניתוח מפורט לפי תלוש',
        'validation_results': 'תוצאות הבדיקה',
        'pass': 'עבר',
        'fail': 'נכשל',
        'hourly_rate_vs_min': 'שכר שעתי {actual} מול מינימום {required}',
        'hours_calc_desc': 'שעות ({hours}) × תעריף = שכר בסיס תואם',
        'pension_desc_detail': 'הפרשת עובד לפנסיה {actual} (נדרש: {required})',
        'violations_summary': 'סיכום הפרות',
        'no_violations': 'לא נמצאו הפרות בניתוח. כל התלושים עומדים בחוקי העבודה הישראליים.',
        'types_found': 'סוגי הפרות שנמצאו',
        'type': 'סוג',
        'expected': 'צפוי',
        'actual': 'בפועל',
        'missing': 'חסר',
        'conclusions': 'מסקנות והמלצות',
        'conclusion_compliant': 'על בסיס הניתוח המקיף, כל התלושים שנבדקו עומדים במלואם בחוקי העבודה הישראליים. לא נדרשות פעולות תיקון.',
        'recommendations_compliant': 'המלצות:\n• המשך לשמור על נהלי השכר הנוכחיים\n• בצע ביקורות תקופתיות להבטחת תאימות מתמשכת\n• הישאר מעודכן בשינויים בחוקי שכר מינימום ופנסיה',
        'conclusion_violations': 'הניתוח זיהה בעיות תאימות בסך {amount} בתשלומים חסרים. שיעור התאימות הכולל הוא {rate}%, עם רמת סיכון שהוערכה כ-{level}.',
        'recommendations_violations': 'המלצות:\n• בדוק ותקן את התשלומים החסרים בהקדם\n• התייעץ עם עורך דין לדיני עבודה בנוגע לחבויות אפשריות\n• יישם בקרות במערכת השכר למניעת הפרות עתידיות\n• שקול גילוי מרצון להפחתת קנסות אפשריים\n• תעד את כל פעולות התיקון שננקטו',
        'disclaimer': 'הצהרה: דוח זה נוצר אוטומטית על בסיס נתונים שחולצו מתלושי שכר באמצעות טכנולוגיית OCR. למרות המאמץ להבטיח דיוק, יש לאמת את הניתוח על ידי איש מקצוע מוסמך. דוח זה אינו מהווה ייעוץ משפטי.',
        'currency': 'NIS ',
        'field': 'שדה',
        'extracted_value': 'ערך שחולץ',
        'legal_requirement': 'דרישה חוקית',
        'status': 'סטטוס',
        'gross_salary': 'שכר ברוטו',
        'net_salary': 'שכר נטו',
        'hours_worked': 'שעות עבודה',
        'hourly_rate': 'שכר שעתי',
        'pension_employee': 'פנסיה (עובד)',
        'min_label': 'מינימום',
    }
}


def _register_hebrew_font():
    """Register a Hebrew-supporting font if available."""
    # Try to find and register Arial or other Hebrew-supporting fonts
    font_paths = [
        # Windows fonts
        'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
        # Linux fonts
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        # WSL access to Windows fonts
        '/mnt/c/Windows/Fonts/arial.ttf',
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('HebrewFont', font_path))
                if 'arialbd' in font_path.lower():
                    pdfmetrics.registerFont(TTFont('HebrewFontBold', font_path))
                else:
                    # Try to find bold version
                    bold_path = font_path.replace('arial.ttf', 'arialbd.ttf').replace('Arial.ttf', 'Arialbd.ttf')
                    if os.path.exists(bold_path):
                        pdfmetrics.registerFont(TTFont('HebrewFontBold', bold_path))
                    else:
                        pdfmetrics.registerFont(TTFont('HebrewFontBold', font_path))
                return True
            except Exception:
                continue
    return False


# Try to register Hebrew font at module load
HEBREW_FONT_AVAILABLE = _register_hebrew_font()


class PDFReportGenerator:
    """Generate comprehensive PDF reports for payslip analysis."""

    def __init__(self, language: str = 'en'):
        """Initialize the PDF generator with styles."""
        self.language = language if language in ['en', 'he'] else 'en'
        self.t = REPORT_TRANSLATIONS[self.language]
        self.vt = VIOLATION_TYPE_TRANSLATIONS[self.language]
        self.styles = getSampleStyleSheet()
        self.font_name = 'HebrewFont' if HEBREW_FONT_AVAILABLE else 'Helvetica'
        self.font_name_bold = 'HebrewFontBold' if HEBREW_FONT_AVAILABLE else 'Helvetica-Bold'
        self._setup_custom_styles()

    def _fmt_currency(self, amount: float) -> str:
        """Format amount with currency symbol."""
        return f"{self.t['currency']}{amount:,.2f}"

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e293b'),
            fontName=self.font_name_bold,
        ))

        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#6366f1'),
            fontName=self.font_name_bold,
        ))

        # Subsection header
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#334155'),
            fontName=self.font_name_bold,
        ))

        # Body text - use custom name to avoid conflict
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=6,
            spaceAfter=6,
            leading=14,
            fontName=self.font_name,
        ))

        # Highlight text (for important findings)
        self.styles.add(ParagraphStyle(
            name='ReportHighlight',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=8,
            textColor=colors.HexColor('#10b981'),
            fontName=self.font_name_bold,
        ))

        # Warning text
        self.styles.add(ParagraphStyle(
            name='ReportWarning',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=8,
            textColor=colors.HexColor('#ef4444'),
            fontName=self.font_name_bold,
        ))

        # Small text for footnotes
        self.styles.add(ParagraphStyle(
            name='ReportSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#64748b'),
            fontName=self.font_name,
        ))

    def generate_report(self, data: dict) -> bytes:
        """
        Generate a comprehensive PDF report from analysis data.

        Args:
            data: Dictionary containing analysis results

        Returns:
            PDF file as bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )

        # Build the report content
        story = []

        # Title page content
        story.extend(self._build_title_section(data))
        story.append(Spacer(1, 20))

        # Executive Summary
        story.extend(self._build_executive_summary(data))
        story.append(Spacer(1, 15))

        # Methodology section
        story.extend(self._build_methodology_section(data))
        story.append(Spacer(1, 15))

        # Summary statistics
        story.extend(self._build_summary_section(data))
        story.append(Spacer(1, 15))

        # Detailed payslip analysis
        if data.get('payslip_details'):
            story.extend(self._build_payslip_details_section(data))
            story.append(Spacer(1, 15))

        # Violations section (if any)
        if data.get('violation_types') or data.get('violations'):
            story.extend(self._build_violations_section(data))
            story.append(Spacer(1, 15))

        # Conclusions and recommendations
        story.extend(self._build_conclusions_section(data))

        # Footer with disclaimer
        story.extend(self._build_disclaimer_section())

        # Build the PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _build_title_section(self, data: dict) -> list:
        """Build the title section of the report."""
        elements = []

        elements.append(Paragraph(
            self.t['title'],
            self.styles['ReportTitle']
        ))

        elements.append(Paragraph(
            f"{self.t['generated_on']}: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
            self.styles['ReportBody']
        ))

        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=colors.HexColor('#6366f1'),
            spaceBefore=10,
            spaceAfter=20,
        ))

        return elements

    def _build_executive_summary(self, data: dict) -> list:
        """Build the executive summary section."""
        elements = []

        elements.append(Paragraph(self.t['executive_summary'], self.styles['SectionHeader']))

        total_payslips = data.get('total_payslips', 0)
        compliant = data.get('compliant_payslips', 0)
        total_missing = data.get('total_missing', 0)
        compliance_rate = data.get('compliance_rate', 100)
        risk_level = data.get('risk_level', 'low')

        # Overall status
        if total_missing == 0:
            status_text = f"<b>{self.t['overall_status']}: {self.t['compliant']}</b>"
            elements.append(Paragraph(status_text, self.styles['ReportHighlight']))
        else:
            status_text = f"<b>{self.t['overall_status']}: {self.t['violations_found']}</b>"
            elements.append(Paragraph(status_text, self.styles['ReportWarning']))

        # Key metrics summary
        summary_text = f"""
        <b>{self.t['key_findings']}:</b><br/>
        • {self.t['total_payslips']}: {total_payslips}<br/>
        • {self.t['compliant_payslips']}: {compliant}<br/>
        • {self.t['non_compliant_payslips']}: {total_payslips - compliant}<br/>
        • {self.t['compliance_rate']}: {compliance_rate:.1f}%<br/>
        • {self.t['risk_assessment']}: {risk_level.upper()}<br/>
        • {self.t['total_missing']}: {self._fmt_currency(total_missing)}
        """
        elements.append(Paragraph(summary_text, self.styles['ReportBody']))

        return elements

    def _build_methodology_section(self, data: dict) -> list:
        """Build the methodology section explaining how analysis was performed."""
        elements = []

        elements.append(Paragraph(self.t['methodology'], self.styles['SectionHeader']))
        elements.append(Paragraph(self.t['methodology_intro'], self.styles['ReportBody']))

        # Data extraction explanation
        elements.append(Paragraph(f"1. {self.t['data_extraction']}", self.styles['SubsectionHeader']))
        elements.append(Paragraph(self.t['data_extraction_text'], self.styles['ReportBody']))

        # Validation checks explanation
        elements.append(Paragraph(f"2. {self.t['validation_checks']}", self.styles['SubsectionHeader']))

        # Create a style for table cells that allows wrapping
        cell_style = ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            fontName=self.font_name,
        )
        header_style = ParagraphStyle(
            'TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName=self.font_name_bold,
            textColor=colors.white,
        )

        checks_data = [
            [Paragraph(self.t['check'], header_style), Paragraph(self.t['description'], header_style), Paragraph(self.t['legal_basis'], header_style)],
            [Paragraph(self.t['minimum_wage_check'], cell_style), Paragraph(self.t['minimum_wage_desc'], cell_style), Paragraph(self.t['minimum_wage_law'], cell_style)],
            [Paragraph(self.t['hours_rate_check'], cell_style), Paragraph(self.t['hours_rate_desc'], cell_style), Paragraph(self.t['hours_rate_law'], cell_style)],
            [Paragraph(self.t['pension_check'], cell_style), Paragraph(self.t['pension_desc'], cell_style), Paragraph(self.t['pension_law'], cell_style)],
        ]

        checks_table = Table(checks_data, colWidths=[1.1*inch, 2.5*inch, 2.0*inch])
        checks_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        elements.append(checks_table)

        # Legal framework
        elements.append(Paragraph(f"3. {self.t['legal_framework']}", self.styles['SubsectionHeader']))
        elements.append(Paragraph(self.t['legal_framework_text'], self.styles['ReportBody']))

        return elements

    def _build_summary_section(self, data: dict) -> list:
        """Build the summary statistics section."""
        elements = []

        elements.append(Paragraph(self.t['analysis_summary'], self.styles['SectionHeader']))

        # Build summary table
        total_checks = data.get('analysis_info', {}).get('total_checks_performed',
                                                          (data.get('total_payslips', 1) * 3))

        summary_data = [
            [self.t['metric'], self.t['value']],
            [self.t['total_payslips'], str(data.get('total_payslips', 0))],
            [self.t['total_checks'], str(total_checks)],
            [self.t['compliant_payslips'], str(data.get('compliant_payslips', 0))],
            [self.t['non_compliant_payslips'], str(data.get('non_compliant_payslips', 0))],
            [self.t['compliance_rate'], f"{data.get('compliance_rate', 100):.1f}%"],
            [self.t['risk_level'], data.get('risk_level', 'Low').upper()],
            [self.t['total_missing'], self._fmt_currency(data.get('total_missing', 0))],
        ]

        if data.get('projected_annual_liability'):
            summary_data.append([self.t['projected_liability'],
                               self._fmt_currency(data.get('projected_annual_liability', 0))])

        summary_table = Table(summary_data, colWidths=[3*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f1f5f9')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f1f5f9'), colors.white]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ]))
        elements.append(summary_table)

        return elements

    def _build_payslip_details_section(self, data: dict) -> list:
        """Build detailed per-payslip analysis section."""
        elements = []

        elements.append(Paragraph(self.t['detailed_analysis'], self.styles['SectionHeader']))

        payslip_details = data.get('payslip_details', [])

        for i, detail in enumerate(payslip_details, 1):
            month_name = detail.get('month_name', detail.get('month', f'Payslip {i}'))
            is_compliant = detail.get('validation_results', {}).get('is_compliant', True)

            # Payslip header
            status_text = f"✓ {self.t['compliant']}" if is_compliant else f"✗ {self.t['violations_found']}"
            status_color = '#10b981' if is_compliant else '#ef4444'

            elements.append(Paragraph(
                f"<font color='{status_color}'>{month_name} - {status_text}</font>",
                self.styles['SubsectionHeader']
            ))

            # Extracted data table
            extracted = detail.get('extracted_data', {})
            legal = detail.get('legal_requirements', {})

            data_rows = [
                [self.t['field'], self.t['extracted_value'], self.t['legal_requirement'], self.t['status']],
                [
                    self.t['gross_salary'],
                    self._fmt_currency(extracted.get('gross_salary', 0)),
                    '-',
                    '-'
                ],
                [
                    self.t['net_salary'],
                    self._fmt_currency(extracted.get('net_salary', 0)),
                    '-',
                    '-'
                ],
                [
                    self.t['hours_worked'],
                    f"{extracted.get('hours_worked', 0):.1f}",
                    '-',
                    '-'
                ],
                [
                    self.t['hourly_rate'],
                    self._fmt_currency(extracted.get('hourly_rate', 0)),
                    f"{self._fmt_currency(legal.get('minimum_hourly_wage', 0))} ({self.t['min_label']})",
                    '✓' if extracted.get('hourly_rate', 0) >= legal.get('minimum_hourly_wage', 0) else '✗'
                ],
                [
                    self.t['pension_employee'],
                    self._fmt_currency(extracted.get('pension_employee', 0)),
                    f"{self._fmt_currency(legal.get('expected_pension_employee', 0))} ({legal.get('pension_employee_rate', '6%')})",
                    '✓' if extracted.get('pension_employee', 0) >= legal.get('expected_pension_employee', 0) * 0.95 else '✗'
                ],
            ]

            detail_table = Table(data_rows, colWidths=[1.5*inch, 1.3*inch, 1.8*inch, 0.6*inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#475569')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ]))
            elements.append(detail_table)

            # Validation checks
            checks = detail.get('checks', [])
            if checks:
                elements.append(Spacer(1, 8))
                elements.append(Paragraph(f"<b>{self.t['validation_results']}:</b>", self.styles['ReportBody']))

                for check in checks:
                    check_status = self.t['pass'] if check.get('passed') else self.t['fail']
                    check_color = '#10b981' if check.get('passed') else '#ef4444'
                    # Use translated name
                    check_name = check.get('name', '').replace('_', ' ').title()
                    # Build description
                    if check.get('name') == 'minimum_wage':
                        desc = self.t['hourly_rate_vs_min'].format(
                            actual=self._fmt_currency(check.get('actual', 0)),
                            required=self._fmt_currency(check.get('required', 0))
                        )
                    elif check.get('name') == 'hours_calculation':
                        desc = self.t['hours_calc_desc'].format(hours=check.get('actual', 0))
                    elif check.get('name') == 'pension_contribution':
                        desc = self.t['pension_desc_detail'].format(
                            actual=self._fmt_currency(check.get('actual', 0)),
                            required=self._fmt_currency(check.get('required', 0))
                        )
                    else:
                        desc = check.get('description', '')
                    check_text = f"<font color='{check_color}'>[{check_status}]</font> {check_name}: {desc}"
                    elements.append(Paragraph(check_text, self.styles['ReportSmall']))

            elements.append(Spacer(1, 15))

        return elements

    def _build_violations_section(self, data: dict) -> list:
        """Build the violations summary section."""
        elements = []

        elements.append(Paragraph(self.t['violations_summary'], self.styles['SectionHeader']))

        violations = data.get('violations', [])
        violation_types = data.get('violation_types', [])

        if not violations and not violation_types:
            elements.append(Paragraph(self.t['no_violations'], self.styles['ReportHighlight']))
            return elements

        if violation_types:
            # Translate violation types to human-readable names
            translated_types = [self.vt.get(vt, vt.replace('_', ' ').title()) for vt in violation_types]
            types_text = f"<b>{self.t['types_found']}:</b> {', '.join(translated_types)}"
            elements.append(Paragraph(types_text, self.styles['ReportWarning']))

        if violations:
            violation_data = [[self.t['type'], self.t['description'], self.t['expected'], self.t['actual'], self.t['missing']]]

            for v in violations:
                # Use translated type name
                v_type = v.get('type', '')
                v_type_display = self.vt.get(v_type, v_type.replace('_', ' ').title())
                # Use description
                v_desc = v.get('description', '')
                if len(v_desc) > 50:
                    v_desc = v_desc[:47] + '...'
                violation_data.append([
                    v_type_display,
                    v_desc,
                    self._fmt_currency(v.get('expected', v.get('expected_value', 0))),
                    self._fmt_currency(v.get('actual', v.get('actual_value', 0))),
                    self._fmt_currency(abs(v.get('missing', v.get('missing_amount', 0)))),
                ])

            violation_table = Table(violation_data, colWidths=[1.2*inch, 1.8*inch, 1*inch, 1*inch, 1*inch])
            violation_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef2f2')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#fca5a5')),
            ]))
            elements.append(violation_table)

        return elements

    def _build_conclusions_section(self, data: dict) -> list:
        """Build conclusions and recommendations section."""
        elements = []

        elements.append(Paragraph(self.t['conclusions'], self.styles['SectionHeader']))

        total_missing = data.get('total_missing', 0)
        compliance_rate = data.get('compliance_rate', 100)
        risk_level = data.get('risk_level', 'low')

        if total_missing == 0:
            conclusion_text = self.t['conclusion_compliant']
            recommendations = self.t['recommendations_compliant'].replace('\n', '<br/>')
            elements.append(Paragraph(f"<b>{conclusion_text}</b><br/><br/>{recommendations}", self.styles['ReportBody']))
        else:
            conclusion_text = self.t['conclusion_violations'].format(
                amount=self._fmt_currency(total_missing),
                rate=f"{compliance_rate:.1f}",
                level=risk_level.upper()
            )
            recommendations = self.t['recommendations_violations'].replace('\n', '<br/>')
            elements.append(Paragraph(f"<b>{conclusion_text}</b><br/><br/>{recommendations}", self.styles['ReportBody']))

        return elements

    def _build_disclaimer_section(self) -> list:
        """Build the disclaimer section."""
        elements = []

        elements.append(Spacer(1, 30))
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#cbd5e1'),
            spaceBefore=10,
            spaceAfter=10,
        ))

        elements.append(Paragraph(self.t['disclaimer'], self.styles['ReportSmall']))

        elements.append(Spacer(1, 10))
        elements.append(Paragraph(
            f"Report generated by SalaryValidator v0.1.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['ReportSmall']
        ))

        return elements


def generate_pdf_report(data: dict, language: str = 'en') -> bytes:
    """
    Convenience function to generate a PDF report.

    Args:
        data: Analysis results dictionary
        language: Report language ('en' or 'he')

    Returns:
        PDF file as bytes
    """
    generator = PDFReportGenerator(language=language)
    return generator.generate_report(data)
