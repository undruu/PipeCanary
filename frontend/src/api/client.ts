const API_BASE = "/api/v1";

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Connections
  createConnection: (data: Record<string, unknown>) =>
    request("/connections", { method: "POST", body: JSON.stringify(data) }),

  testConnection: (id: string) =>
    request(`/connections/${id}/test`, { method: "POST" }),

  listTables: (connectionId: string) =>
    request(`/connections/${connectionId}/tables`),

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
