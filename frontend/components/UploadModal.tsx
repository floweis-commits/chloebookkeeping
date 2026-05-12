"use client";

import { useState } from "react";
import { Upload, X } from "lucide-react";
import { uploadFile } from "@/lib/api";
import { useToast } from "./Toast";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function UploadModal({
  isOpen,
  onClose,
  onSuccess,
}: UploadModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const { addToast } = useToast();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) return;

    setUploading(true);
    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);
        await uploadFile(formData);
      }
      addToast("success", `${files.length} file(s) uploaded successfully`);
      setFiles([]);
      onClose();
      onSuccess?.();
    } catch (error) {
      addToast("error", "Failed to upload files");
    } finally {
      setUploading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">Upload Files</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-lg border-2 border-dashed border-blush-300 bg-blush-50 p-6 text-center hover:border-blush-400 transition-colors cursor-pointer">
            <input
              type="file"
              multiple
              onChange={handleFileChange}
              className="hidden"
              id="file-input"
            />
            <label
              htmlFor="file-input"
              className="flex flex-col items-center gap-2 cursor-pointer"
            >
              <Upload size={32} className="text-blush-400" />
              <span className="text-sm font-medium text-gray-700">
                Click to upload or drag and drop
              </span>
              <span className="text-xs text-gray-500">
                PDF, DOC, XLSX up to 50MB
              </span>
            </label>
          </div>

          {files.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700">
                Selected files ({files.length}):
              </p>
              <ul className="space-y-1">
                {files.map((file) => (
                  <li key={file.name} className="text-sm text-gray-600">
                    • {file.name}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={files.length === 0 || uploading}
              className="flex-1 rounded-md bg-blush-400 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blush-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {uploading ? "Uploading..." : "Upload"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
