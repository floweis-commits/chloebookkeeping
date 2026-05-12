"""
Stripe connector — fetches charges, payouts, and fees via Stripe API.

Auth: API key (secret key stored per-tenant in stripe_connections table).
Uses stripe-python SDK (async via httpx under the hood).
"""

import httpx
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import StripeConnection


STRIPE_BASE = "https://api.stripe.com/v1"


class StripeConnector:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{STRIPE_BASE}{path}",
                params=params,
                auth=(self.api_key, ""),
            )
            resp.raise_for_status()
            return resp.json()

    def _ts(self, date_str: str, end_of_day: bool = False) -> int:
        """Convert YYYY-MM-DD to Unix timestamp."""
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if end_of_day:
            dt = dt.replace(hour=23, minute=59, second=59)
        return int(dt.timestamp())

    async def get_transactions(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """
        Fetch all Stripe charges (successful) for a date range.

        Returns normalized list with keys:
        id, date, description, amount, currency, type, status, source
        """
        transactions = []
        params = {
            "created[gte]": self._ts(start_date),
            "created[lte]": self._ts(end_date, end_of_day=True),
            "limit": 100,
            "expand[]": "data.customer",
        }
        while True:
            data = await self._get("/charges", params)
            for charge in data.get("data", []):
                if charge.get("status") != "succeeded":
                    continue
                customer = charge.get("customer") or {}
                desc = charge.get("description") or (
                    customer.get("name") if isinstance(customer, dict) else ""
                ) or "Stripe charge"
                transactions.append({
                    "id": charge["id"],
                    "date": self._from_ts(charge["created"]),
                    "description": desc,
                    "amount": charge["amount"] / 100,  # Stripe amounts in cents
                    "currency": charge["currency"].upper(),
                    "type": "charge",
                    "status": charge["status"],
                    "source": "stripe",
                })
            if not data.get("has_more"):
                break
            params["starting_after"] = data["data"][-1]["id"]

        return transactions

    async def get_payouts(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Fetch Stripe payouts (bank transfers) for the period."""
        payouts = []
        params = {
            "arrival_date[gte]": self._ts(start_date),
            "arrival_date[lte]": self._ts(end_date, end_of_day=True),
            "limit": 100,
            "status": "paid",
        }
        while True:
            data = await self._get("/payouts", params)
            for payout in data.get("data", []):
                payouts.append({
                    "id": payout["id"],
                    "date": self._from_ts(payout["arrival_date"]),
                    "amount": payout["amount"] / 100,
                    "currency": payout["currency"].upper(),
                    "source": "stripe",
                    "type": "payout",
                })
            if not data.get("has_more"):
                break
            params["starting_after"] = data["data"][-1]["id"]

        return payouts

    async def get_fees(
        self, start_date: str, end_date: str
    ) -> dict[str, float]:
        """Sum Stripe processing fees from balance transactions."""
        total_fees = 0.0
        params = {
            "created[gte]": self._ts(start_date),
            "created[lte]": self._ts(end_date, end_of_day=True),
            "type": "charge",
            "limit": 100,
        }
        while True:
            data = await self._get("/balance_transactions", params)
            for bt in data.get("data", []):
                total_fees += bt.get("fee", 0) / 100
            if not data.get("has_more"):
                break
            params["starting_after"] = data["data"][-1]["id"]

        return {"total_fees": round(total_fees, 2), "currency": "USD"}

    @staticmethod
    def _from_ts(ts: int) -> str:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


async def get_stripe_connector_for_tenant(
    db: AsyncSession, tenant_id: str
) -> StripeConnector:
    result = await db.execute(
        select(StripeConnection).where(
            StripeConnection.tenant_id == tenant_id,
            StripeConnection.is_active == True,  # noqa: E712
        )
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        raise ValueError(f"No active Stripe connection for tenant {tenant_id}")
    return StripeConnector(api_key=conn.api_key)
