"""
Integration tests for report generation pipeline.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db.models import Tenant, User, Report, QuickBooksConnection
from backend.agents.report_generator import ReportGeneratorAgent
from backend.pdf.report_builder import ReportBuilder


@pytest.fixture
async def test_db():
    """Create an in-memory test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create test tenant
        tenant = Tenant(id=uuid4(), name="Test Client")
        session.add(tenant)
        await session.commit()

    yield async_session, engine

    await engine.dispose()


@pytest.mark.asyncio
async def test_report_generator_basic(test_db):
    """Test basic report generation with mock data."""
    async_session, engine = test_db

    async with async_session() as db:
        # Get test tenant
        from sqlalchemy import select
        result = await db.execute(select(Tenant))
        tenant = result.scalar_one()

        agent = ReportGeneratorAgent()

        # Generate report with mock data
        report_result = await agent.generate_report(
            db=db,
            tenant_id=tenant.id,
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
            client_name="Test Client",
            bookkeeper_name="Test Bookkeeper",
        )

        assert 'pdf_bytes' in report_result
        assert report_result['pdf_bytes']
        assert len(report_result['pdf_bytes']) > 1000  # PDF should be substantial
        assert 'report_data' in report_result
        assert report_result['report_data']['client_name'] == "Test Client"


def test_report_builder_with_sample_data():
    """Test PDF report builder with sample financial data."""
    context = {
        'client_name': 'Acme Corporation',
        'bookkeeper_name': 'Jane Smith',
        'period_start': datetime(2024, 1, 1),
        'period_end': datetime(2024, 1, 31),
        'balance_sheet': {
            'Cash': 25000.00,
            'Accounts Receivable': 15000.00,
            'Equipment': 50000.00,
            'Accounts Payable': -10000.00,
            'Loan Payable': -30000.00,
            'Owner Equity': 50000.00,
        },
        'pl_current_month': {
            'PayPal Sales': 20000.00,
            'Sales': 45000.00,
            'Sales of Product Income': 12000.00,
            'Total Income': 77000.00,
            'Car & Truck Fuel': 350.00,
            'Contractors': 3000.00,
            'Insurance': 1500.00,
            'Office Supplies & Software': 400.00,
            'Payroll Expenses': 18000.00,
            'Travel': 600.00,
            'Vet Expenses': 1500.00,
        },
        'pl_by_month': [
            {
                'month': 'Jan 2024',
                'data': {
                    'PayPal Sales': 20000.00,
                    'Sales': 45000.00,
                    'Total Income': 65000.00,
                    'Expenses': -15000.00,
                }
            },
        ],
        'kpis': {
            'Total Income': 77000.00,
            'Total Expenses': 25350.00,
            'Net Income': 51650.00,
            'Gross Margin %': 95.5,
            'Net Profit Margin %': 67.1,
            'Return on Assets %': 45.2,
            'Return on Equity %': 103.3,
        },
        'pl_monthly_comparison': {
            'Total Income': {
                'this_month': 77000.00,
                'last_month': 68000.00,
            },
            'Payroll Expenses': {
                'this_month': 18000.00,
                'last_month': 17000.00,
            },
        },
        'pl_ytd_comparison': {
            'Total Income': {
                'this_year': 77000.00,
                'last_year': 65000.00,
            },
        },
        'ai_insights': 'Cash position is strong with $25k on hand. Payroll expenses are trending up (5.9% month-over-month). Consider reviewing contractor spending relative to payroll efficiency. PayPal and direct sales channels showing healthy growth vs prior year.',
        'logo_path': None,
    }

    builder = ReportBuilder(context)
    pdf_bytes = builder.build()

    # Verify PDF generation
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000

    # PDF should start with %PDF magic bytes
    assert pdf_bytes.startswith(b'%PDF')


def test_kpi_calculation():
    """Test KPI calculation logic."""
    agent = ReportGeneratorAgent()

    balance_sheet = {
        'Cash': 50000,
        'Assets': 150000,
        'Liabilities': -50000,
        'Equity': 100000,
    }

    pl = {
        'Income': 100000,
        'Total Income': 100000,
        'Expenses': -30000,
    }

    kpis = agent._calculate_kpis(balance_sheet, pl)

    assert kpis['Total Income'] == 100000
    assert kpis['Net Income'] > 0
    assert 'Gross Margin %' in kpis
    assert 'Net Profit Margin %' in kpis
    assert 'Return on Assets %' in kpis
    assert 'Return on Equity %' in kpis


def test_currency_formatting():
    """Test currency formatting utility."""
    builder = ReportBuilder({})

    assert builder._format_currency(1234.56) == "$1,234.56"
    assert builder._format_currency(1000000.00) == "$1,000,000.00"
    assert builder._format_currency(0) == "$0.00"
    assert builder._format_currency(-500) == "$-500.00"


def test_percentage_formatting():
    """Test percentage formatting utility."""
    builder = ReportBuilder({})

    assert builder._format_percentage(50.0) == "50.0%"
    assert builder._format_percentage(33.333) == "33.3%"
    assert builder._format_percentage(0) == "0.0%"
    assert builder._format_percentage(-10.5) == "-10.5%"


def test_report_generator_categories():
    """Verify income and expense categories match requirements."""
    agent = ReportGeneratorAgent()

    # Check income categories
    expected_income = {
        "PayPal Sales",
        "Sales",
        "Sales of Product Income",
        "Total Income",
    }
    assert agent.INCOME_CATEGORIES == expected_income

    # Check expense categories
    assert "Car & Truck" in agent.EXPENSE_CATEGORIES
    assert "Fuel" in agent.EXPENSE_CATEGORIES["Car & Truck"]
    assert "Payroll Expenses" in agent.EXPENSE_CATEGORIES
    assert "Officer Wages" in agent.EXPENSE_CATEGORIES["Payroll Expenses"]
    assert "Vet Expenses" in agent.EXPENSE_CATEGORIES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
