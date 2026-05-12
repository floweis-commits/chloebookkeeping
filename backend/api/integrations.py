"""
API endpoints for managing integrations (QuickBooks, Shopify).
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_user, get_db, require_role
from backend.connectors.quickbooks import QuickBooksConnector, get_quickbooks_connector
from backend.connectors.shopify import get_shopify_connector_for_tenant
from backend.connectors.paypal import get_paypal_connector_for_tenant
from backend.connectors.stripe import get_stripe_connector_for_tenant
from backend.agents.reconciler import ReconcilerAgent
from backend.db.models import (
    QuickBooksConnection, ShopifyConnection,
    PayPalConnection, StripeConnection,
    FlaggedItem, Report, User,
)

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


# ─────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────

class ShopifyConnectRequest(BaseModel):
    api_key: str
    api_secret: str
    store_domain: str  # e.g. "store.myshopify.com"


class PayPalConnectRequest(BaseModel):
    client_id: str
    client_secret: str
    sandbox: bool = False


class StripeConnectRequest(BaseModel):
    api_key: str  # sk_live_... or sk_test_...


# ─────────────────────────────────────────────────────────────────────
# QuickBooks Endpoints
# ─────────────────────────────────────────────────────────────────────

@router.get("/{client_id}/quickbooks/connect")
async def quickbooks_connect(
    client_id: str,
    _: User = Depends(require_role("bookkeeper")),
) -> Dict[str, str]:
    """Return the QB OAuth authorization URL. Bookkeeper only."""
    qb = get_quickbooks_connector()
    # State token embeds tenant_id so the callback can store tokens
    auth_url = qb.get_authorization_url(tenant_id=client_id)
    return {
        "authorization_url": auth_url,
        "message": "Redirect user to this URL to authorize QuickBooks access",
    }


@router.get("/quickbooks/callback")
async def quickbooks_callback(
    code: str,
    realmId: str,
    state: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Handle QuickBooks OAuth callback. Validates state, stores tokens."""
    qb = get_quickbooks_connector()

    # Validate state and recover tenant_id (one-time use)
    tenant_id = qb.pop_tenant_from_state(state)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    try:
        tokens = await qb.exchange_code_for_tokens(code, realmId)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"QB token exchange failed: {e}")

    token_expires_at = datetime.utcnow() + timedelta(
        seconds=tokens.get("expires_in", 3600)
    )

    # Upsert connection record
    existing = await db.execute(
        select(QuickBooksConnection).where(QuickBooksConnection.tenant_id == tenant_id)
    )
    connection = existing.scalar_one_or_none()

    if connection:
        connection.access_token = tokens["access_token"]
        connection.refresh_token = tokens["refresh_token"]
        connection.realm_id = realmId
        connection.token_expires_at = token_expires_at
    else:
        connection = QuickBooksConnection(
            tenant_id=tenant_id,
            realm_id=realmId,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_expires_at=token_expires_at,
        )
        db.add(connection)

    await db.commit()

    return {
        "status": "success",
        "message": "QuickBooks connected successfully",
        "realm_id": realmId,
    }


# ─────────────────────────────────────────────────────────────────────
# Shopify Endpoints
# ─────────────────────────────────────────────────────────────────────

