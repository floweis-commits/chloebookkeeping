"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import ReportList from "@/components/ReportList";
import { getReports, generateReport, downloadReport } from "@/lib/api";
import { getSupabaseUser, getUserRole } from "@/lib/auth";
import { useToast } from "@/components/Toast";
import { Report } from "@/lib/types";

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [role, setRole] = useState("client");
  const { addToast } = useToast();

  useEffect(() => {
    getSupabaseUser().then((u) => setRole(getUserRole(u)));
    getReports(0, 50)
      .then((res) => setReports(Array.isArray(res) ? res : res.items || []))
      .catch(() => setReports([]))
      .finally(() => setLoading(false));
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const newReport = await generateReport();
      setReports([newReport, ...reports]);
      addToast("success", "Report generation started");
    } catch {
      addToast("error", "Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (reportId: string) => {
    try {
      const blob = await downloadReport(reportId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${reportId}.pdf`;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
      addToast("success", "Report downloaded");
    } catch {
      addToast("error", "Failed to download report");
    }
  };

  const canGenerate = role === "bookkeeper";

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Reports</h1>
        {canGenerate && (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="rounded-md bg-blush-400 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blush-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            {generating ? "Generating..." : "Generate New Report"}
          </button>
        )}
      </div>
      <ReportList reports={reports} onDownload={handleDownload} isLoading={loading} />
    </AppShell>
  );
}
