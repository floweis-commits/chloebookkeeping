"use client";

import { useState } from "react";
import { X, Mail } from "lucide-react";
import { inviteUser } from "@/lib/api";
import { getSupabaseUser } from "@/lib/auth";
import { useToast } from "./Toast";

interface InviteUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function InviteUserModal({ isOpen, onClose, onSuccess }: InviteUserModalProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("client");
  const [loading, setLoading] = useState(false);
  const { addToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    try {
      const user = await getSupabaseUser();
      await inviteUser(email, role, user?.id ?? "");
      addToast("success", `Invitation sent to ${email}`);
      setEmail("");
      setRole("client");
      onClose();
      onSuccess?.();
    } catch {
      addToast("error", "Failed to send invitation");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">Invite User</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Email Address</label>
            <div className="relative">
              <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
                required
                className="w-full rounded-md border border-gray-300 pl-10 pr-3 py-2 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400"
              />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400"
            >
              <option value="client">Client</option>
              <option value="bookkeeper">Bookkeeper</option>
            </select>
          </div>

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
              disabled={!email || loading}
              className="flex-1 rounded-md bg-blush-400 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blush-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loading ? "Sending..." : "Send Invitation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
