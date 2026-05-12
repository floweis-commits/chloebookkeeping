"""
Month-end scheduler — orchestrates the full bookkeeping workflow.

Timeline each month:
  Last day of month, 6 AM:
    1. Pull data from all connected sources (QB, Shopify, PayPal, Stripe)
    2. Categorize uncategorized transactions
    3. Reconcile processor transactions against QB
    4. Create/update Report record with status=pending_review
    5. Email Chloe with flagged item count + review link

  When Chloe clears all flagged items (via /review UI):
    → Report status flips to "ready"
    → PDF auto-generates
    → Status → "generated"
    → Email Chloe that report is ready (she can deliver to client)
"""

import calendar
from datetime import datetime, date, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from backend.config import settings
from backend.db.database import async_session as AsyncSessionLocal
from backend.db.models import (
    Report, FlaggedItem, QuickBooksConnection,
    ShopifyConnection, PayPalConnection, StripeConnection,
)
from backend.connectors.quickbooks import get_quickbooks_connector
from backend.connectors.shopify import get_shopify_connector_for_tenant
from backend.connectors.paypal import get_paypal_connector_for_tenant
from backend.connectors.stripe import get_stripe_connector_for_tenant
from backend.agents.categorizer import CategorizerAgent
from backend.agents.reconciler import ReconcilerAgent
from backend.services.email import send_review_reminder, send_report_ready

scheduler = AsyncIOScheduler(timezone="America/Denver")

BOOKKEEPER_EMAIL = "chloe@channeledbychloe.com"
BOOKKEEPER_NAME = "Chloe"
COMPANY_NAME = "Channeled by Chloe LLC"


