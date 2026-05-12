"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import { getFlaggedItems, getFlaggedSummary, reviewFlaggedItem } from "@/lib/api";
import { getSupabaseUser } from "@/lib/auth";
import { useToast } from "@/components/Toast";
import {
  CheckCircle2, XCircle, AlertTriangle, RotateCcw,
  ChevronDown, ChevronUp, Loader2,
} from "lucide-react";

interface FlaggedItem {
  id: string;
  source: string;
  type: string;
  description: string;
  amount: string | null;
  transaction_id: string | null;
  status: string;
  note: string | null;
  created_at: string;
}

interface Summary { pending: number; approved: number; rejected: number; corrected: number }

const SOURCE_LABELS: Record<string, string> = {
  quickbooks: "QuickBooks",
  shopify: "Shopify",
  paypal: "PayPal",
  stripe: "Stripe",
  categorizer: "AI Categorizer",
};

const TYPE_LABELS: Record<string, string> = {
  unmatched_processor: "No QB match",
  unmatched_qb: "No processor match",
  amount_mismatch: "Amount mismatch",
  low_confidence: "Low confidence",
};

function SourceBadge({ source }: { source: string }) {
  const colors: Record<string, string> = {
    quickbooks: "bg-green-100 text-green-700",
    shopify: "bg-emerald-100 text-emerald-700",
    paypal: "bg-blue-100 text-blue-700",
    stripe: "bg-purple-100 text-purple-700",
    categorizer: "bg-amber-100 text-amber-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[source] ?? "bg-gray-100 text-gray-600"}`}>
      {SOURCE_LABELS[source] ?? source}
    </span>
  );
}

function FlaggedCard({
  item,
  onReview,
}: {
  item: FlaggedItem;
  onReview: (id: string, status: "approved" | "rejected", note?: string) => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(false);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState<"approved" | "rejected" | null>(null);

  if (item.status !== "pending") return null;

  const handle = async (decision: "approved" | "rejected") => {
    setLoading(decision);
    await onReview(item.id, decision, note || undefined);
    setLoading(null);
  };

  return (
    <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <SourceBadge source={item.source} />
              <span className="text-xs text-gray-400">{TYPE_LABELS[item.type] ?? item.type}</span>
              {item.amount && (
                <span className="text-xs font-mono font-medium text-gray-700">
                  ${Math.abs(parseFloat(item.amount)).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-700">{item.description}</p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => handle("approved")}
              disabled={!!loading}
              className="flex items-center gap-1 rounded-md bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-50 transition-colors"
            >
              {loading === "approved" ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={13} />}
              Approve
            </button>
            <button
              onClick={() => handle("rejected")}
              disabled={!!loading}
              className="flex items-center gap-1 rounded-md bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-50 transition-colors"
            >
              {loading === "rejected" ? <Loader2 size={12} className="animate-spin" /> : <XCircle size={13} />}
              Reject
            </button>
            <button
              onClick={() => setExpanded(!expanded)}
              className="rounded-md p-1.5 text-gray-400 hover:bg-gray-50 transition-colors"
            >
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>
        </div>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Note (optional — shown in audit log)
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="e.g. Confirmed with client, duplicate entry removed…"
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-xs outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400 resize-none"
            />
            {item.transaction_id && (
              <p className="mt-1 text-xs text-gray-400 font-mono">ID: {item.transaction_id}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ReviewPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [items, setItems] = useState<FlaggedItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const { addToast } = useToast();

  const load = async (uid: string) => {
    try {
      const [itemData, sumData] = await Promise.all([
        getFlaggedItems(uid, "pending"),
        getFlaggedSummary(uid),
      ]);
      setItems(itemData);
      setSummary(sumData);
    } catch {
      addToast("error", "Failed to load review queue");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getSupabaseUser().then((u) => {
      if (!u) return;
      setUserId(u.id);
      load(u.id);
    });
  }, []);

  const handleReview = async (id: string, status: "approved" | "rejected", note?: string) => {
    try {
      const result = await reviewFlaggedItem(id, { status, note });
      setItems((prev) => prev.filter((i) => i.id !== id));
      setSummary((prev) => prev ? { ...prev, pending: prev.pending - 1, [status]: prev[status] + 1 } : prev);

      if (result.queue_cleared) {
        addToast("success", "All items reviewed — report is being generated!");
      } else {
        addToast("success", status === "approved" ? "Approved" : "Rejected");
      }
    } catch {
      addToast("error", "Failed to submit review");
    }
  };

  const pendingCount = items.filter((i) => i.status === "pending").length;

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Review Queue</h1>
        <p className="mt-1 text-sm text-gray-500">
          Approve or reject flagged transactions before the monthly report is generated.
        </p>
      </div>

      {/* Summary bar */}
      {summary && (
        <div className="mb-6 grid grid-cols-4 gap-3 max-w-2xl">
          {[
            { label: "Pending", value: summary.pending, color: "text-amber-600 bg-amber-50" },
            { label: "Approved", value: summary.approved, color: "text-emerald-600 bg-emerald-50" },
            { label: "Rejected", value: summary.rejected, color: "text-red-600 bg-red-50" },
            { label: "Corrected", value: summary.corrected, color: "text-blue-600 bg-blue-50" },
          ].map(({ label, value, color }) => (
            <div key={label} className={`rounded-xl p-4 ${color.split(" ")[1]}`}>
              <div className={`text-2xl font-bold ${color.split(" ")[0]}`}>{value}</div>
              <div className="text-xs text-gray-500 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-400 mt-8">
          <Loader2 size={16} className="animate-spin" /> Loading…
        </div>
      ) : pendingCount === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center max-w-sm mx-auto">
          <div className="rounded-full bg-emerald-50 p-4 mb-4">
            <CheckCircle2 size={32} className="text-emerald-500" />
          </div>
          <h3 className="text-base font-medium text-gray-700">Queue is clear</h3>
          <p className="mt-1 text-sm text-gray-400">
            No pending items. The report will generate automatically once all items are reviewed.
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-w-2xl">
          <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 rounded-lg px-4 py-2.5 mb-4">
            <AlertTriangle size={15} />
            <span><strong>{pendingCount}</strong> item{pendingCount !== 1 ? "s" : ""} need your review before the report can be generated</span>
          </div>
          {items.map((item) => (
            <FlaggedCard key={item.id} item={item} onReview={handleReview} />
          ))}
        </div>
      )}
    </AppShell>
  );
}
