/**
 * TypeScript types for Chloe Bookkeeping API responses
 */

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone?: string;
  timezone: string;
  role: "bookkeeper" | "client";
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  business_name: string;
  business_type?: string;
  created_at: string;
  updated_at: string;
}

export interface FileRecord {
  id: string;
  name: string;
  path: string;
  size: number;
  mime_type: string;
  uploaded_at: string;
  uploaded_by: string;
  is_new?: boolean;
  tenant_id: string;
}

export interface Report {
  id: string;
  period: string;
  status: "pending" | "complete" | "failed";
  generated_at: string;
  file_url?: string;
  tenant_id: string;
}

export interface Permission {
  id: string;
  user_id: string;
  tenant_id: string;
  user_name: string;
  user_email: string;
  role: "bookkeeper" | "client";
  access_level: "read" | "write" | "admin";
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
  tenant: Tenant;
}

export interface RefreshTokenResponse {
  access_token: string;
}

export interface ApiError {
  status: number;
  message: string;
  details?: Record<string, unknown>;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface PaginationParams {
  skip?: number;
  limit?: number;
}
