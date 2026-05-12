"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { connectStripe } from "@/lib/api";

interface Props {
  isOpen: boolean;
  tenantId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function StripeConnectModal({ isOpen, tenantId, onClose, onSuccess }: Props) {
  const [apiKey, setApiKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await connectStripe(tenantId, { api_key: apiKey.trim() });
      onSuccess();
      onClose();
    } catch {
      setError("Failed to connect. Check your API key and try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <span className="text-xl">⚡</span>
            <h2 className="text-base font-semibold text-gray-800">Connect Stripe</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <p className="mb-4 text-xs text-gray-500">
          Enter your Stripe <span className="font-medium">restricted API key</span> from the Stripe
          Dashboard → Developers → API keys. Needs read access to Charges, Payouts, and Balance transactions.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Secret API key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
              placeholder="sk_live_… or sk_test_…"
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm font-mono outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400"
            />
          </div>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex gap-3 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 rounded-md bg-blush-400 py-2 text-sm font-medium text-white hover:bg-blush-500 disabled:bg-gray-200 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? "Connecting…" : "Connect Stripe"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
