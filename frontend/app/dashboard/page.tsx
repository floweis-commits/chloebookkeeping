"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AppShell from "@/components/AppShell";
import FileList from "@/components/FileList";
import { getRecentFiles, getFlaggedSummary } from "@/lib/api";
import { getSupabaseUser } from "@/lib/auth";
import { useUser } from "@/components/UserProvider";
import { FileRecord } from "@/lib/types";
import { AlertTriangle, CheckCircle2, Clock, FileText, ArrowRight } from "lucide-react";

type WorkflowStatus = "idle" | "pending_review" | "ready" | "generated";

interface MonthEndCardProps {
  pendingCount: number;
  status: WorkflowStatus;
}

function MonthEndCard({ pendingCount, status }: MonthEndCardProps) {
  const thisMonth = new Date().toLocaleString("en-US", { month: "long", year: "numeric" });

  if (status === "idle") {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-3 mb-2">
          <div className="rounded-full bg-gray-100 p-2">
            <Clock size={16} className="text-gray-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700">{thisMonth} Report</p>
            <p className="text-xs text-gray-400">Scheduled for end of month</p>
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-3">
          Data will be pulled automatically on the last day of the month.
        </p>
      </div>
    );
  }

  if (status === "pending_review") {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-amber-100 p-2">
              <AlertTriangle size={16} className="text-amber-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-amber-800">{thisMonth} — Action needed</p>
              <p className="text-xs text-amber-600">
                <strong>{pendingCount}</strong> item{pendingCount !== 1 ? "s" : ""} need review before the report can generate
              </p>
            </div>
          </div>
          <Link
            href="/review"
            className="flex items-center gap-1 rounded-md bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600 transition-colors"
          >
            Review <ArrowRight size={12} />
          </Link>
        </div>
        <div className="mt-3 h-1.5 rounded-full bg-amber-200 overflow-hidden">
          <div className="h-full bg-amber-500 rounded-full" style={{ width: "30%" }} />
        </div>
        <p className="text-xs text-amber-500 mt-1">Step 2 of 4 — Awaiting review</p>
      </div>
    );
  }

  if (status === "ready") {
    return (
      <div className="rounded-xl border border-blue-200 bg-blue-50 p-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-blue-100 p-2">
            <FileText size={16} className="text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-blue-800">{thisMonth} — Generating report…</p>
            <p className="text-xs text-blue-500">All items reviewed. PDF is being built.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-emerald-100 p-2">
            <CheckCircle2 size={16} className="text-emerald-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-emerald-800">{thisMonth} — Report ready</p>
            <p className="text-xs text-emerald-600">Management report generated and ready to deliver</p>
          </div>
        </div>
        <Link
          href="/reports"
          className="flex items-center gap-1 rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 transition-colors"
        >
          View <ArrowRight size={12} />
        </Link>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { role } = useUser();
  const [userId, setUserId] = useState<string | null>(null);
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [filesLoading, setFilesLoading] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus>("idle");

  useEffect(() => {
    getSupabaseUser().then((u) => {
      if (!u) return;
      setUserId(u.id);

      if (u.user_metadata?.role === "bookkeeper") {
        getFlaggedSummary(u.id)
          .then((s) => {
            setPendingCount(s.pending ?? 0);
            if (s.pending > 0) setWorkflowStatus("pending_review");
          })
          .catch(() => {});
      }
    });

    getRecentFiles(10)
      .then((res) => setFiles(Array.isArray(res) ? res : res.items || []))
      .catch(() => setFiles([]))
      .finally(() => setFilesLoading(false));
  }, []);

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold text-gray-800">Dashboard</h1>
      </div>

      {/* Month-end workflow card — bookkeeper only */}
      {role === "bookkeeper" && (
        <section className="mb-8">
          <h2 className="text-sm font-medium uppercase tracking-wide text-gray-400 mb-3">
            Month-end Status
          </h2>
          <MonthEndCard pendingCount={pendingCount} status={workflowStatus} />
        </section>
      )}

      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-700">Recent Files</h2>
          {role === "bookkeeper" && (
            <Link
              href="/reports"
              className="rounded-md bg-blush-400 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blush-500"
            >
              View Reports
            </Link>
          )}
        </div>
        <FileList files={files} isLoading={filesLoading} />
      </section>
    </AppShell>
  );
}
