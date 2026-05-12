"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import InviteUserModal from "@/components/InviteUserModal";
import { getProfile, updateProfile, getPermissions, revokePermission } from "@/lib/api";
import { getSupabaseUser, getUserRole, signOut } from "@/lib/auth";
import { useToast } from "@/components/Toast";
import { Permission } from "@/lib/types";
import { X } from "lucide-react";

export default function SettingsPage() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [timezone, setTimezone] = useState("America/Chicago");
  const [role, setRole] = useState("client");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [inviteOpen, setInviteOpen] = useState(false);
  const { addToast } = useToast();

  useEffect(() => {
    const load = async () => {
      try {
        const supabaseUser = await getSupabaseUser();
        const userRole = getUserRole(supabaseUser);
        setRole(userRole);
        setEmail(supabaseUser?.email ?? "");

        try {
          const profile = await getProfile();
          setFirstName(profile.first_name ?? "");
          setLastName(profile.last_name ?? "");
          setPhone(profile.phone ?? "");
          setTimezone(profile.timezone ?? "America/Chicago");
        } catch {
          // Backend not running — prefill from Supabase metadata
          const meta = supabaseUser?.user_metadata ?? {};
          setFirstName(meta.first_name ?? "");
          setLastName(meta.last_name ?? "");
        }
      } catch {
        addToast("error", "Failed to load profile");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [addToast]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateProfile({ first_name: firstName, last_name: lastName, phone, timezone });
      addToast("success", "Profile updated");
    } catch {
      addToast("error", "Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  const handleRevoke = async (permissionId: string) => {
    try {
      await revokePermission(permissionId);
      setPermissions(permissions.filter((p) => p.id !== permissionId));
      addToast("success", "Access revoked");
    } catch {
      addToast("error", "Failed to revoke access");
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4" />
          <div className="h-64 bg-gray-200 rounded" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <h1 className="mb-8 text-2xl font-semibold text-gray-800">Settings</h1>

      <section className="mb-8">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">Profile</h2>
        <form onSubmit={handleSave} className="max-w-2xl space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">First name</label>
              <input value={firstName} onChange={(e) => setFirstName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Last name</label>
              <input value={lastName} onChange={(e) => setLastName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400" />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
            <input type="email" value={email} disabled
              className="w-full rounded-md border border-gray-300 bg-gray-100 px-3 py-2 text-sm cursor-not-allowed" />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Phone</label>
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400" />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Timezone</label>
            <select value={timezone} onChange={(e) => setTimezone(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none focus:border-blush-400 focus:ring-1 focus:ring-blush-400">
              <option value="America/New_York">Eastern Time</option>
              <option value="America/Chicago">Central Time</option>
              <option value="America/Denver">Mountain Time</option>
              <option value="America/Los_Angeles">Pacific Time</option>
            </select>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={saving}
              className="rounded-md bg-blush-400 px-6 py-2 text-sm font-medium text-white hover:bg-blush-500 disabled:bg-gray-300 disabled:cursor-not-allowed">
              {saving ? "Saving..." : "Save changes"}
            </button>
            <button type="button" onClick={signOut}
              className="rounded-md border border-gray-300 px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Sign out
            </button>
          </div>
        </form>
      </section>

      {role === "bookkeeper" && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">Manage Access</h2>
            <button onClick={() => setInviteOpen(true)}
              className="rounded-md bg-blush-400 px-4 py-2 text-sm font-medium text-white hover:bg-blush-500">
              Invite User
            </button>
          </div>

          {permissions.length === 0 ? (
            <div className="rounded-lg border-2 border-dashed border-gray-200 bg-gray-50 py-8 text-center">
              <p className="text-gray-500">No users invited yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {permissions.map((perm) => (
                <div key={perm.id} className="flex items-center justify-between rounded-lg border border-gray-100 bg-white px-4 py-3 shadow-sm">
                  <div>
                    <p className="text-sm font-medium text-gray-700">{perm.user_name}</p>
                    <p className="text-xs text-gray-500">{perm.user_email}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700">{perm.role}</span>
                    <button onClick={() => handleRevoke(perm.id)} className="text-gray-400 hover:text-red-600">
                      <X size={18} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <InviteUserModal isOpen={inviteOpen} onClose={() => setInviteOpen(false)}
            onSuccess={() => {}} />
        </section>
      )}
    </AppShell>
  );
}
