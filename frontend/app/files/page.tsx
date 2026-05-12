"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import FileList from "@/components/FileList";
import UploadModal from "@/components/UploadModal";
import { Search, Upload } from "lucide-react";
import { getFiles } from "@/lib/api";
import { getSupabaseUser, getUserRole } from "@/lib/auth";
import { FileRecord } from "@/lib/types";

export default function FilesPage() {
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [role, setRole] = useState("client");

  const loadFiles = async () => {
    try {
      const res = await getFiles(0, 100);
      setFiles(Array.isArray(res) ? res : res.items || []);
    } catch {
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getSupabaseUser().then((u) => setRole(getUserRole(u)));
    loadFiles();
  }, []);

  const filtered = files.filter((f) =>
    f.name.toLowerCase().includes(search.toLowerCase())
  );

  const canUpload = role === "bookkeeper" || role === "admin";

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-800">Files</h1>
        {canUpload && (
          <button
            onClick={() => setUploadOpen(true)}
            className="flex items-center gap-2 rounded-md bg-blush-400 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blush-500"
          >
            <Upload size={18} />
            Add a file
          </button>
        )}
      </div>

      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          placeholder="Search files"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400"
        />
      </div>

      <FileList files={filtered} isLoading={loading} />

      <UploadModal
        isOpen={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSuccess={loadFiles}
      />
    </AppShell>
  );
}
