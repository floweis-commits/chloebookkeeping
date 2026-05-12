"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { connectPayPal } from "@/lib/api";

interface Props {
  isOpen: boolean;
  tenantId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function PayPalConnectModal({ isOpen, tenantId, onClose, onSuccess }: Props) {
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [sandbox, setSandbox] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await connectPayPal(tenantId, {
        client_id: clientId.trim(),
        client_secret: clientSecret.trim(),
        sandbox,
      });
      onSuccess();
      onClose();
    } catch {
      setError("Failed to connect. Check your credentials and try again.");
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
            <span className="text-xl">💳</span>
            <h2 className="text-base font-semibold text-gray-800">Connect PayPal</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <p className="mb-4 text-xs text-gray-500">
          Enter your PayPal app credentials from the{" "}
          <span className="font-medium">PayPal Developer Dashboard</span> →{" "}
          My Apps &amp; Credentials. Requires Transaction Search permission.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Client ID</label>
            <input
              type="text"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              required
              placeholder="AaBbCcDd…"
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm font-mono outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Client Secret</label>
            <input
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              required
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm font-mono outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={sandbox}
              onChange={(e) => setSandbox(e.target.checked)}
              className="rounded border-gray-300 text-blush-400 focus:ring-blush-400"
            />
            <span className="text-xs text-gray-600">Use sandbox (testing)</span>
          </label>

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex gap-3 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 rounded-md bg-blush-400 py-2 text-sm font-medium text-white hover:bg-blush-500 disabled:bg-gray-200 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? "Connecting…" : "Connect PayPal"}
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
