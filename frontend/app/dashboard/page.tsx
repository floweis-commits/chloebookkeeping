"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import FileList from "@/components/FileList";
import { getRecentFiles } from "@/lib/api";
import { FileRecord } from "@/lib/types";

export default function DashboardPage() {
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRecentFiles(10)
      .then((res) => setFiles(Array.isArray(res) ? res : res.items || []))
      .catch(() => setFiles([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-semibold text-gray-800">Dashboard</h1>
      </div>
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-700">Recent Files</h2>
          <a
            href="/reports"
            className="rounded-md bg-blush-400 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blush-500"
          >
            Generate New Report
          </a>
        </div>
        <FileList files={files} isLoading={loading} />
      </section>
    </AppShell>
  );
}
