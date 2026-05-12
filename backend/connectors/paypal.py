"""
PayPal connector — fetches transactions and payouts via PayPal REST API v2.

Auth: Client Credentials OAuth2 (app-level, not user-delegated).
Credentials stored per-tenant in paypal_connections table.
"""

import httpx
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import PayPalConnection


PAYPAL_BASE = "https://api-m.paypal.com"
PAYPAL_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"


class PayPalConnector:
    def __init__(self, client_id: str, client_secret: str, sandbox: bool = False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = PAYPAL_SANDBOX_BASE if sandbox else PAYPAL_BASE
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Fetch a short-lived OAuth2 token using client credentials."""
        if self._access_token:
            return self._access_token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
            return self._access_token

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_transactions(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """
        Fetch PayPal transactions for a date range.

        Args:
            start_date: "YYYY-MM-DD"
            end_date: "YYYY-MM-DD"

        Returns:
            List of normalized transaction dicts with keys:
            id, date, description, amount, currency, type, status
        """
        # PayPal wants ISO 8601 with time
        start_iso = f"{start_date}T00:00:00-0700"
        end_iso = f"{end_date}T23:59:59-0700"

        data = await self._get(
            "/v1/reporting/transactions",
            params={
                "start_date": start_iso,
                "end_date": end_iso,
                "fields": "all",
                "page_size": 500,
            },
        )

        transactions = []
        for item in data.get("transaction_details", []):
            info = item.get("transaction_info", {})
            amount_obj = info.get("transaction_amount", {})
            transactions.append({
                "id": info.get("transaction_id", ""),
                "date": info.get("transaction_initiation_date", "")[:10],
                "description": info.get("transaction_subject") or info.get("transaction_note") or "PayPal transaction",
                "amount": float(amount_obj.get("value", 0)),
                "currency": amount_obj.get("currency_code", "USD"),
                "type": info.get("transaction_event_code", ""),
                "status": info.get("transaction_status", ""),
                "source": "paypal",
            })

        return transactions

    async def get_payouts(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Fetch PayPal balance transfers (payouts to bank)."""
        data = await self._get(
            "/v1/reporting/transactions",
            params={
                "start_date": f"{start_date}T00:00:00-0700",
                "end_date": f"{end_date}T23:59:59-0700",
                "transaction_type": "T0400",  # PayPal to bank transfer
                "fields": "all",
                "page_size": 100,
            },
        )
        payouts = []
        for item in data.get("transaction_details", []):
            info = item.get("transaction_info", {})
            amount_obj = info.get("transaction_amount", {})
            payouts.append({
                "id": info.get("transaction_id", ""),
                "date": info.get("transaction_initiation_date", "")[:10],
                "amount": abs(float(amount_obj.get("value", 0))),
                "currency": amount_obj.get("currency_code", "USD"),
                "source": "paypal",
                "type": "payout",
            })
        return payouts

    async def get_fees(
        self, start_date: str, end_date: str
    ) -> dict[str, float]:
        """Summarize total PayPal fees for the period."""
        data = await self._get(
            "/v1/reporting/transactions",
            params={
                "start_date": f"{start_date}T00:00:00-0700",
                "end_date": f"{end_date}T23:59:59-0700",
                "fields": "all",
                "page_size": 500,
            },
        )
        total_fees = 0.0
        for item in data.get("transaction_details", []):
            info = item.get("transaction_info", {})
            fee_obj = info.get("fee_amount", {})
            total_fees += abs(float(fee_obj.get("value", 0)))

        return {"total_fees": total_fees, "currency": "USD"}


async def get_paypal_connector_for_tenant(
    db: AsyncSession, tenant_id: str
) -> "PayPalConnector":
    result = await db.execute(
        select(PayPalConnection).where(
            PayPalConnection.tenant_id == tenant_id,
            PayPalConnection.is_active == True,  # noqa: E712
        )
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        raise ValueError(f"No active PayPal connection for tenant {tenant_id}")
    return PayPalConnector(
        client_id=conn.client_id,
        client_secret=conn.client_secret,
        sandbox=conn.sandbox,
    )