@router.post("/{client_id}/shopify/connect")
async def shopify_connect(
    client_id: str,
    body: ShopifyConnectRequest,
    _: User = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Store Shopify API credentials for a tenant. Bookkeeper only.

    Credentials are accepted in the request body (never query params)
    to avoid leaking secrets into server logs and browser history.
    """
    existing = await db.execute(
        select(ShopifyConnection).where(ShopifyConnection.tenant_id == client_id)
    )
    connection = existing.scalar_one_or_none()

    if connection:
        connection.api_key = body.api_key
        connection.api_secret = body.api_secret
        connection.store_domain = body.store_domain
    else:
        connection = ShopifyConnection(
            tenant_id=client_id,
            api_key=body.api_key,
            api_secret=body.api_secret,
            store_domain=body.store_domain,
        )
        db.add(connection)

    await db.commit()
    return {"status": "success", "message": f"Shopify store {body.store_domain} connected"}


# ─────────────────────────────────────────────────────────────────────
# Data Sync Endpoint
# ─────────────────────────────────────────────────────────────────────

@router.post("/{client_id}/sync")
async def manual_sync(
    client_id: str,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    current_user: User = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Trigger manual data sync from QuickBooks and Shopify. Bookkeeper only.

    Stores raw API results in Report.data (JSONB) for later use by
    the report generator agent.
    """
    sync_results: Dict[str, Any] = {
        "quickbooks": None,
        "shopify": None,
        "errors": [],
    }

    # ── QuickBooks ─────────────────────────────────────────
    qb_result = await db.execute(
        select(QuickBooksConnection).where(QuickBooksConnection.tenant_id == client_id)
    )
    qb_conn = qb_result.scalar_one_or_none()

    if qb_conn:
        try:
            qb = get_quickbooks_connector()
            access_token = await qb.get_access_token_for_tenant(db, client_id)
            sync_results["quickbooks"] = {
                "transactions": await qb.get_transactions(
                    access_token, qb_conn.realm_id, start_date, end_date
                ),
                "chart_of_accounts": await qb.get_chart_of_accounts(
                    access_token, qb_conn.realm_id
                ),
            }
        except Exception as e:
            sync_results["errors"].append(f"QuickBooks sync failed: {e}")
    else:
        sync_results["errors"].append("QuickBooks not connected for this tenant")

    # ── Shopify ────────────────────────────────────────────
    shopify_txns = None
    try:
        shopify_connector = await get_shopify_connector_for_tenant(db, client_id)
        shopify_data = {
            "sales": await shopify_connector.get_sales(start_date, end_date),
            "payouts": await shopify_connector.get_payouts(start_date, end_date),
            "fees": await shopify_connector.get_fees(start_date, end_date),
        }
        sync_results["shopify"] = shopify_data
        shopify_txns = shopify_data["sales"]
    except ValueError:
        sync_results["errors"].append("Shopify not connected for this tenant")
    except Exception as e:
        sync_results["errors"].append(f"Shopify sync failed: {e}")

    # ── PayPal ─────────────────────────────────────────────
    paypal_txns = None
    try:
        paypal_connector = await get_paypal_connector_for_tenant(db, client_id)
        paypal_data = {
            "transactions": await paypal_connector.get_transactions(start_date, end_date),
            "payouts": await paypal_connector.get_payouts(start_date, end_date),
            "fees": await paypal_connector.get_fees(start_date, end_date),
        }
        sync_results["paypal"] = paypal_data
        paypal_txns = paypal_data["transactions"]
    except ValueError:
        sync_results["errors"].append("PayPal not connected for this tenant")
    except Exception as e:
        sync_results["errors"].append(f"PayPal sync failed: {e}")

    # ── Stripe ─────────────────────────────────────────────
    stripe_txns = None
    try:
        stripe_connector = await get_stripe_connector_for_tenant(db, client_id)
        stripe_data = {
            "transactions": await stripe_connector.get_transactions(start_date, end_date),
            "payouts": await stripe_connector.get_payouts(start_date, end_date),
            "fees": await stripe_connector.get_fees(start_date, end_date),
        }
        sync_results["stripe"] = stripe_data
        stripe_txns = stripe_data["transactions"]
    except ValueError:
        sync_results["errors"].append("Stripe not connected for this tenant")
    except Exception as e:
        sync_results["errors"].append(f"Stripe sync failed: {e}")

    # ── Reconciliation ─────────────────────────────────────
    qb_txns = (sync_results.get("quickbooks") or {}).get("transactions", [])
    if qb_txns:
        reconciler = ReconcilerAgent()
        recon_results = reconciler.reconcile_all_sources(
            qb_transactions=qb_txns,
            shopify_transactions=shopify_txns,
            paypal_transactions=paypal_txns,
            stripe_transactions=stripe_txns,
            period_start=start_date,
            period_end=end_date,
        )
        flagged_dicts = reconciler.to_flagged_items(recon_results)
        for item in flagged_dicts:
            db.add(FlaggedItem(
                tenant_id=client_id,
                source=item["source"],
                type=item["type"],
                description=item["description"],
                amount=str(item.get("amount", "")),
                transaction_id=item.get("transaction_id"),
                raw=item.get("raw"),
                status="pending",
            ))
        sync_results["reconciliation"] = {
            source: r.summary for source, r in recon_results.items()
        }

    # ── Persist raw data ───────────────────────────────────
    report = Report(
        tenant_id=client_id,
        title=f"Data Sync {start_date} to {end_date}",
        period_start=datetime.strptime(start_date, "%Y-%m-%d"),
        period_end=datetime.strptime(end_date, "%Y-%m-%d"),
        data=sync_results,
    )
    db.add(report)
    await db.commit()

    return {
        "status": "success",
        "report_id": str(report.id),
        "sync_results": sync_results,
    }


# ─────────────────────────────────────────────────────────────────────
# Status Endpoint
# ─────────────────────────────────────────────────────────────────────

@router.get("/{client_id}/status")
async def integration_status(
    client_id: str,
    _: User = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get connection status for all integrations for a tenant."""
    result: Dict[str, Any] = {
        "quickbooks": {"connected": False},
        "shopify": {"connected": False},
        "paypal": {"connected": False},
        "stripe": {"connected": False},
    }

    qb_result = await db.execute(
        select(QuickBooksConnection).where(QuickBooksConnection.tenant_id == client_id)
    )
    qb_conn = qb_result.scalar_one_or_none()
    if qb_conn and qb_conn.is_active:
        result["quickbooks"] = {
            "connected": True,
            "realm_id": qb_conn.realm_id,
            "token_expires_at": qb_conn.token_expires_at.isoformat(),
        }

    shopify_result = await db.execute(
        select(ShopifyConnection).where(ShopifyConnection.tenant_id == client_id)
    )
    shopify_conn = shopify_result.scalar_one_or_none()
    if shopify_conn and shopify_conn.is_active:
        result["shopify"] = {"connected": True, "store_domain": shopify_conn.store_domain}

    paypal_result = await db.execute(
        select(PayPalConnection).where(PayPalConnection.tenant_id == client_id)
    )
    paypal_conn = paypal_result.scalar_one_or_none()
    if paypal_conn and paypal_conn.is_active:
        result["paypal"] = {"connected": True, "sandbox": paypal_conn.sandbox}

    stripe_result = await db.execute(
        select(StripeConnection).where(StripeConnection.tenant_id == client_id)
    )
    stripe_conn = stripe_result.scalar_one_or_none()
    if stripe_conn and stripe_conn.is_active:
        result["stripe"] = {"connected": True}

    return result


# ─────────────────────────────────────────────────────────────────────
# PayPal + Stripe Connect Endpoints
# ─────────────────────────────────────────────────────────────────────

@router.post("/{client_id}/paypal/connect")
async def paypal_connect(
    client_id: str,
    body: PayPalConnectRequest,
    _: User = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Store PayPal client credentials for a tenant. Bookkeeper only."""
    existing = await db.execute(
        select(PayPalConnection).where(PayPalConnection.tenant_id == client_id)
    )
    connection = existing.scalar_one_or_none()
    if connection:
        connection.client_id = body.client_id
        connection.client_secret = body.client_secret
        connection.sandbox = body.sandbox
    else:
        connection = PayPalConnection(
            tenant_id=client_id,
            client_id=body.client_id,
            client_secret=body.client_secret,
            sandbox=body.sandbox,
        )
        db.add(connection)
    await db.commit()
    mode = "sandbox" if body.sandbox else "live"
    return {"status": "success", "message": f"PayPal connected ({mode})"}


@router.post("/{client_id}/stripe/connect")
async def stripe_connect(
    client_id: str,
    body: StripeConnectRequest,
    _: User = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """Store Stripe API key for a tenant. Bookkeeper only."""
    existing = await db.execute(
        select(StripeConnection).where(StripeConnection.tenant_id == client_id)
    )
    connection = existing.scalar_one_or_none()
    if connection:
        connection.api_key = body.api_key
    else:
        connection = StripeConnection(tenant_id=client_id, api_key=body.api_key)
        db.add(connection)
    await db.commit()
    return {"status": "success", "message": "Stripe connected"}
