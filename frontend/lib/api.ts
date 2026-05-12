/**
 * API client — wraps fetch with Supabase session token + FastAPI base URL.
 */

import { createClient } from "@/utils/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getToken(): Promise<string | null> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = await getToken();

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });


  return res;
}

export async function getProfile() {
  const res = await apiFetch("/api/users/me");
  if (!res.ok) throw new Error("Failed to fetch profile");
  return res.json();
}

export async function updateProfile(data: any) {
  const res = await apiFetch("/api/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update profile");
  return res.json();
}

export async function getFiles(skip = 0, limit = 100) {
  const res = await apiFetch(`/api/files?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch files");
  return res.json();
}

export async function getRecentFiles(limit = 10) {
  const res = await apiFetch(`/api/files/recent?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch recent files");
  return res.json();
}

export async function uploadFile(formData: FormData) {
  const token = await getToken();
  const res = await fetch(`${API_URL}/api/files/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to upload file");
  return res.json();
}

export async function deleteFile(fileId: string) {
  const res = await apiFetch(`/api/files/${fileId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete file");
  return res.json();
}

export async function getReports(skip = 0, limit = 50) {
  const res = await apiFetch(`/api/reports?skip=${skip}&limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch reports");
  return res.json();
}

export async function generateReport() {
  const res = await apiFetch("/api/reports/generate", { method: "POST" });
  if (!res.ok) throw new Error("Failed to generate report");
  return res.json();
}

export async function downloadReport(reportId: string) {
  const res = await apiFetch(`/api/reports/${reportId}/download`);
  if (!res.ok) throw new Error("Failed to download report");
  return res.blob();
}

export async function getPermissions(tenantId: string) {
  const res = await apiFetch(`/api/permissions/tenant/${tenantId}`);
  if (!res.ok) throw new Error("Failed to fetch permissions");
  return res.json();
}

export async function inviteUser(email: string, role: string, tenantId: string) {
  const res = await apiFetch("/api/permissions/invite", {
    method: "POST",
    body: JSON.stringify({ email, role, tenant_id: tenantId }),
  });
  if (!res.ok) throw new Error("Failed to invite user");
  return res.json();
}

export async function revokePermission(permissionId: string) {
  const res = await apiFetch(`/api/permissions/${permissionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to revoke permission");
  return res.json();
}

export async function getIntegrationStatus(tenantId: string) {
  const res = await apiFetch(`/api/integrations/${tenantId}/status`);
  if (!res.ok) throw new Error("Failed to fetch integration status");
  return res.json();
}

export async function getQuickBooksAuthUrl(tenantId: string) {
  const res = await apiFetch(`/api/integrations/${tenantId}/quickbooks/connect`);
  if (!res.ok) throw new Error("Failed to get QuickBooks auth URL");
  return res.json();
}

export async function connectShopify(
  tenantId: string,
  data: { store_domain: string; api_key: string; api_secret: string }
) {
  const res = await apiFetch(`/api/integrations/${tenantId}/shopify/connect`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to connect Shopify");
  return res.json();
}

export async function connectPayPal(
  tenantId: string,
  data: { client_id: string; client_secret: string; sandbox: boolean }
) {
  const res = await apiFetch(`/api/integrations/${tenantId}/paypal/connect`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to connect PayPal");
  return res.json();
}

export async function connectStripe(tenantId: string, data: { api_key: string }) {
  const res = await apiFetch(`/api/integrations/${tenantId}/stripe/connect`, {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to connect Stripe");
  return res.json();
}

export async function getFlaggedItems(tenantId: string, flagStatus?: string) {
  const qs = flagStatus ? `?status=${flagStatus}` : "";
  const res = await apiFetch(`/api/flagged/${tenantId}${qs}`);
  if (!res.ok) throw new Error("Failed to fetch flagged items");
  return res.json();
}

export async function getFlaggedSummary(tenantId: string) {
  const res = await apiFetch(`/api/flagged/${tenantId}/summary`);
  if (!res.ok) throw new Error("Failed to fetch flagged summary");
  return res.json();
}

export async function reviewFlaggedItem(
  itemId: string,
  data: { status: "approved" | "rejected" | "corrected"; note?: string }
) {
  const res = await apiFetch(`/api/flagged/${itemId}/review`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to review flagged item");
  return res.json();
}
