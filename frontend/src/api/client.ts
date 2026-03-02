import { getStoredTokens, storeTokens, clearStoredTokens } from "./tokens";

const API_BASE = "/api/v1";

// Singleton refresh promise to prevent concurrent refresh requests
let refreshPromise: Promise<{ access_token: string; refresh_token: string }> | null = null;

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const stored = getStoredTokens();
    if (!stored?.refresh_token) {
      throw new Error("No refresh token");
    }

    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: stored.refresh_token }),
    });

    if (!res.ok) {
      clearStoredTokens();
      throw new Error("Token refresh failed");
    }

    const data = await res.json();
    const tokens = {
      access_token: data.access_token as string,
      refresh_token: data.refresh_token as string,
    };
    storeTokens(tokens);
    return tokens;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const tokens = getStoredTokens();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (tokens?.access_token) {
    headers["Authorization"] = `Bearer ${tokens.access_token}`;
  }

  let response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  // On 401, attempt token refresh and retry once
  if (response.status === 401 && tokens?.refresh_token) {
    try {
      const newTokens = await refreshAccessToken();
      headers["Authorization"] = `Bearer ${newTokens.access_token}`;
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
      });
    } catch {
      // Refresh failed — let the 401 propagate
      clearStoredTokens();
      window.dispatchEvent(new Event("auth:logout"));
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Auth API methods (bypass token injection since they manage tokens directly)
export const authApi = {
  login: async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail || "Login failed");
    }
    return res.json() as Promise<{ access_token: string; refresh_token: string; token_type: string }>;
  },

  register: async (email: string, name: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, name, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(err.detail || "Registration failed");
    }
    return res.json() as Promise<{ access_token: string; refresh_token: string; token_type: string }>;
  },

  getMe: () => request<{ id: string; email: string; name: string; plan_tier: string; created_at: string }>("/auth/me"),
};

export interface ConnectionData {
  id: string;
  org_id: string;
  type: string;
  name: string;
  status: string;
  config: Record<string, unknown> | null;
  last_tested_at: string | null;
  created_at: string;
}

export interface ConnectionTestResultData {
  success: boolean;
  message: string;
  error_detail: string | null;
  tested_at: string;
}

export const api = {
  // Connections
  listConnections: () =>
    request<ConnectionData[]>("/connections"),

  getConnection: (id: string) =>
    request<ConnectionData>(`/connections/${id}`),

  createConnection: (data: Record<string, unknown>) =>
    request<ConnectionData>("/connections", { method: "POST", body: JSON.stringify(data) }),

  updateConnection: (id: string, data: Record<string, unknown>) =>
    request<ConnectionData>(`/connections/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  deleteConnection: (id: string) =>
    request<void>(`/connections/${id}`, { method: "DELETE" }),

  testConnection: (id: string) =>
    request<ConnectionTestResultData>(`/connections/${id}/test`, { method: "POST" }),

  listTables: (connectionId: string, schema: string) =>
    request<{ tables: Array<{ table_name: string; table_type: string; row_count: number }> }>(
      `/connections/${connectionId}/tables?schema=${encodeURIComponent(schema)}`
    ),

  // Monitored Tables
  addMonitoredTables: (data: Record<string, unknown>) =>
    request("/tables/monitor", { method: "POST", body: JSON.stringify(data) }),

  getTableHealth: (tableId: string) =>
    request(`/tables/${tableId}/health`),

  getSchemaHistory: (tableId: string) =>
    request(`/tables/${tableId}/schema/history`),

  // Alerts
  listAlerts: (params?: Record<string, string>) => {
    const searchParams = new URLSearchParams(params);
    return request(`/alerts?${searchParams}`);
  },

  updateAlert: (id: string, data: Record<string, unknown>) =>
    request(`/alerts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // Notifications
  updateNotificationConfig: (data: Record<string, unknown>) =>
    request("/notifications/config", { method: "PUT", body: JSON.stringify(data) }),
};
