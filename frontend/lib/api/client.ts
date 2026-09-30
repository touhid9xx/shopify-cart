/**
 * API client — fetch wrapper with:
 *   - Auto JWT injection
 *   - Auto refresh on 401 (single retry)
 *   - Typed errors (ApiError)
 *   - JSON + multipart support
 */

import type { ApiError, TokenPair } from "@/lib/api-types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

// ───── Token storage (sessionStorage — swap with cookie if preferred) ─────
const ACCESS_KEY = "shopify.access";
const REFRESH_KEY = "shopify.refresh";

export const tokenStore = {
  getAccess(): string | null {
    if (typeof window === "undefined") return null;
    return window.sessionStorage.getItem(ACCESS_KEY);
  },
  getRefresh(): string | null {
    if (typeof window === "undefined") return null;
    return window.sessionStorage.getItem(REFRESH_KEY);
  },
  set(pair: TokenPair): void {
    if (typeof window === "undefined") return;
    window.sessionStorage.setItem(ACCESS_KEY, pair.access_token);
    window.sessionStorage.setItem(REFRESH_KEY, pair.refresh_token);
  },
  clear(): void {
    if (typeof window === "undefined") return;
    window.sessionStorage.removeItem(ACCESS_KEY);
    window.sessionStorage.removeItem(REFRESH_KEY);
  },
};

// ───── Errors ─────
export class HttpError extends Error {
  readonly status: number;
  readonly code: string;
  readonly payload: ApiError | null;

  constructor(status: number, code: string, message: string, payload: ApiError | null) {
    super(message);
    this.name = "HttpError";
    this.status = status;
    this.code = code;
    this.payload = payload;
  }
}

// ───── Refresh coordination (avoid parallel refresh storms) ─────
let refreshPromise: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refresh = tokenStore.getRefresh();
    if (!refresh) return false;

    try {
      const res = await fetch(
        `${BASE_URL}/auth/refresh?token=${encodeURIComponent(refresh)}`,
        { method: "POST" }
      );
      if (!res.ok) {
        tokenStore.clear();
        return false;
      }
      const data = (await res.json()) as TokenPair;
      tokenStore.set(data);
      return true;
    } catch {
      tokenStore.clear();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ───── Core request ─────
export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** If true, skip auth header (e.g. for /auth/login) */
  skipAuth?: boolean;
  /** If true, don't try refreshing on 401 */
  skipRefresh?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, skipAuth, skipRefresh, headers: baseHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    ...((baseHeaders as Record<string, string>) || {}),
  };

  let requestBody: BodyInit | undefined;
  if (body instanceof FormData) {
    requestBody = body;
    // Let browser set Content-Type with boundary
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  }

  if (!skipAuth) {
    const token = tokenStore.getAccess();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers,
    body: requestBody,
  });

  // Auto-refresh path
  if (res.status === 401 && !skipAuth && !skipRefresh) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      const newToken = tokenStore.getAccess();
      if (newToken) headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(`${BASE_URL}${path}`, {
        ...rest,
        headers,
        body: requestBody,
      });
    }
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    const apiError: ApiError | null =
      isJson && typeof payload === "object" && payload !== null
        ? (payload as ApiError)
        : null;
    throw new HttpError(
      res.status,
      apiError?.error ?? "http_error",
      apiError?.detail ?? `HTTP ${res.status}`,
      apiError
    );
  }

  return payload as T;
}

// ───── Convenience methods ─────
export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body }),

  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PUT", body }),

  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "PATCH", body }),

  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "DELETE" }),

  /** For file uploads */
  upload: <T>(path: string, form: FormData, options?: RequestOptions) =>
    request<T>(path, { ...options, method: "POST", body: form }),
};
