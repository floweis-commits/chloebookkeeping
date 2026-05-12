"""
Report Generator Agent

Orchestrates the monthly Management Report pipeline:
1. Pull data from QuickBooks (Balance Sheet, P&L, etc.)
2. Run insights agent for anomalies and tax tips
3. Assemble sections into a PDF via ReportLab
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.connectors.quickbooks import QuickBooksConnector
from backend.pdf.report_builder import ReportBuilder


class ReportGeneratorAgent:
    """Agent that orchestrates report generation pipeline."""

    # Income categories (exact names from requirements)
    INCOME_CATEGORIES = {
        "PayPal Sales",
        "Sales",
        "Sales of Product Income",
        "Total Income",
    }

    # Expense categories with subcategories
    EXPENSE_CATEGORIES = {
        "Car & Truck": ["Fuel"],
        "Contractors": [],
        "Employee Expense Reimbursements": [],
        "Horse Expenses": [],
        "Insurance": [],
        "Legal & Professional Services": [],
        "Meals": [],
        "Office Supplies & Software": [],
        "Pasture Expenses": [],
        "Payment Processing Fees": ["PayPal/QB/Shopify/Stripe Fees"],
        "Payroll Expenses": ["Officer Wages", "Payroll Fees", "Taxes"],
        "Postage & Shipping": [],
        "Retreat Expenses": [],
        "Sales Tax": [],
        "Travel": [],
        "Vet Expenses": [],
    }

    def __init__(self):
        self.qb_connector = QuickBooksConnector()
        self.glm = AsyncOpenAI(
            api_key=settings.glm_api_key,
            base_url=settings.glm_base_url,
        )

    async def generate_report(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        period_start: datetime,
        period_end: datetime,
        client_name: str,
        bookkeeper_name: str,
        logo_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete management report for a period.

        Args:
            db: Database session
            tenant_id: Tenant UUID
            period_start: Start of reporting period
            period_end: End of reporting period
            client_name: Client business name
            bookkeeper_name: Bookkeeper full name
            logo_path: Optional path to client logo

        Returns:
            Dict with report_id, pdf_bytes, and metadata
        """
        # Fetch QB connection for this tenant
        access_token = await self.qb_connector.get_access_token_for_tenant(db, str(tenant_id))
        # In a real implementation, fetch realm_id from QB connection
        realm_id = "1234567890"  # Placeholder

        # Fetch financial data from QuickBooks
        balance_sheet = await self._fetch_balance_sheet(
            access_token, realm_id, period_end
        )
        pl_current_month = await self._fetch_pl_for_month(
            access_token, realm_id, period_start, period_end
        )
        pl_by_month = await self._fetch_pl_by_month(
            access_token, realm_id, period_start, period_end
        )

        # Calculate KPIs and comparisons
        kpis = self._calculate_kpis(balance_sheet, pl_current_month)
        pl_monthly_comparison = self._calculate_monthly_comparison(
            access_token, realm_id, period_start, period_end
        )
        pl_ytd_comparison = self._calculate_ytd_comparison(
            access_token, realm_id, period_start, period_end
        )

        # Generate AI insights
        ai_insights = await self._generate_ai_insights(
            balance_sheet, pl_current_month, pl_by_month, kpis
        )

        # Assemble report context
        report_context = {
            'client_name': client_name,
            'bookkeeper_name': bookkeeper_name,
            'period_start': period_start,
            'period_end': period_end,
            'balance_sheet': balance_sheet,
            'pl_current_month': pl_current_month,
            'pl_by_month': pl_by_month,
            'kpis': kpis,
            'pl_monthly_comparison': pl_monthly_comparison,
            'pl_ytd_comparison': pl_ytd_comparison,
            'ai_insights': ai_insights,
            'logo_path': logo_path,
        }

        # Build PDF
        builder = ReportBuilder(report_context)
        pdf_bytes = builder.build()

        return {
            'pdf_bytes': pdf_bytes,
            'report_data': report_context,
            'period_start': period_start,
            'period_end': period_end,
        }

    async def _fetch_balance_sheet(
        self,
        access_token: str,
        realm_id: str,
        as_of_date: datetime,
    ) -> Dict[str, float]:
        """Fetch balance sheet from QuickBooks."""
        try:
            response = await self.qb_connector.get_balance_sheet(
                access_token,
                realm_id,
                as_of_date.strftime('%Y-%m-%d'),
            )
            return self._parse_balance_sheet(response)
        except Exception as e:
            print(f"Error fetching balance sheet: {e}")
            return {}

    async def _fetch_pl_for_month(
        self,
        access_token: str,
        realm_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, float]:
        """Fetch P&L for a specific month."""
        try:
            response = await self.qb_connector.get_profit_and_loss(
                access_token,
                realm_id,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
            )
            return self._parse_profit_and_loss(response)
        except Exception as e:
            print(f"Error fetching P&L: {e}")
            return {}

    async def _fetch_pl_by_month(
        self,
        access_token: str,
        realm_id: str,
        year_start: datetime,
        year_end: datetime,
    ) -> List[Dict[str, Any]]:
        """Fetch P&L for each month in the year."""
        pl_by_month = []
        current = year_start.replace(day=1)

        while current <= year_end:
            # Get last day of month
            if current.month == 12:
                month_end = current.replace(year=current.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current.replace(month=current.month + 1, day=1) - timedelta(days=1)

            try:
                response = await self.qb_connector.get_profit_and_loss(
                    access_token,
                    realm_id,
                    current.strftime('%Y-%m-%d'),
                    month_end.strftime('%Y-%m-%d'),
                )
                pl_data = self._parse_profit_and_loss(response)
                pl_by_month.append({
                    'month': current.strftime('%b %Y'),
                    'data': pl_data,
                })
            except Exception as e:
                print(f"Error fetching P&L for {current.strftime('%B %Y')}: {e}")

            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return pl_by_month

    async def _calculate_monthly_comparison(
        self,
        access_token: str,
        realm_id: str,
        current_start: datetime,
        current_end: datetime,
    ) -> Dict[str, Dict[str, float]]:
        """Calculate monthly comparison (this month vs last month)."""
        # Get current month P&L
        current_pl = await self._fetch_pl_for_month(
            access_token, realm_id, current_start, current_end
        )

        # Get last month dates
        if current_start.month == 1:
            last_start = current_start.replace(year=current_start.year - 1, month=12, day=1)
        else:
            last_start = current_start.replace(month=current_start.month - 1, day=1)

        if current_start.month == 1:
            last_end = last_start.replace(day=31)
        else:
            last_end = (current_start.replace(day=1) - timedelta(days=1))

        last_pl = await self._fetch_pl_for_month(access_token, realm_id, last_start, last_end)

        # Build comparison
        comparison = {}
        all_accounts = set(current_pl.keys()) | set(last_pl.keys())
        for account in sorted(all_accounts):
            comparison[account] = {
                'this_month': current_pl.get(account, 0),
                'last_month': last_pl.get(account, 0),
            }

        return comparison

    async def _calculate_ytd_comparison(
        self,
        access_token: str,
        realm_id: str,
        current_start: datetime,
        current_end: datetime,
    ) -> Dict[str, Dict[str, float]]:
        """Calculate YTD comparison (this year vs last year)."""
        # Get current year P&L (Jan 1 to period end)
        year_start = current_start.replace(month=1, day=1)
        current_ytd_pl = await self._fetch_pl_for_month(
            access_token, realm_id, year_start, current_end
        )

        # Get last year P&L (same period last year)
        last_year_start = year_start.replace(year=year_start.year - 1)
        last_year_end = current_end.replace(year=current_end.year - 1)
        last_ytd_pl = await self._fetch_pl_for_month(
            access_token, realm_id, last_year_start, last_year_end
        )

        # Build comparison
        comparison = {}
        all_accounts = set(current_ytd_pl.keys()) | set(last_ytd_pl.keys())
        for account in sorted(all_accounts):
            comparison[account] = {
                'this_year': current_ytd_pl.get(account, 0),
                'last_year': last_ytd_pl.get(account, 0),
            }

        return comparison

    def _parse_balance_sheet(self, response: Dict[str, Any]) -> Dict[str, float]:
        """Parse QB balance sheet response into account: amount dict."""
        # In a real implementation, parse QB response structure
        # This is a placeholder that returns structure expected by report builder
        return {
            "Cash": 15000.00,
            "Accounts Receivable": 8500.00,
            "Inventory": 22000.00,
            "Equipment": 35000.00,
            "Accounts Payable": -5000.00,
            "Loan Payable": -25000.00,
            "Owner Equity": 50500.00,
        }

    def _parse_profit_and_loss(self, response: Dict[str, Any]) -> Dict[str, float]:
        """Parse QB P&L response into account: amount dict."""
        # In a real implementation, parse QB response structure
        return {
            "PayPal Sales": 25000.00,
            "Sales": 35000.00,
            "Sales of Product Income": 8000.00,
            "Total Income": 68000.00,
            "Car & Truck Fuel": 450.00,
            "Contractors": 2500.00,
            "Insurance": 1200.00,
            "Office Supplies & Software": 350.00,
            "Payroll Expenses": 15000.00,
            "Travel": 800.00,
            "Vet Expenses": 2000.00,
        }

    def _calculate_kpis(
        self,
        balance_sheet: Dict[str, float],
        pl: Dict[str, float],
    ) -> Dict[str, Any]:
        """Calculate key performance indicators."""
        total_income = pl.get('Total Income', 0)
        total_assets = sum(v for k, v in balance_sheet.items() if v > 0)
        total_liabilities = abs(sum(v for k, v in balance_sheet.items() if v < 0))
        total_equity = total_assets - total_liabilities

        # Calculate common expenses
        total_expenses = sum(v for k, v in pl.items() if 'expense' in k.lower() or 'cost' in k.lower())
        net_income = total_income - total_expenses

        # Margins
        gross_margin = (total_income - 0) / total_income if total_income else 0
        net_margin = net_income / total_income if total_income else 0

        # Returns
        roa = net_income / total_assets if total_assets else 0
        roe = net_income / total_equity if total_equity else 0

        return {
            'Total Income': total_income,
            'Total Expenses': total_expenses,
            'Net Income': net_income,
            'Gross Margin %': gross_margin * 100,
            'Net Profit Margin %': net_margin * 100,
            'Return on Assets %': roa * 100,
            'Return on Equity %': roe * 100,
            'Current Assets': total_assets,
            'Current Liabilities': total_liabilities,
            'Equity': total_equity,
        }

    async def _generate_ai_insights(
        self,
        balance_sheet: Dict[str, float],
        pl: Dict[str, float],
        pl_by_month: List[Dict[str, Any]],
        kpis: Dict[str, Any],
    ) -> str:
        """Generate AI-powered insights and tax tips using Claude API."""
        # Prepare financial summary for Claude
        summary = f"""
Financial Summary:
- Total Income: ${pl.get('Total Income', 0):,.2f}
- Total Expenses: ${abs(sum(v for k, v in pl.items() if 'expense' in k.lower())):,.2f}
- Net Income: ${pl.get('Total Income', 0) - abs(sum(v for k, v in pl.items() if 'expense' in k.lower())):,.2f}
- Gross Margin: {kpis.get('Gross Margin %', 0):.1f}%
- Net Profit Margin: {kpis.get('Net Profit Margin %', 0):.1f}%

Major Accounts:
"""
        for account, amount in sorted(pl.items(), key=lambda x: abs(x[1]), reverse=True)[:10]:
            summary += f"- {account}: ${amount:,.2f}\n"

        response = await self.glm.chat.completions.create(
            model=settings.glm_model,
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a financial analyst and tax strategist. Analyze the provided "
                        "financial data and generate: 1) 2-3 specific, actionable tax optimization "
                        "tips tied to actual line items in the data. 2) 1-2 anomalies or notable "
                        "trends. Max 150 words. Reference actual accounts/amounts."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Analyze this financial data and provide insights:\n\n{summary}",
                },
            ],
        )
        return response.choices[0].message.content or ""

