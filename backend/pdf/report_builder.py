"""
PDF Report Builder

Generates a complete Management Report PDF with:
- Cover page
- Table of contents
- Executive Summary
- Balance Sheet
- Profit & Loss (single month)
- P&L by Month
- P&L Monthly Comparison
- P&L YTD Comparison
"""

from io import BytesIO
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Image, KeepTogether, PageTemplate, Frame, Flowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY


# Accent color: muted rose
ACCENT_COLOR = colors.HexColor("#C9A99A")
TEXT_COLOR = colors.HexColor("#333333")


class HeaderFooter(PageTemplate):
    """Custom page template with headers and footers."""

    def __init__(self, pagesize=letter, page_number=1, client_name=""):
        frame = Frame(0.5 * inch, 0.5 * inch, 7.5 * inch, 9.5 * inch, id='normal')
        PageTemplate.__init__(self, pagesize, [frame])
        self.page_number = page_number
        self.client_name = client_name

    def beforeDrawPage(self, canvas, doc):
        """Draw header and footer."""
        canvas.saveState()

        # Page number footer
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawString(7.5 * inch, 0.3 * inch, f"Page {self.page_number}")

        # Footer text
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(0.5 * inch, 0.3 * inch, "For management use only")

        canvas.restoreState()


class ReportBuilder:
    """Builds the complete PDF report."""

    def __init__(self, context: Dict[str, Any]):
        """
        Initialize report builder with financial data context.

        Args:
            context: Dict with keys:
                - client_name: str
                - bookkeeper_name: str
                - period_start: datetime
                - period_end: datetime
                - balance_sheet: Dict[str, float]
                - pl_current_month: Dict[str, float]
                - pl_by_month: List[Dict]
                - pl_monthly_comparison: Dict
                - pl_ytd_comparison: Dict
                - kpis: Dict[str, Any]
                - ai_insights: str
                - logo_path: Optional[str]
        """
        self.context = context
        self.styles = self._create_styles()
        self.story = []
        self.page_count = 0

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create custom paragraph styles."""
        styles = getSampleStyleSheet()

        custom_styles = {
            'title': ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=28,
                textColor=ACCENT_COLOR,
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
            ),
            'heading1': ParagraphStyle(
                'CustomHeading1',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=ACCENT_COLOR,
                spaceAfter=12,
                spaceBefore=12,
                fontName='Helvetica-Bold',
            ),
            'heading2': ParagraphStyle(
                'CustomHeading2',
                parent=styles['Heading2'],
                fontSize=12,
                textColor=ACCENT_COLOR,
                spaceAfter=10,
                spaceBefore=6,
                fontName='Helvetica-Bold',
            ),
            'normal': ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                textColor=TEXT_COLOR,
                alignment=TA_LEFT,
                spaceAfter=6,
            ),
            'small': ParagraphStyle(
                'CustomSmall',
                parent=styles['Normal'],
                fontSize=9,
                textColor=TEXT_COLOR,
                spaceAfter=4,
            ),
        }
        return custom_styles

    def _format_currency(self, value: float) -> str:
        """Format a number as currency."""
        return f"${value:,.2f}"

    def _format_percentage(self, value: float) -> str:
        """Format a number as percentage."""
        return f"{value:.1f}%"

    def build(self) -> bytes:
        """Build and return the complete PDF as bytes."""
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        self._build_story()
        doc.build(self.story)

        return buffer.getvalue()

    def _build_story(self):
        """Build the document story (sequence of elements)."""
        self._add_cover_page()
        self.story.append(PageBreak())

        self._add_table_of_contents()
        self.story.append(PageBreak())

        self._add_executive_summary()
        self.story.append(PageBreak())

        self._add_balance_sheet()
        self.story.append(PageBreak())

        self._add_pl_current_month()
        self.story.append(PageBreak())

        self._add_pl_by_month()
        self.story.append(PageBreak())

        self._add_pl_monthly_comparison()
        self.story.append(PageBreak())

        self._add_pl_ytd_comparison()

    def _add_cover_page(self):
        """Add the cover page with client info."""
        # Logo (if available)
        if self.context.get('logo_path'):
            try:
                img = Image(self.context['logo_path'], width=2*inch, height=2*inch)
                self.story.append(img)
                self.story.append(Spacer(1, 0.3*inch))
            except Exception:
                pass  # Skip logo if not available

        # Title
        title = Paragraph(
            f"Management Report",
            self.styles['title']
        )
        self.story.append(title)
        self.story.append(Spacer(1, 0.3*inch))

        # Client and period info
        client_name = self.context.get('client_name', 'Client')
        period_start = self.context.get('period_start')
        period_end = self.context.get('period_end')

        period_str = ""
        if period_start and period_end:
            period_str = f"{period_start.strftime('%B %d, %Y')} – {period_end.strftime('%B %d, %Y')}"

        info_lines = [
            f"<b>Client:</b> {client_name}",
            f"<b>Period:</b> {period_str}",
            f"<b>Bookkeeper:</b> {self.context.get('bookkeeper_name', 'N/A')}",
            f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y')}",
        ]

        for line in info_lines:
            self.story.append(Paragraph(line, self.styles['normal']))
            self.story.append(Spacer(1, 0.15*inch))

    def _add_table_of_contents(self):
        """Add table of contents."""
        title = Paragraph("Table of Contents", self.styles['heading1'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.2*inch))

        toc_items = [
            "Executive Summary",
            "Balance Sheet",
            "Profit & Loss (Current Month)",
            "Profit & Loss by Month",
            "Profit & Loss Monthly Comparison",
            "Profit & Loss YTD Comparison",
        ]

        for i, item in enumerate(toc_items, 1):
            self.story.append(Paragraph(f"{i}. {item}", self.styles['normal']))
            self.story.append(Spacer(1, 0.12*inch))

    def _add_executive_summary(self):
        """Add executive summary with KPIs and insights."""
        title = Paragraph("Executive Summary", self.styles['heading1'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.15*inch))

        # KPIs section
        kpis = self.context.get('kpis', {})
        if kpis:
            kpi_title = Paragraph("Key Performance Indicators", self.styles['heading2'])
            self.story.append(kpi_title)
            self.story.append(Spacer(1, 0.1*inch))

            # Build KPI table
            kpi_data = [["Metric", "Value"]]
            for key, value in kpis.items():
                if isinstance(value, float):
                    if 'percentage' in key.lower() or 'margin' in key.lower():
                        formatted = self._format_percentage(value)
                    else:
                        formatted = self._format_currency(value)
                else:
                    formatted = str(value)
                kpi_data.append([key.replace('_', ' ').title(), formatted])

            if len(kpi_data) > 1:
                kpi_table = Table(kpi_data, colWidths=[3.5*inch, 2*inch])
                kpi_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), ACCENT_COLOR),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), TA_LEFT),
                    ('ALIGN', (1, 0), (-1, -1), TA_RIGHT),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                self.story.append(kpi_table)
                self.story.append(Spacer(1, 0.2*inch))

        # AI Insights section
        insights = self.context.get('ai_insights', '')
        if insights:
            insights_title = Paragraph("AI-Generated Insights & Tax Tips", self.styles['heading2'])
            self.story.append(insights_title)
            self.story.append(Spacer(1, 0.1*inch))

            insights_para = Paragraph(insights, self.styles['normal'])
            self.story.append(insights_para)
            self.story.append(Spacer(1, 0.15*inch))

    def _add_balance_sheet(self):
        """Add balance sheet section."""
        title = Paragraph("Balance Sheet", self.styles['heading1'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.15*inch))

        bs = self.context.get('balance_sheet', {})
        if not bs:
            self.story.append(Paragraph("No balance sheet data available.", self.styles['normal']))
            return

        # Build balance sheet table
        bs_data = [["Account", "Amount"]]

        assets = {}
        liabilities = {}
        equity = {}

        # Categorize accounts (simplified)
        for account, amount in bs.items():
            if any(x in account.lower() for x in ['asset', 'bank', 'cash', 'receivable', 'inventory']):
                assets[account] = amount
            elif any(x in account.lower() for x in ['liability', 'payable', 'loan', 'debt']):
                liabilities[account] = amount
            else:
                equity[account] = amount

        # Assets
        if assets:
            bs_data.append(["<b>ASSETS</b>", ""])
            total_assets = 0
            for account, amount in sorted(assets.items()):
                bs_data.append([f"  {account}", self._format_currency(amount)])
                total_assets += amount
            bs_data.append(["<b>Total Assets</b>", f"<b>{self._format_currency(total_assets)}</b>"])

        # Liabilities
        if liabilities:
            bs_data.append(["", ""])
            bs_data.append(["<b>LIABILITIES</b>", ""])
            total_liabilities = 0
            for account, amount in sorted(liabilities.items()):
                bs_data.append([f"  {account}", self._format_currency(amount)])
                total_liabilities += amount
            bs_data.append(["<b>Total Liabilities</b>", f"<b>{self._format_currency(total_liabilities)}</b>"])

        # Equity
        if equity:
            bs_data.append(["", ""])
            bs_data.append(["<b>EQUITY</b>", ""])
            total_equity = 0
            for account, amount in sorted(equity.items()):
                bs_data.append([f"  {account}", self._format_currency(amount)])
                total_equity += amount
            bs_data.append(["<b>Total Equity</b>", f"<b>{self._format_currency(total_equity)}</b>"])

        bs_table = Table(bs_data, colWidths=[3.5*inch, 2*inch])
        bs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), TA_LEFT),
            ('ALIGN', (1, 0), (-1, -1), TA_RIGHT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        self.story.append(bs_table)

    def _add_pl_current_month(self):
        """Add P&L for current month only."""
        title = Paragraph("Profit & Loss - Current Month", self.styles['heading1'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.15*inch))

        pl = self.context.get('pl_current_month', {})
        if not pl:
            self.story.append(Paragraph("No P&L data available.", self.styles['normal']))
            return

        pl_data = [["Account", "Amount"]]

        # Income section
        income_accounts = {k: v for k, v in pl.items() if any(x in k.lower() for x in ['income', 'sales', 'revenue'])}
        if income_accounts:
            pl_data.append(["<b>INCOME</b>", ""])
            total_income = 0
            for account, amount in sorted(income_accounts.items()):
                pl_data.append([f"  {account}", self._format_currency(amount)])
                total_income += amount
            pl_data.append(["<b>Total Income</b>", f"<b>{self._format_currency(total_income)}</b>"])

        # Expense section
        pl_data.append(["", ""])
        pl_data.append(["<b>EXPENSES</b>", ""])
        expense_accounts = {k: v for k, v in pl.items() if 'expense' in k.lower() or 'cost' in k.lower()}
        total_expenses = 0
        for account, amount in sorted(expense_accounts.items()):
            pl_data.append([f"  {account}", self._format_currency(abs(amount))])
            total_expenses += abs(amount)
        pl_data.append(["<b>Total Expenses</b>", f"<b>{self._format_currency(total_expenses)}</b>"])

        # Net income
        pl_data.append(["", ""])
        net_income = total_income - total_expenses
        pl_data.append(["<b>NET INCOME</b>", f"<b>{self._format_currency(net_income)}</b>"])

        pl_table = Table(pl_data, colWidths=[3.5*inch, 2*inch])
        pl_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), TA_LEFT),
            ('ALIGN', (1, 0), (-1, -1), TA_RIGHT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        self.story.append(pl_table)

    def _add_pl_by_month(self):
        """Add P&L by month with monthly columns."""
        title = Paragraph("Profit & Loss by Month", self.styles['heading1'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.15*inch))

        pl_by_month = self.context.get('pl_by_month', [])
        if not pl_by_month:
            self.story.append(Paragraph("No monthly P&L data available.", self.styles['normal']))
            return

        # Collect all accounts and months
        all_accounts = set()
        for month_data in pl_by_month:
            all_accounts.update(month_data.get('data', {}).keys())

        months = [m.get('month') for m in pl_by_month]

        # Build table: Account | Month1 | Month2 | ... | YTD Total
        col_widths = [2.5*inch] + [0.65*inch] * len(months) + [0.65*inch]
        pl_data = [["Account"] + months + ["YTD Total"]]

        for account in sorted(all_accounts):
            row = [account]
            ytd_total = 0
            for month_data in pl_by_month:
                value = month_data.get('data', {}).get(account, 0)
                row.append(self._format_currency(value))
                ytd_total += value
            row.append(self._format_currency(ytd_total))
            pl_data.append(row)

        pl_table = Table(pl_data, colWidths=col_widths)
        pl_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), TA_LEFT),
            ('ALIGN', (1, 0), (-1, -1), TA_RIGHT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        self.story.append(pl_table)

    def _add_pl_monthly_comparison(self):
        """Add P&L monthly comparison."""
        title = Paragraph("Profit & Loss - Monthly Comparison", self.styles['heading1'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.15*inch))

        comparison = self.context.get('pl_monthly_comparison', {})
        if not comparison:
            self.story.append(Paragraph("No comparison data available.", self.styles['normal']))
            return

        comp_data = [["Account", "This Month", "Last Month", "Change", "% Change"]]

        for account, metrics in sorted(comparison.items()):
            this_month = metrics.get('this_month', 0)
            last_month = metrics.get('last_month', 0)
            change = this_month - last_month
            pct_change = (change / last_month * 100) if last_month != 0 else 0

            comp_data.append([
                account,
                self._format_currency(this_month),
                self._format_currency(last_month),
                self._format_currency(change),
                self._format_percentage(pct_change),
            ])

        comp_table = Table(comp_data, colWidths=[2*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.1*inch])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), TA_LEFT),
            ('ALIGN', (1, 0), (-1, -1), TA_RIGHT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        self.story.append(comp_table)

    def _add_pl_ytd_comparison(self):
        """Add P&L YTD comparison."""
        title = Paragraph("Profit & Loss - YTD Comparison", self.styles['heading1'])
        self.story.append(title)
        self.story.append(Spacer(1, 0.15*inch))

        ytd = self.context.get('pl_ytd_comparison', {})
        if not ytd:
            self.story.append(Paragraph("No YTD comparison data available.", self.styles['normal']))
            return

        ytd_data = [["Account", "This Year", "Last Year", "Change", "% Change"]]

        for account, metrics in sorted(ytd.items()):
            this_year = metrics.get('this_year', 0)
            last_year = metrics.get('last_year', 0)
            change = this_year - last_year
            pct_change = (change / last_year * 100) if last_year != 0 else 0

            ytd_data.append([
                account,
                self._format_currency(this_year),
                self._format_currency(last_year),
                self._format_currency(change),
                self._format_percentage(pct_change),
            ])

        ytd_table = Table(ytd_data, colWidths=[2*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.1*inch])
        ytd_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACCENT_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), TA_LEFT),
            ('ALIGN', (1, 0), (-1, -1), TA_RIGHT),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        self.story.append(ytd_table)
