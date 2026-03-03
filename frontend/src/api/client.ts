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

export interface TableListItemData {
  id: string;
  connection_id: string;
  connection_name: string;
  schema_name: string;
  table_name: string;
  check_frequency: string;
  is_active: boolean;
  open_alerts_count: number;
  latest_row_count: number | null;
  last_checked_at: string | null;
  created_at: string;
}

export interface TableHealthData {
  table_id: string;
  schema_name: string;
  table_name: string;
  latest_row_count: number | null;
  latest_schema: Array<{ name: string; type: string; nullable: boolean }> | null;
  open_alerts_count: number;
  last_checked_at: string | null;
}

export interface CheckResultData {
  id: string;
  table_id: string;
  check_type: string;
  column_name: string | null;
  value: number;
  measured_at: string;
}

export interface SchemaSnapshotData {
  id: string;
  columns: Array<{ name: string; type: string; nullable: boolean }>;
  captured_at: string | null;
}

export interface AlertData {
  id: string;
  table_id: string;
  type: string;
  severity: string;
  status: string;
  details_json: Record<string, unknown>;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface DashboardSummaryData {
  active_connections: number;
  monitored_tables: number;
  open_alerts: number;
  critical_alerts: number;
  warning_alerts: number;
  last_check_at: string | null;
}

export interface ScheduleData {
  id: string;
  connection_id: string;
  schema_name: string;
  table_name: string;
  check_frequency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
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

  listWarehouseTables: (connectionId: string, schema: string) =>
    request<{ tables: Array<{ table_name: string; table_type: string; row_count: number }> }>(
      `/connections/${connectionId}/tables?schema=${encodeURIComponent(schema)}`
    ),

  // Monitored Tables
  listMonitoredTables: (params?: { connection_id?: string; is_active?: boolean }) => {
    const searchParams = new URLSearchParams();
    if (params?.connection_id) searchParams.set("connection_id", params.connection_id);
    if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));
    const qs = searchParams.toString();
    return request<TableListItemData[]>(`/tables${qs ? `?${qs}` : ""}`);
  },

  addMonitoredTables: (data: Record<string, unknown>) =>
    request<TableListItemData[]>("/tables/monitor", { method: "POST", body: JSON.stringify(data) }),

  getTableHealth: (tableId: string) =>
    request<TableHealthData>(`/tables/${tableId}/health`),

  getCheckResults: (tableId: string, params?: { check_type?: string; days?: number; column_name?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.check_type) searchParams.set("check_type", params.check_type);
    if (params?.days) searchParams.set("days", String(params.days));
    if (params?.column_name) searchParams.set("column_name", params.column_name);
    const qs = searchParams.toString();
    return request<CheckResultData[]>(`/tables/${tableId}/check-results${qs ? `?${qs}` : ""}`);
  },

  getSchemaHistory: (tableId: string) =>
    request<SchemaSnapshotData[]>(`/tables/${tableId}/schema/history`),

  getTableSchedule: (tableId: string) =>
    request<ScheduleData>(`/tables/${tableId}/schedule`),

  updateTableSchedule: (tableId: string, data: { check_frequency?: string; is_active?: boolean }) =>
    request<ScheduleData>(`/tables/${tableId}/schedule`, { method: "PATCH", body: JSON.stringify(data) }),

  // Dashboard
  getDashboardSummary: () =>
    request<DashboardSummaryData>("/dashboard/summary"),

  // Alerts
  listAlerts: (params?: Record<string, string>) => {
    const searchParams = new URLSearchParams(params);
    return request<AlertData[]>(`/alerts?${searchParams}`);
  },

  updateAlert: (id: string, data: Record<string, unknown>) =>
    request<AlertData>(`/alerts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  // Notifications
  updateNotificationConfig: (data: Record<string, unknown>) =>
    request("/notifications/config", { method: "PUT", body: JSON.stringify(data) }),
};
