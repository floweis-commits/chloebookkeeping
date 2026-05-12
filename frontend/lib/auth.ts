/**
 * Auth helpers — Supabase-backed.
 * Role is stored in user_metadata when creating users via Supabase dashboard
 * or admin SDK: { role: "bookkeeper" | "client" | "accountant" }
 */

import { createClient } from "@/utils/supabase/client";

export async function getSupabaseUser() {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}

export async function getSupabaseSession() {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session;
}

export async function signOut() {
  const supabase = createClient();
  await supabase.auth.signOut();
  window.location.href = "/login";
}

/** Returns the role stored in Supabase user_metadata, defaulting to "client" */
export function getUserRole(user: any): string {
  return user?.user_metadata?.role ?? "client";
}

// ── Legacy shims — keep so nothing else breaks during migration ──
export const getAccessToken = (): string | null => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
};
export const clearTokens = (): void => {
  if (typeof window === "undefined") return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
  localStorage.removeItem("tenant");
};
export const getStoredUser = () => null;
export const getStoredTenant = () => null;
