"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import ShopifyConnectModal from "@/components/ShopifyConnectModal";
import PayPalConnectModal from "@/components/PayPalConnectModal";
import StripeConnectModal from "@/components/StripeConnectModal";
import { getIntegrationStatus, getQuickBooksAuthUrl } from "@/lib/api";
import { getSupabaseUser } from "@/lib/auth";
import { useToast } from "@/components/Toast";
import { CheckCircle2, Circle, AlertCircle, ExternalLink, RefreshCw } from "lucide-react";

type ConnectionState = "disconnected" | "connected" | "error" | "loading";

interface IntegrationStatus {
  quickbooks: { connected: boolean; realm_id?: string; token_expires_at?: string };
  shopify: { connected: boolean; store_domain?: string };
  paypal: { connected: boolean; sandbox?: boolean };
  stripe: { connected: boolean };
}

function StatusBadge({ state }: { state: ConnectionState }) {
  if (state === "loading") {
    return (
      <span className="flex items-center gap-1.5 text-xs text-gray-400">
        <RefreshCw size={12} className="animate-spin" />
        Checking…
      </span>
    );
  }
  if (state === "connected") {
    return (
      <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600">
        <CheckCircle2 size={14} />
        Connected
      </span>
    );
  }
  if (state === "error") {
    return (
      <span className="flex items-center gap-1.5 text-xs font-medium text-red-500">
        <AlertCircle size={14} />
        Error
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1.5 text-xs text-gray-400">
      <Circle size={14} />
      Not connected
    </span>
  );
}

interface IntegrationCardProps {
  logo: React.ReactNode;
  name: string;
  description: string;
  state: ConnectionState;
  meta?: string;
  onConnect: () => void;
  connectLabel?: string;
}

function IntegrationCard({ logo, name, description, state, meta, onConnect, connectLabel = "Connect" }: IntegrationCardProps) {
  return (
    <div className="flex items-start justify-between rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-gray-100 bg-gray-50 text-xl">
          {logo}
        </div>
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <h3 className="text-sm font-semibold text-gray-800">{name}</h3>
            <StatusBadge state={state} />
          </div>
          <p className="text-xs text-gray-500 max-w-xs">{description}</p>
          {meta && state === "connected" && (
            <p className="mt-1 text-xs text-gray-400">{meta}</p>
          )}
        </div>
      </div>

      <div className="ml-4 shrink-0">
        {state === "connected" ? (
          <button
            onClick={onConnect}
            className="rounded-md border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Reconnect
          </button>
        ) : (
          <button
            onClick={onConnect}
            disabled={state === "loading"}
            className="flex items-center gap-1.5 rounded-md bg-blush-400 px-4 py-1.5 text-xs font-medium text-white hover:bg-blush-500 disabled:bg-gray-200 disabled:cursor-not-allowed transition-colors"
          >
            {connectLabel}
            <ExternalLink size={12} />
          </button>
        )}
      </div>
    </div>
  );
}

export default function IntegrationsPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [qbState, setQbState] = useState<ConnectionState>("loading");
  const [shopifyState, setShopifyState] = useState<ConnectionState>("loading");
  const [paypalState, setPaypalState] = useState<ConnectionState>("loading");
  const [stripeState, setStripeState] = useState<ConnectionState>("loading");
  const [shopifyOpen, setShopifyOpen] = useState(false);
  const [paypalOpen, setPaypalOpen] = useState(false);
  const [stripeOpen, setStripeOpen] = useState(false);
  const { addToast } = useToast();

  const refreshStatus = async (uid: string) => {
    try {
      const s: IntegrationStatus = await getIntegrationStatus(uid);
      setStatus(s);
      setQbState(s.quickbooks.connected ? "connected" : "disconnected");
      setShopifyState(s.shopify.connected ? "connected" : "disconnected");
      setPaypalState(s.paypal.connected ? "connected" : "disconnected");
      setStripeState(s.stripe.connected ? "connected" : "disconnected");
    } catch {
      setQbState("disconnected");
      setShopifyState("disconnected");
      setPaypalState("disconnected");
      setStripeState("disconnected");
    }
  };

  useEffect(() => {
    getSupabaseUser().then(async (u) => {
      if (!u) return;
      setUserId(u.id);
      refreshStatus(u.id);
    });
  }, []);

  const handleQBConnect = async () => {
    if (!userId) return;
    try {
      const { authorization_url } = await getQuickBooksAuthUrl(userId);
      window.location.href = authorization_url;
    } catch {
      addToast("error", "Failed to start QuickBooks authorization");
    }
  };

  const handleSuccess = (source: string) => {
    addToast("success", `${source} connected`);
    if (userId) refreshStatus(userId);
  };

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-800">Integrations</h1>
        <p className="mt-1 text-sm text-gray-500">
          Connect your data sources to power automated reports.
        </p>
      </div>

      <div className="space-y-3 max-w-2xl">
        <IntegrationCard
          logo={<span>💼</span>}
          name="QuickBooks Online"
          description="Sync your chart of accounts, P&L, and transaction history. Required for monthly management reports."
          state={qbState}
          meta={status?.quickbooks.realm_id ? `Realm: ${status.quickbooks.realm_id}` : undefined}
          onConnect={handleQBConnect}
          connectLabel="Authorize with QB"
        />

        <IntegrationCard
          logo={<span>🛍️</span>}
          name="Shopify"
          description="Pull sales, payouts, and fee data to reconcile e-commerce revenue in your reports."
          state={shopifyState}
          meta={status?.shopify.store_domain ? `Store: ${status.shopify.store_domain}` : undefined}
          onConnect={() => setShopifyOpen(true)}
          connectLabel="Connect store"
        />

        <IntegrationCard
          logo={<span>💳</span>}
          name="PayPal"
          description="Import PayPal transactions and fees for reconciliation against QuickBooks entries."
          state={paypalState}
          meta={status?.paypal.sandbox ? "Sandbox mode" : undefined}
          onConnect={() => setPaypalOpen(true)}
          connectLabel="Connect PayPal"
        />

        <IntegrationCard
          logo={<span>⚡</span>}
          name="Stripe"
          description="Sync Stripe charges, payouts, and processing fees for automatic categorization."
          state={stripeState}
          onConnect={() => setStripeOpen(true)}
          connectLabel="Connect Stripe"
        />
      </div>

      {/* Future integrations */}
      <div className="mt-8 max-w-2xl">
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-gray-400">Coming soon</p>
        <div className="space-y-3 opacity-50 pointer-events-none">
          <div className="flex items-center gap-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 p-5">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-gray-200 bg-white text-xl">
              <span>📦</span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Amazon Seller Central</p>
              <p className="text-xs text-gray-400">Sales and settlement reports</p>
            </div>
          </div>
          <div className="flex items-center gap-4 rounded-xl border border-dashed border-gray-200 bg-gray-50 p-5">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-gray-200 bg-white text-xl">
              <span>🏦</span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">Bank Feed</p>
              <p className="text-xs text-gray-400">Direct bank transaction import</p>
            </div>
          </div>
        </div>
      </div>

      {userId && (
        <>
          <ShopifyConnectModal
            isOpen={shopifyOpen}
            tenantId={userId}
            onClose={() => setShopifyOpen(false)}
            onSuccess={() => handleSuccess("Shopify")}
          />
          <PayPalConnectModal
            isOpen={paypalOpen}
            tenantId={userId}
            onClose={() => setPaypalOpen(false)}
            onSuccess={() => handleSuccess("PayPal")}
          />
          <StripeConnectModal
            isOpen={stripeOpen}
            tenantId={userId}
            onClose={() => setStripeOpen(false)}
            onSuccess={() => handleSuccess("Stripe")}
          />
        </>
      )}
    </AppShell>
  );
}
