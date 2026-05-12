"use client";

import { FileText, Download, Clock, CheckCircle, AlertCircle } from "lucide-react";
import { Report } from "@/lib/types";
import { formatDate } from "@/lib/utils";

interface ReportListProps {
  reports: Report[];
  onDownload?: (reportId: string) => void;
  isLoading?: boolean;
}

export default function ReportList({
  reports,
  onDownload,
  isLoading = false,
}: ReportListProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "complete":
        return (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700">
            <CheckCircle size={14} />
            Complete
          </div>
        );
      case "pending":
        return (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
            <Clock size={14} />
            Pending
          </div>
        );
      case "failed":
        return (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">
            <AlertCircle size={14} />
            Failed
          </div>
        );
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="animate-pulse rounded-lg border border-gray-100 bg-white px-4 py-4 shadow-sm"
          >
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 py-12 text-center">
        <FileText size={40} className="mx-auto mb-3 text-gray-300" />
        <p className="text-gray-500">No reports yet. Generate your first report.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {reports.map((report) => (
        <div
          key={report.id}
          className="flex items-center justify-between rounded-lg border border-gray-100 bg-white px-4 py-4 shadow-sm transition-colors hover:bg-blush-50"
        >
          <div className="flex items-center gap-3 flex-1">
            <FileText size={20} className="text-blush-400 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-700">
                Management Report - {report.period}
              </p>
              <p className="text-xs text-gray-400">
                Generated {formatDate(report.generated_at)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {getStatusBadge(report.status)}
            {report.status === "complete" && (
              <button
                onClick={() => onDownload?.(report.id)}
                className="rounded-md p-2 text-gray-400 transition-colors hover:bg-blush-100 hover:text-blush-600"
                title="Download report"
              >
                <Download size={18} />
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
