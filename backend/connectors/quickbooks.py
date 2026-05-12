"""
QuickBooks Online API connector.

Handles OAuth2 flow, token refresh, and data pulls:
- Balance Sheet
- Profit & Loss
- Transactions (General Ledger)
- Chart of Accounts
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import QuickBooksConnection, Tenant

# In-memory state store: state_token → tenant_id
# Entries expire after use. For multi-process deployments, swap for Redis.
_oauth_state_store: dict[str, str] = {}


class QuickBooksConnector:
    """Handles QuickBooks Online API interactions."""

    def __init__(self, client_id: str = None, client_secret: str = None,
                 environment: str = "sandbox"):
        """Initialize QuickBooks connector.

        Args:
            client_id: OAuth2 client ID (defaults to env var)
            client_secret: OAuth2 client secret (defaults to env var)
            environment: "sandbox" or "production"
        """
        self.client_id = client_id or os.getenv("QBO_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("QBO_CLIENT_SECRET")
        self.redirect_uri = os.getenv("QBO_REDIRECT_URI")
        self.environment = environment

        # QB uses the same base URL for sandbox and production;
        # the realm_id (company ID) distinguishes sandbox vs real companies.
        self.auth_url = "https://appcenter.intuit.com/connect/oauth2"
        self.api_base = "https://quickbooks.api.intuit.com"

    def get_authorization_url(self, tenant_id: str) -> str:
        """Generate QuickBooks OAuth2 authorization URL.

        Embeds tenant_id in a random state token so the callback knows
        which tenant is completing the connection.
        """
        state = secrets.token_urlsafe(32)
        _oauth_state_store[state] = tenant_id

        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "com.intuit.quickbooks.accounting",
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return f"{self.auth_url}?{urlencode(params)}"

    def pop_tenant_from_state(self, state: str) -> str | None:
        """Validate state and return the associated tenant_id (one-time use)."""
        return _oauth_state_store.pop(state, None)

    async def exchange_code_for_tokens(self, auth_code: str, realm_id: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens.

        Args:
            auth_code: Authorization code from OAuth callback
            realm_id: QuickBooks realm (company) ID

        Returns:
            Dict with access_token, refresh_token, expires_in
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth.platform.intuit.com/oauth2/tokens/bearer",
                data={
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "redirect_uri": self.redirect_uri,
                },
                auth=(self.client_id, self.client_secret),
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token.

        Args:
            refresh_token: Refresh token from previous auth

        Returns:
            Dict with new access_token, refresh_token, expires_in
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth.platform.intuit.com/oauth2/tokens/bearer",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                auth=(self.client_id, self.client_secret),
            )
            response.raise_for_status()
            return response.json()

    async def get_access_token_for_tenant(
        self, db: AsyncSession, tenant_id: str
    ) -> str:
        """Get valid access token, refreshing if needed.

        Args:
            db: Database session
            tenant_id: Tenant UUID

        Returns:
            Valid access token
        """
        result = await db.execute(
            select(QuickBooksConnection).where(
                QuickBooksConnection.tenant_id == tenant_id
            )
        )
        connection = result.scalar_one_or_none()

        if not connection:
            raise ValueError(f"No QuickBooks connection for tenant {tenant_id}")

        # Check if token is expired
        if connection.token_expires_at <= datetime.utcnow():
            # Refresh token
            tokens = await self.refresh_access_token(connection.refresh_token)
            connection.access_token = tokens["access_token"]
            connection.refresh_token = tokens["refresh_token"]
            connection.token_expires_at = datetime.utcnow() + timedelta(
                seconds=tokens["expires_in"]
            )
            await db.commit()

        return connection.access_token

    async def _api_call(
        self,
        access_token: str,
        realm_id: str,
        method: str = "GET",
        endpoint: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Make authenticated API call to QuickBooks.

        Args:
            access_token: OAuth access token
            realm_id: QuickBooks realm ID
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional args passed to httpx

        Returns:
            JSON response from API
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        url = f"{self.api_base}/v3/company/{realm_id}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method, url, headers=headers, **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def get_balance_sheet(
        self,
        access_token: str,
        realm_id: str,
        as_of_date: str,  # Format: "2024-12-31"
    ) -> Dict[str, Any]:
        """Get Balance Sheet report for a specific date.

        Args:
            access_token: OAuth access token
            realm_id: QuickBooks realm ID
            as_of_date: Date in YYYY-MM-DD format

        Returns:
            Structured Balance Sheet data
        """
        # QB Reports API uses query string params, not SQL syntax.
        # The /query endpoint uses SQL; /reports/* uses date params.
        return await self._api_call(
            access_token, realm_id, endpoint="/reports/BalanceSheet",
            params={"date_macro": "Custom", "start_date": as_of_date, "end_date": as_of_date}
        )

    async def get_profit_and_loss(
        self,
        access_token: str,
        realm_id: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """Get Profit & Loss report for a date range.

        Args:
            access_token: OAuth access token
            realm_id: QuickBooks realm ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Structured P&L data
        """
        params = {
            "start_date": start_date,
            "end_date": end_date,
        }
        return await self._api_call(
            access_token,
            realm_id,
            endpoint="/reports/ProfitAndLoss",
            params=params
        )

    async def get_transactions(
        self,
        access_token: str,
        realm_id: str,
        start_date: str,
        end_date: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get transactions (Journal Entries) for a date range.

        Args:
            access_token: OAuth access token
            realm_id: QuickBooks realm ID
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Max transactions to return

        Returns:
            List of transaction objects
        """
        # QB uses JournalEntry for general ledger transactions
        query = (
            f"select * from JournalEntry "
            f"where TxnDate >= '{start_date}' and TxnDate <= '{end_date}' "
            f"maxresults {limit}"
        )

        response = await self._api_call(
            access_token,
            realm_id,
            endpoint="/query",
            params={"query": query}
        )

        return response.get("QueryResponse", {}).get("JournalEntry", [])

    async def get_chart_of_accounts(
        self,
        access_token: str,
        realm_id: str,
    ) -> List[Dict[str, Any]]:
        """Get Chart of Accounts.

        Args:
            access_token: OAuth access token
            realm_id: QuickBooks realm ID

        Returns:
            List of account objects
        """
        query = "select * from Account"

        response = await self._api_call(
            access_token,
            realm_id,
            endpoint="/query",
            params={"query": query}
        )

        return response.get("QueryResponse", {}).get("Account", [])


# Singleton instance
_qb_connector: Optional[QuickBooksConnector] = None


def get_quickbooks_connector() -> QuickBooksConnector:
    """Get or create QuickBooks connector instance."""
    global _qb_connector
    if _qb_connector is None:
        _qb_connector = QuickBooksConnector()
    return _qb_connector