def _last_day_of_month(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _period_label(period_end: date) -> str:
    return period_end.strftime("%B %Y")


async def run_month_end_for_tenant(tenant_id: str, period_start: date, period_end: date) -> None:
    """
    Full month-end pipeline for one tenant.
    Called by the scheduler on the last day of each month.
    """
    async with AsyncSessionLocal() as db:
        start_str = period_start.isoformat()
        end_str = period_end.isoformat()
        period_label = _period_label(period_end)

        # ── 1. Pull data ───────────────────────────────────────
        sync_data: dict[str, Any] = {"errors": []}
        qb_txns: list = []
        shopify_txns: list = []
        paypal_txns: list = []
        stripe_txns: list = []

        qb_row = await db.execute(
            select(QuickBooksConnection).where(QuickBooksConnection.tenant_id == tenant_id)
        )
        qb_conn = qb_row.scalar_one_or_none()
        if qb_conn and qb_conn.is_active:
            try:
                qb = get_quickbooks_connector()
                token = await qb.get_access_token_for_tenant(db, tenant_id)
                qb_txns = await qb.get_transactions(token, qb_conn.realm_id, start_str, end_str)
                sync_data["quickbooks"] = {"transactions": qb_txns}
            except Exception as e:
                sync_data["errors"].append(f"QuickBooks: {e}")

        for connector_fn, txns_list, key in [
            (get_shopify_connector_for_tenant, shopify_txns, "shopify"),
            (get_paypal_connector_for_tenant, paypal_txns, "paypal"),
            (get_stripe_connector_for_tenant, stripe_txns, "stripe"),
        ]:
            try:
                conn = await connector_fn(db, tenant_id)
                txns = await conn.get_transactions(start_str, end_str)
                txns_list.extend(txns)
                sync_data[key] = {"transactions": txns}
            except ValueError:
                pass  # not connected
            except Exception as e:
                sync_data["errors"].append(f"{key}: {e}")

        # ── 2. Categorize ──────────────────────────────────────
        all_processor_txns = shopify_txns + paypal_txns + stripe_txns
        categorized = []
        if all_processor_txns:
            try:
                cat = CategorizerAgent()
                categorized = await cat.categorize_batch(all_processor_txns)
            except Exception as e:
                sync_data["errors"].append(f"Categorizer: {e}")

        # ── 3. Reconcile ───────────────────────────────────────
        flagged_items: list[dict] = []
        if qb_txns:
            rec = ReconcilerAgent()
            recon = rec.reconcile_all_sources(
                qb_transactions=qb_txns,
                shopify_transactions=shopify_txns or None,
                paypal_transactions=paypal_txns or None,
                stripe_transactions=stripe_txns or None,
                period_start=start_str,
                period_end=end_str,
            )
            flagged_items = rec.to_flagged_items(recon)

        # Also flag low-confidence categorizations
        for cat_result in categorized:
            if cat_result.flagged:
                flagged_items.append({
                    "source": "categorizer",
                    "type": "low_confidence",
                    "description": cat_result.flag_reason or f"Low-confidence category: {cat_result.category}",
                    "amount": str(cat_result.original.get("amount", "")),
                    "transaction_id": cat_result.transaction_id,
                    "raw": cat_result.original,
                })

        # ── 4. Persist report + flagged items ──────────────────
        report = Report(
            tenant_id=tenant_id,
            title=f"Management Report — {period_label}",
            period_start=datetime.combine(period_start, datetime.min.time()),
            period_end=datetime.combine(period_end, datetime.min.time()),
            client_name=COMPANY_NAME,
            bookkeeper_name=BOOKKEEPER_NAME,
            data=sync_data,
            status="pending_review" if flagged_items else "ready",
            flagged_count=len(flagged_items),
            reviewed_count=0,
        )
        db.add(report)
        await db.flush()  # get report.id

        for item in flagged_items:
            db.add(FlaggedItem(
                tenant_id=tenant_id,
                source=item["source"],
                type=item["type"],
                description=item["description"],
                amount=str(item.get("amount", "")),
                transaction_id=item.get("transaction_id"),
                raw=item.get("raw"),
                status="pending",
            ))

        await db.commit()

        # ── 5. Email Chloe ─────────────────────────────────────
        if flagged_items:
            await send_review_reminder(
                to=BOOKKEEPER_EMAIL,
                period_label=period_label,
                flagged_count=len(flagged_items),
                app_url=settings.app_url,
            )
            report.reminder_sent_at = datetime.utcnow()
            await db.commit()
        else:
            # No items to review — go straight to generation
            await trigger_report_generation(str(report.id))

        print(f"[scheduler] Month-end complete for {period_label}: "
              f"{len(flagged_items)} flagged items, report={report.id}")


async def trigger_report_generation(report_id: str) -> None:
    """
    Called when all flagged items are cleared.
    Generates the PDF and marks the report as generated.
    """
    from backend.agents.report_generator import ReportGeneratorAgent

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if report is None:
            return

        try:
            agent = ReportGeneratorAgent()
            output = await agent.generate_report(
                db=db,
                tenant_id=report.tenant_id,
                period_start=report.period_start,
                period_end=report.period_end,
                client_name=report.client_name or COMPANY_NAME,
                bookkeeper_name=report.bookkeeper_name or BOOKKEEPER_NAME,
            )

            # Save PDF to storage
            import os
            pdf_dir = settings.storage_local_path
            os.makedirs(pdf_dir, exist_ok=True)
            pdf_path = os.path.join(pdf_dir, f"report_{report_id}.pdf")
            with open(pdf_path, "wb") as f:
                f.write(output["pdf_bytes"])

            report.file_path = pdf_path
            report.status = "generated"
            report.generated_at = datetime.utcnow()
            await db.commit()

            # Notify Chloe
            period_label = _period_label(report.period_end.date())
            await send_report_ready(
                to=BOOKKEEPER_EMAIL,
                period_label=period_label,
                client_name=report.client_name or COMPANY_NAME,
                app_url=settings.app_url,
            )

        except Exception as e:
            print(f"[scheduler] Report generation failed for {report_id}: {e}")


async def _month_end_job() -> None:
    """Scheduler entry point — runs daily at 6 AM, exits early if not month-end."""
    today = date.today()
    if today != _last_day_of_month(today.year, today.month):
        return  # not the last day of the month

    period_end = today
    period_start = today.replace(day=1)

    # Get all active tenants that have at least one connected integration
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(QuickBooksConnection).where(QuickBooksConnection.is_active == True))  # noqa: E712
        connections = result.scalars().all()

    for conn in connections:
        await run_month_end_for_tenant(
            tenant_id=str(conn.tenant_id),
            period_start=period_start,
            period_end=period_end,
        )


def start_scheduler() -> None:
    """Register all jobs and start the scheduler. Called at app startup."""
    # Last day of every month at 6:00 AM Mountain Time
    # "last day" = day 28-31 AND it's the last day of the month
    # Simplest reliable pattern: run daily, check if today is last day
    scheduler.add_job(
        _month_end_job,
        CronTrigger(hour=6, minute=0),  # runs daily at 6 AM; job self-checks if it's month-end
        id="month_end_pipeline",
        replace_existing=True,
    )
    scheduler.start()
    print("[scheduler] Started — month-end pipeline runs daily at 6 AM MT (self-checks for last day)")


async def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
