"""PDF Report Generator for SalaryValidator."""

import io
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


class PDFReportGenerator:
    """Generate comprehensive PDF reports for payslip analysis."""

    def __init__(self):
        """Initialize the PDF generator with styles."""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

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
        ))

        # Section header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=12,
            textColor=colors.HexColor('#6366f1'),
        ))

        # Subsection header
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#334155'),
        ))

        # Body text - use custom name to avoid conflict
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=6,
            spaceAfter=6,
            leading=14,
        ))

        # Highlight text (for important findings)
        self.styles.add(ParagraphStyle(
            name='ReportHighlight',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=8,
            textColor=colors.HexColor('#10b981'),
            fontName='Helvetica-Bold',
        ))

        # Warning text
        self.styles.add(ParagraphStyle(
            name='ReportWarning',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=8,
            spaceAfter=8,
            textColor=colors.HexColor('#ef4444'),
            fontName='Helvetica-Bold',
        ))

        # Small text for footnotes
        self.styles.add(ParagraphStyle(
            name='ReportSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#64748b'),
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
            "Payslip Compliance Analysis Report",
            self.styles['ReportTitle']
        ))

        elements.append(Paragraph(
            f"Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M')}",
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

        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))

        total_payslips = data.get('total_payslips', 0)
        compliant = data.get('compliant_payslips', 0)
        total_missing = data.get('total_missing', 0)
        compliance_rate = data.get('compliance_rate', 100)
        risk_level = data.get('risk_level', 'low')

        # Overall status
        if total_missing == 0:
            status_text = f"""
            <b>Overall Status: COMPLIANT</b><br/><br/>
            After thorough analysis of {total_payslips} payslip(s), all reviewed documents
            were found to be in compliance with Israeli labor laws. No violations were detected,
            and no missing payments were identified.
            """
            elements.append(Paragraph(status_text, self.styles['ReportHighlight']))
        else:
            status_text = f"""
            <b>Overall Status: VIOLATIONS FOUND</b><br/><br/>
            Analysis of {total_payslips} payslip(s) revealed compliance issues.
            Total estimated missing payments: NIS {total_missing:,.2f}
            """
            elements.append(Paragraph(status_text, self.styles['ReportWarning']))

        # Key metrics summary
        summary_text = f"""
        <b>Key Findings:</b><br/>
        • Total payslips analyzed: {total_payslips}<br/>
        • Compliant payslips: {compliant}<br/>
        • Non-compliant payslips: {total_payslips - compliant}<br/>
        • Overall compliance rate: {compliance_rate:.1f}%<br/>
        • Risk assessment: {risk_level.upper()}<br/>
        • Total missing amount: NIS {total_missing:,.2f}
        """
        elements.append(Paragraph(summary_text, self.styles['ReportBody']))

        return elements

    def _build_methodology_section(self, data: dict) -> list:
        """Build the methodology section explaining how analysis was performed."""
        elements = []

        elements.append(Paragraph("Analysis Methodology", self.styles['SectionHeader']))

        methodology_text = """
        This analysis was conducted using automated payslip validation technology.
        The following process was applied to each payslip:
        """
        elements.append(Paragraph(methodology_text, self.styles['ReportBody']))

        # Data extraction explanation
        elements.append(Paragraph("1. Data Extraction", self.styles['SubsectionHeader']))
        extraction_text = """
        Payslip data was extracted using Optical Character Recognition (OCR) technology.
        Key fields extracted include: gross salary, net salary, hours worked, hourly rate,
        overtime hours and pay, pension contributions, income tax, and national insurance deductions.
        """
        elements.append(Paragraph(extraction_text, self.styles['ReportBody']))

        # Validation checks explanation
        elements.append(Paragraph("2. Validation Checks Performed", self.styles['SubsectionHeader']))

        # Create a style for table cells that allows wrapping
        cell_style = ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
        )
        header_style = ParagraphStyle(
            'TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            fontName='Helvetica-Bold',
            textColor=colors.white,
        )

        checks_data = [
            [Paragraph('Check', header_style), Paragraph('Description', header_style), Paragraph('Legal Basis', header_style)],
            [Paragraph('Minimum Wage', cell_style), Paragraph('Verifies hourly rate meets legal minimum', cell_style), Paragraph('Minimum Wage Law 5747-1987', cell_style)],
            [Paragraph('Hours × Rate', cell_style), Paragraph('Validates salary calculation accuracy', cell_style), Paragraph('Protection of Wages Law 5718-1958', cell_style)],
            [Paragraph('Pension', cell_style), Paragraph('Checks mandatory pension deductions (6% employee, 6.5% employer)', cell_style), Paragraph('Pension Extension Order 2008', cell_style)],
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
        elements.append(Paragraph("3. Legal Framework", self.styles['SubsectionHeader']))
        legal_text = """
        All validations are based on current Israeli labor laws and regulations. Minimum wage
        rates are date-specific, accounting for historical changes in the legal minimum wage.
        The current minimum wage (as of April 2024) is NIS 5,880.02 per month (NIS 32.30 per hour).
        """
        elements.append(Paragraph(legal_text, self.styles['ReportBody']))

        return elements

    def _build_summary_section(self, data: dict) -> list:
        """Build the summary statistics section."""
        elements = []

        elements.append(Paragraph("Analysis Summary", self.styles['SectionHeader']))

        # Build summary table
        total_checks = data.get('analysis_info', {}).get('total_checks_performed',
                                                          (data.get('total_payslips', 1) * 3))

        summary_data = [
            ['Metric', 'Value'],
            ['Total Payslips Analyzed', str(data.get('total_payslips', 0))],
            ['Total Validation Checks Performed', str(total_checks)],
            ['Compliant Payslips', str(data.get('compliant_payslips', 0))],
            ['Non-Compliant Payslips', str(data.get('non_compliant_payslips', 0))],
            ['Compliance Rate', f"{data.get('compliance_rate', 100):.1f}%"],
            ['Risk Level', data.get('risk_level', 'Low').upper()],
            ['Total Missing Amount', f"NIS {data.get('total_missing', 0):,.2f}"],
        ]

        if data.get('projected_annual_liability'):
            summary_data.append(['Projected Annual Liability',
                               f"NIS {data.get('projected_annual_liability', 0):,.2f}"])

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

        elements.append(Paragraph("Detailed Payslip Analysis", self.styles['SectionHeader']))

        payslip_details = data.get('payslip_details', [])

        for i, detail in enumerate(payslip_details, 1):
            month_name = detail.get('month_name', detail.get('month', f'Payslip {i}'))
            is_compliant = detail.get('validation_results', {}).get('is_compliant', True)

            # Payslip header
            status_text = "✓ COMPLIANT" if is_compliant else "✗ VIOLATIONS FOUND"
            status_color = '#10b981' if is_compliant else '#ef4444'

            elements.append(Paragraph(
                f"<font color='{status_color}'>{month_name} - {status_text}</font>",
                self.styles['SubsectionHeader']
            ))

            # Extracted data table
            extracted = detail.get('extracted_data', {})
            legal = detail.get('legal_requirements', {})

            data_rows = [
                ['Field', 'Extracted Value', 'Legal Requirement', 'Status'],
                [
                    'Gross Salary',
                    f"NIS {extracted.get('gross_salary', 0):,.2f}",
                    '-',
                    '-'
                ],
                [
                    'Net Salary',
                    f"NIS {extracted.get('net_salary', 0):,.2f}",
                    '-',
                    '-'
                ],
                [
                    'Hours Worked',
                    f"{extracted.get('hours_worked', 0):.1f}",
                    '-',
                    '-'
                ],
                [
                    'Hourly Rate',
                    f"NIS {extracted.get('hourly_rate', 0):,.2f}",
                    f"NIS {legal.get('minimum_hourly_wage', 0):,.2f} (min)",
                    '✓' if extracted.get('hourly_rate', 0) >= legal.get('minimum_hourly_wage', 0) else '✗'
                ],
                [
                    'Pension (Employee)',
                    f"NIS {extracted.get('pension_employee', 0):,.2f}",
                    f"NIS {legal.get('expected_pension_employee', 0):,.2f} ({legal.get('pension_employee_rate', '6%')})",
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
                elements.append(Paragraph("<b>Validation Results:</b>", self.styles['ReportBody']))

                for check in checks:
                    check_status = "✓ PASS" if check.get('passed') else "✗ FAIL"
                    check_color = '#10b981' if check.get('passed') else '#ef4444'
                    check_text = f"<font color='{check_color}'>{check_status}</font> - {check.get('name_hebrew', check.get('name', ''))}: {check.get('description', '')}"
                    elements.append(Paragraph(check_text, self.styles['ReportSmall']))

            elements.append(Spacer(1, 15))

        return elements

    def _build_violations_section(self, data: dict) -> list:
        """Build the violations summary section."""
        elements = []

        elements.append(Paragraph("Violations Summary", self.styles['SectionHeader']))

        violations = data.get('violations', [])
        violation_types = data.get('violation_types', [])

        if not violations and not violation_types:
            elements.append(Paragraph(
                "No violations were found during the analysis. All payslips are compliant with Israeli labor laws.",
                self.styles['ReportHighlight']
            ))
            return elements

        if violation_types:
            types_text = f"<b>Types of violations found:</b> {', '.join(violation_types)}"
            elements.append(Paragraph(types_text, self.styles['ReportWarning']))

        if violations:
            violation_data = [['Type', 'Description', 'Expected', 'Actual', 'Missing']]

            for v in violations:
                violation_data.append([
                    v.get('type_hebrew', v.get('type', '')),
                    v.get('description', '')[:40] + '...' if len(v.get('description', '')) > 40 else v.get('description', ''),
                    f"NIS {v.get('expected', v.get('expected_value', 0)):,.2f}",
                    f"NIS {v.get('actual', v.get('actual_value', 0)):,.2f}",
                    f"NIS {v.get('missing', v.get('missing_amount', 0)):,.2f}",
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

        elements.append(Paragraph("Conclusions and Recommendations", self.styles['SectionHeader']))

        total_missing = data.get('total_missing', 0)
        compliance_rate = data.get('compliance_rate', 100)
        risk_level = data.get('risk_level', 'low')

        if total_missing == 0:
            conclusion_text = """
            <b>Conclusion:</b> Based on our comprehensive analysis, all reviewed payslips
            are in full compliance with Israeli labor laws. No corrective actions are required
            at this time.
            <br/><br/>
            <b>Recommendations:</b>
            <br/>• Continue maintaining current payroll practices
            <br/>• Perform regular audits to ensure ongoing compliance
            <br/>• Stay informed about changes to minimum wage and pension regulations
            """
            elements.append(Paragraph(conclusion_text, self.styles['ReportBody']))
        else:
            conclusion_text = f"""
            <b>Conclusion:</b> Our analysis identified compliance issues totaling NIS {total_missing:,.2f}
            in missing payments. The overall compliance rate is {compliance_rate:.1f}%,
            with a risk level assessed as {risk_level.upper()}.
            <br/><br/>
            <b>Recommendations:</b>
            <br/>• Review and rectify identified underpayments promptly
            <br/>• Consult with a labor law attorney regarding potential liabilities
            <br/>• Implement payroll system checks to prevent future violations
            <br/>• Consider voluntary disclosure to reduce potential penalties
            <br/>• Document all corrective actions taken
            """
            elements.append(Paragraph(conclusion_text, self.styles['ReportBody']))

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

        disclaimer_text = """
        <b>Disclaimer:</b> This report is generated automatically based on data extracted
        from uploaded payslip documents using OCR technology. While every effort is made to
        ensure accuracy, the analysis should be verified by a qualified professional.
        This report does not constitute legal advice. For specific legal guidance, please
        consult with a licensed labor law attorney. The analysis is based on Israeli labor
        laws as of the report generation date and may not reflect recent legislative changes.
        """
        elements.append(Paragraph(disclaimer_text, self.styles['ReportSmall']))

        elements.append(Spacer(1, 10))
        elements.append(Paragraph(
            f"Report generated by SalaryValidator v0.1.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['ReportSmall']
        ))

        return elements


def generate_pdf_report(data: dict) -> bytes:
    """
    Convenience function to generate a PDF report.

    Args:
        data: Analysis results dictionary

    Returns:
        PDF file as bytes
    """
    generator = PDFReportGenerator()
    return generator.generate_report(data)
