"""
Shopify API connector.

Pulls order and payment data for reconciliation against QuickBooks records.
Handles:
- Sales by payment processor
- Payouts and fees
- Fee breakdown by processor
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime

import httpx
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import ShopifyConnection


class ShopifyConnector:
    """Handles Shopify API interactions."""

    def __init__(self, api_key: str = None, api_secret: str = None,
                 store_domain: str = None, encryption_key: str = None):
        """Initialize Shopify connector.

        Args:
            api_key: Shopify API key
            api_secret: Shopify API secret
            store_domain: Store domain (e.g., store.myshopify.com)
            encryption_key: Key for encrypting/decrypting credentials
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.store_domain = store_domain or os.getenv("SHOPIFY_STORE_DOMAIN")
        self.encryption_key = encryption_key or os.getenv("SHOPIFY_ENCRYPTION_KEY")

        # API base URL
        self.api_url = f"https://{self.store_domain}/admin/api/2024-01"

    def _get_auth_header(self) -> Dict[str, str]:
        """Generate Authorization header for API calls."""
        return {
            "X-Shopify-Access-Token": self.api_key,
            "Content-Type": "application/json",
        }

    async def _api_call(
        self,
        method: str = "GET",
        endpoint: str = "",
        **kwargs
    ) -> tuple[Dict[str, Any], Dict[str, str]]:
        """Make authenticated API call to Shopify.

        Returns:
            (json_body, response_headers) — headers needed for Link-based pagination.
        """
        headers = self._get_auth_header()
        url = f"{self.api_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, url, headers=headers, **kwargs
            )
            response.raise_for_status()
            return response.json(), dict(response.headers)

    async def get_sales(
        self,
        start_date: str,
        end_date: str,
    ) -> Dict[str, float]:
        """Get total sales by payment processor for a date range.

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Dict with sales totals by processor:
            {
                "PayPal Sales": 1000.00,
                "Sales": 5000.00,
                "Sales of Product Income": 3000.00,
            }
        """
        orders = await self._get_orders(start_date, end_date)

        sales_by_processor = {
            "PayPal Sales": 0.0,
            "Sales": 0.0,
            "Sales of Product Income": 0.0,
        }

        for order in orders:
            total = float(order.get("total_price", 0))
            payment_gateway = self._identify_payment_processor(order)

            if payment_gateway == "paypal":
                sales_by_processor["PayPal Sales"] += total
            else:
                # Default to generic sales
                sales_by_processor["Sales"] += total
                # Also track product income
                sales_by_processor["Sales of Product Income"] += total

        return sales_by_processor

    async def get_payouts(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """Get payout transactions with fee breakdowns.

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            List of payout objects with fee data:
            [
                {
                    "id": "payout_123",
                    "date": "2024-01-15",
                    "amount": 5000.00,
                    "status": "completed",
                    "currency": "USD",
                    "fees": {...}
                }
            ]
        """
        endpoint = "/payouts.json"
        params = {
            "status": "completed",
            "created_at_min": start_date,
            "created_at_max": end_date,
        }

        try:
            body, _ = await self._api_call(
                method="GET",
                endpoint=endpoint,
                params=params,
            )
            payouts = body.get("payouts", [])

            for payout in payouts:
                payout["fees"] = await self._get_payout_fees(payout["id"])

            return payouts
        except Exception as e:
            # Payouts endpoint only available for Shopify Balance accounts
            print(f"Error fetching payouts: {e}")
            return []

    async def get_fees(
        self,
        start_date: str,
        end_date: str,
    ) -> Dict[str, float]:
        """Get total fees by processor for a date range.

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            Dict with fees by processor:
            {
                "PayPal Fees": 250.00,
                "QuickBooks Payments Fees": 150.00,
                "Shopify Fees": 100.00,
                "Stripe Fees": 75.00,
            }
        """
        # Get all transactions in date range
        transactions = await self._get_transactions(start_date, end_date)

        fees_by_processor = {
            "PayPal Fees": 0.0,
            "QuickBooks Payments Fees": 0.0,
            "Shopify Fees": 0.0,
            "Stripe Fees": 0.0,
        }

        for transaction in transactions:
            # Extract fee information
            fee_amount = float(transaction.get("fee", 0))
            processor = self._identify_payment_processor(transaction)

            if processor == "paypal":
                fees_by_processor["PayPal Fees"] += fee_amount
            elif processor == "quickbooks":
                fees_by_processor["QuickBooks Payments Fees"] += fee_amount
            elif processor == "stripe":
                fees_by_processor["Stripe Fees"] += fee_amount
            else:
                # Default Shopify fees
                fees_by_processor["Shopify Fees"] += fee_amount

        return fees_by_processor

    async def _get_orders(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """Get all orders in a date range, handling Shopify Link-header pagination."""
        params = {
            "created_at_min": start_date,
            "created_at_max": end_date,
            "status": "any",
            "limit": 250,
        }

        all_orders: List[Dict[str, Any]] = []
        next_url: str | None = None

        while True:
            if next_url:
                # Paginating — use full URL returned in Link header
                async with httpx.AsyncClient() as client:
                    resp = await client.get(next_url, headers=self._get_auth_header())
                    resp.raise_for_status()
                    body, headers = resp.json(), dict(resp.headers)
            else:
                body, headers = await self._api_call(
                    method="GET", endpoint="/orders.json", params=params
                )

            all_orders.extend(body.get("orders", []))

            # Shopify pagination is in the HTTP Link header, not the body.
            # Format: <url>; rel="next", <url>; rel="previous"
            link_header = headers.get("link", "")
            next_url = None
            for part in link_header.split(","):
                part = part.strip()
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
                    break

            if not next_url:
                break

        return all_orders

    async def _get_transactions(
        self,
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """Get payment transactions for all orders in a date range.

        Shopify has no top-level /transactions.json endpoint.
        Transactions live at /orders/{id}/transactions.json per order.
        We fetch all orders first, then collect their transactions.
        """
        orders = await self._get_orders(start_date, end_date)
        all_transactions: List[Dict[str, Any]] = []

        for order in orders:
            order_id = order.get("id")
            if not order_id:
                continue
            try:
                body, _ = await self._api_call(
                    method="GET",
                    endpoint=f"/orders/{order_id}/transactions.json",
                )
                txns = body.get("transactions", [])
                # Tag each transaction with its gateway for processor identification
                for t in txns:
                    t.setdefault("gateway", order.get("payment_gateway", ""))
                all_transactions.extend(txns)
            except Exception as e:
                print(f"Error fetching transactions for order {order_id}: {e}")

        return all_transactions

    async def _get_payout_fees(self, payout_id: str) -> Dict[str, Any]:
        """Get fee breakdown for a specific payout.

        Args:
            payout_id: Payout ID

        Returns:
            Dict with fee details
        """
        endpoint = f"/payouts/{payout_id}/transactions.json"

        try:
            body, _ = await self._api_call(
                method="GET",
                endpoint=endpoint,
            )
            transactions = body.get("transactions", [])

            # Aggregate fees
            fees = {
                "paypal_fees": 0.0,
                "stripe_fees": 0.0,
                "shopify_fees": 0.0,
                "total": 0.0,
            }

            for txn in transactions:
                fee_amount = float(txn.get("fee", 0))
                processor = self._identify_payment_processor(txn)

                if processor == "paypal":
                    fees["paypal_fees"] += fee_amount
                elif processor == "stripe":
                    fees["stripe_fees"] += fee_amount
                else:
                    fees["shopify_fees"] += fee_amount

                fees["total"] += fee_amount

            return fees
        except Exception as e:
            print(f"Error fetching payout fees for {payout_id}: {e}")
            return {"paypal_fees": 0.0, "stripe_fees": 0.0, "shopify_fees": 0.0, "total": 0.0}

    def _identify_payment_processor(self, transaction: Dict[str, Any]) -> str:
        """Identify which payment processor handled a transaction.

        Args:
            transaction: Transaction or order object

        Returns:
            Processor name: "paypal", "stripe", "quickbooks", or "shopify"
        """
        # Check various fields that might indicate processor
        gateway = transaction.get("gateway", "").lower()
        source_name = transaction.get("source_name", "").lower()

        if "paypal" in gateway or "paypal" in source_name:
            return "paypal"
        elif "stripe" in gateway or "stripe" in source_name:
            return "stripe"
        elif "quickbooks" in gateway or "qbo" in gateway:
            return "quickbooks"
        else:
            return "shopify"


async def get_shopify_connector_for_tenant(
    db: AsyncSession,
    tenant_id: str,
) -> ShopifyConnector:
    """Get Shopify connector for a tenant, loading credentials from DB.

    Args:
        db: Database session
        tenant_id: Tenant UUID

    Returns:
        Initialized ShopifyConnector
    """
    result = await db.execute(
        select(ShopifyConnection).where(
            ShopifyConnection.tenant_id == tenant_id
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise ValueError(f"No Shopify connection for tenant {tenant_id}")

    # TODO: Decrypt credentials if using encryption
    return ShopifyConnector(
        api_key=connection.api_key,
        api_secret=connection.api_secret,
        store_domain=connection.store_domain,
    )
