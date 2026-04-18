import { getAccessToken, handleUnauthorizedResponse } from "./auth";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type LookupStatus = "pending" | "processing" | "done" | "failed";

export interface LookupCreatePayload {
  first_name: string;
  last_name: string;
  domain: string;
}

export interface LookupQueueResponse {
  id: string;
  status: LookupStatus;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LookupRecord {
  id: string;
  first_name: string;
  last_name: string;
  domain: string;
  email: string | null;
  confidence: number;
  reason_code: string;
  verifier_calls_used: number;
  status: LookupStatus;
  created_at: string;
  completed_at: string | null;
}

export interface HistoryResponse {
  page: number;
  limit: number;
  total: number;
  items: LookupRecord[];
}

export interface AnalyticsSummary {
  total_lookups: number;
  overall_hit_rate: number;
  credits_used_this_month: number;
}

export interface WeeklyVolumePoint {
  week_start: string;
  lookups: number;
}

export interface DomainHitRatePoint {
  domain: string;
  total_lookups: number;
  hits: number;
  hit_rate: number;
}

export interface WeeklyCreditsPoint {
  week_start: string;
  credits_used: number;
}

interface RequestOptions extends RequestInit {
  query?: Record<string, string | number | undefined | null>;
  auth?: "required" | "none";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin);

  if (options.query) {
    for (const [key, value] of Object.entries(options.query)) {
      if (value === undefined || value === null || value === "") {
        continue;
      }
      url.searchParams.set(key, String(value));
    }
  }

  const headers = new Headers(options.headers);
  if (options.body !== undefined && options.body !== null && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (options.auth !== "none") {
    const accessToken = getAccessToken();
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
  }

  const response = await fetch(url.toString(), {
    ...options,
    headers,
  });

  if (response.status === 401 && options.auth !== "none") {
    handleUnauthorizedResponse();
  }

  if (!response.ok) {
    let message = "Request failed";
    try {
      const errorPayload = await response.json();
      if (typeof errorPayload?.detail === "string") {
        message = errorPayload.detail;
      }
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export function login(password: string) {
  return request<AuthTokenResponse>("/api/auth/token", {
    method: "POST",
    auth: "none",
    body: JSON.stringify({ password }),
  });
}

export function createLookup(payload: LookupCreatePayload) {
  return request<LookupQueueResponse>("/api/lookup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getLookup(lookupId: string) {
  return request<LookupRecord>(`/api/lookup/${lookupId}`);
}

export function getHistory(params: {
  page: number;
  limit: number;
  domain?: string;
  status?: string;
}) {
  return request<HistoryResponse>("/api/history", {
    query: params,
  });
}

export function getAnalyticsSummary() {
  return request<AnalyticsSummary>("/api/analytics/summary");
}

export function getAnalyticsVolume() {
  return request<WeeklyVolumePoint[]>("/api/analytics/volume");
}

export function getAnalyticsDomains() {
  return request<DomainHitRatePoint[]>("/api/analytics/domains");
}

export function getAnalyticsCredits() {
  return request<WeeklyCreditsPoint[]>("/api/analytics/credits");
}
