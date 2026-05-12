"use client";

import { useState } from "react";
import { Folder, FileIcon, ChevronRight } from "lucide-react";
import { FileRecord } from "@/lib/types";
import { formatDate, formatFileSize, truncateText } from "@/lib/utils";

interface FileListProps {
  files: FileRecord[];
  onSelectFile?: (file: FileRecord) => void;
  isLoading?: boolean;
}

export default function FileList({
  files,
  onSelectFile,
  isLoading = false,
}: FileListProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggleSelect = (fileId: string) => {
    const newSelected = new Set(selected);
    if (newSelected.has(fileId)) {
      newSelected.delete(fileId);
    } else {
      newSelected.add(fileId);
    }
    setSelected(newSelected);
  };

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="animate-pulse rounded-lg border border-gray-100 bg-white px-4 py-3 shadow-sm"
          >
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 py-12 text-center">
        <FileIcon size={40} className="mx-auto mb-3 text-gray-300" />
        <p className="text-gray-500">No files yet. Start by uploading a file.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {files.map((file) => (
        <div
          key={file.id}
          className="flex items-center justify-between rounded-lg border border-gray-100 bg-white px-4 py-3 shadow-sm transition-colors hover:bg-blush-50"
        >
          <div className="flex items-center gap-3 flex-1">
            <input
              type="checkbox"
              checked={selected.has(file.id)}
              onChange={() => toggleSelect(file.id)}
              className="h-4 w-4 rounded border-gray-300 text-blush-400 cursor-pointer"
            />
            <Folder size={20} className="text-blush-400 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-700 truncate">
                {truncateText(file.name, 50)}
              </p>
              <p className="text-xs text-gray-400">
                {formatDate(file.uploaded_at)} • {formatFileSize(file.size)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            {file.is_new && (
              <span className="inline-flex items-center rounded-full bg-blush-400 px-2.5 py-0.5 text-xs font-medium text-white">
                New
              </span>
            )}
            <ChevronRight size={16} className="text-gray-300" />
          </div>
        </div>
      ))}
    </div>
  );
}
