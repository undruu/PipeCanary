import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from "recharts";
import {
  api,
  type TableHealthData,
  type CheckResultData,
  type SchemaSnapshotData,
  type AlertData,
  type ScheduleData,
} from "@/api/client";
import HealthIndicator from "@/components/HealthIndicator";

const VALID_FREQUENCIES = ["hourly", "every_6h", "every_12h", "daily", "weekly"];
const frequencyLabels: Record<string, string> = {
  hourly: "Hourly",
  every_6h: "Every 6 hours",
  every_12h: "Every 12 hours",
  daily: "Daily",
  weekly: "Weekly",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

type Tab = "schema" | "row_count" | "null_rate" | "alerts" | "schedule";

function TableDetail() {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState<Tab>("schema");
  const [health, setHealth] = useState<TableHealthData | null>(null);
  const [schedule, setSchedule] = useState<ScheduleData | null>(null);
  const [rowCountHistory, setRowCountHistory] = useState<CheckResultData[]>([]);
  const [nullRateData, setNullRateData] = useState<CheckResultData[]>([]);
  const [schemaHistory, setSchemaHistory] = useState<SchemaSnapshotData[]>([]);
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editFrequency, setEditFrequency] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchAll = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [healthData, scheduleData, rowCounts, nullRates, schemas, alertsData] =
        await Promise.all([
          api.getTableHealth(id),
          api.getTableSchedule(id),
          api.getCheckResults(id, { check_type: "row_count", days: 14 }),
          api.getCheckResults(id, { check_type: "null_rate", days: 14 }),
          api.getSchemaHistory(id),
          api.listAlerts({ table_id: id, limit: "20" }),
        ]);
      setHealth(healthData);
      setSchedule(scheduleData);
      setEditFrequency(scheduleData.check_frequency);
      setRowCountHistory(rowCounts);
      setNullRateData(nullRates);
      setSchemaHistory(schemas);
      setAlerts(alertsData);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load table");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  async function handleSaveSchedule() {
    if (!id) return;
    setSaving(true);
    try {
      const updated = await api.updateTableSchedule(id, {
        check_frequency: editFrequency,
      });
      setSchedule(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update schedule");
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleActive() {
    if (!id || !schedule) return;
    setSaving(true);
    try {
      const updated = await api.updateTableSchedule(id, {
        is_active: !schedule.is_active,
      });
      setSchedule(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle active");
    } finally {
      setSaving(false);
    }
  }

  async function handleAlertAction(alertId: string, status: string) {
    try {
      const updated = await api.updateAlert(alertId, { status });
      setAlerts((prev) =>
        prev.map((a) => (a.id === updated.id ? updated : a))
      );
      // Refresh health to update alert count
      if (id) {
        const h = await api.getTableHealth(id);
        setHealth(h);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update alert");
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block w-8 h-8 border-4 border-canary-200 border-t-canary-600 rounded-full animate-spin" />
        <p className="mt-2 text-gray-500">Loading table details...</p>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Table not found.</p>
        <Link to="/tables" className="mt-2 text-canary-600 hover:underline text-sm">
          Back to Tables
        </Link>
      </div>
    );
  }

  // Prepare row count chart data
  const rowChartData = rowCountHistory.map((r) => ({
    date: new Date(r.measured_at).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }),
    value: r.value,
  }));

  // Aggregate null rates by column (latest value per column)
  const latestNullByColumn: Record<string, number> = {};
  for (const nr of nullRateData) {
    if (nr.column_name) {
      latestNullByColumn[nr.column_name] = nr.value;
    }
  }
  const nullBarData = Object.entries(latestNullByColumn).map(([col, rate]) => ({
    column: col,
    rate: Math.round(rate * 10000) / 100, // as percentage
  }));

  const tabs: { key: Tab; label: string }[] = [
    { key: "schema", label: "Schema" },
    { key: "row_count", label: "Row Count" },
    { key: "null_rate", label: "Null Rates" },
    { key: "alerts", label: `Alerts (${health.open_alerts_count})` },
    { key: "schedule", label: "Schedule" },
  ];

  return (
    <div>
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-4">
        <Link to="/tables" className="hover:text-canary-600">
          Tables
        </Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900">
          {health.schema_name}.{health.table_name}
        </span>
      </nav>

      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            {health.table_name}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Schema: {health.schema_name}
          </p>
        </div>
        <div className="mt-3 sm:mt-0 flex items-center gap-4">
          <HealthIndicator
            openAlerts={health.open_alerts_count}
            isActive={schedule?.is_active ?? true}
          />
          {health.latest_row_count != null && (
            <div className="text-sm text-gray-600">
              {health.latest_row_count.toLocaleString()} rows
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="mt-6 border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`whitespace-nowrap border-b-2 py-3 px-1 text-sm font-medium ${
                tab === t.key
                  ? "border-canary-500 text-canary-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="mt-6">
        {tab === "schema" && (
          <div>
            {/* Current schema */}
            {health.latest_schema && health.latest_schema.length > 0 ? (
              <div className="bg-white shadow rounded-lg overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-sm font-medium text-gray-900">
                    Current Schema ({health.latest_schema.length} columns)
                  </h3>
                </div>
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Column
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Type
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Nullable
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {health.latest_schema.map((col) => (
                      <tr key={col.name}>
                        <td className="px-6 py-3 text-sm font-mono text-gray-900">
                          {col.name}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-600 font-mono">
                          {col.type}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-600">
                          {col.nullable ? (
                            <span className="text-yellow-600">Yes</span>
                          ) : (
                            <span className="text-green-600">No</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="bg-white shadow rounded-lg p-6 text-center text-gray-500">
                No schema data available yet. Waiting for first check.
              </div>
            )}

            {/* Schema history timeline */}
            {schemaHistory.length > 1 && (
              <div className="mt-6 bg-white shadow rounded-lg overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-sm font-medium text-gray-900">
                    Schema Change History
                  </h3>
                </div>
                <div className="divide-y divide-gray-200">
                  {schemaHistory.map((snapshot) => (
                    <div key={snapshot.id} className="px-6 py-3 flex items-center justify-between">
                      <div className="text-sm text-gray-600">
                        {snapshot.columns.length} columns
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatDate(snapshot.captured_at)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "row_count" && (
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-900 mb-4">
              Row Count Trend (14 days)
            </h3>
            {rowChartData.length > 0 ? (
              <div style={{ width: "100%", height: 300 }}>
                <ResponsiveContainer>
                  <LineChart data={rowChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => v.toLocaleString()} />
                    <Tooltip formatter={(value: number | undefined) => [value != null ? value.toLocaleString() : "—", "Rows"]} />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#d97706"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">
                No row count data available yet.
              </p>
            )}
          </div>
        )}

        {tab === "null_rate" && (
          <div className="bg-white shadow rounded-lg p-6">
            <h3 className="text-sm font-medium text-gray-900 mb-4">
              Null Rate per Column (%)
            </h3>
            {nullBarData.length > 0 ? (
              <div style={{ width: "100%", height: Math.max(200, nullBarData.length * 36) }}>
                <ResponsiveContainer>
                  <BarChart data={nullBarData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12 }} />
                    <YAxis
                      type="category"
                      dataKey="column"
                      tick={{ fontSize: 12 }}
                      width={120}
                    />
                    <Tooltip formatter={(value: number | undefined) => [`${value ?? 0}%`, "Null Rate"]} />
                    <Bar dataKey="rate" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">
                No null rate data available yet.
              </p>
            )}
          </div>
        )}

        {tab === "alerts" && (
          <div className="space-y-3">
            {alerts.length === 0 ? (
              <div className="bg-white shadow rounded-lg p-6 text-center text-gray-500">
                No alerts for this table.
              </div>
            ) : (
              alerts.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onAction={handleAlertAction}
                />
              ))
            )}
          </div>
        )}

        {tab === "schedule" && schedule && (
          <div className="bg-white shadow rounded-lg p-6 max-w-lg">
            <h3 className="text-sm font-medium text-gray-900 mb-4">
              Check Schedule
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Check Frequency
                </label>
                <select
                  value={editFrequency}
                  onChange={(e) => setEditFrequency(e.target.value)}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-canary-500 focus:ring-canary-500"
                >
                  {VALID_FREQUENCIES.map((f) => (
                    <option key={f} value={f}>
                      {frequencyLabels[f]}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-700">Monitoring Active</span>
                <button
                  onClick={handleToggleActive}
                  disabled={saving}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    schedule.is_active ? "bg-canary-600" : "bg-gray-300"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      schedule.is_active ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>

              <button
                onClick={handleSaveSchedule}
                disabled={saving || editFrequency === schedule.check_frequency}
                className="px-4 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Alert card sub-component
// ---------------------------------------------------------------------------

const alertTypeColors: Record<string, string> = {
  schema_drift: "border-l-purple-500",
  row_count: "border-l-blue-500",
  null_rate: "border-l-orange-500",
  cardinality: "border-l-teal-500",
};

const alertTypeLabels: Record<string, string> = {
  schema_drift: "Schema Drift",
  row_count: "Row Count",
  null_rate: "Null Rate",
  cardinality: "Cardinality",
};

const severityStyles: Record<string, string> = {
  warning: "bg-yellow-100 text-yellow-800",
  critical: "bg-red-100 text-red-800",
};

const statusStyles: Record<string, string> = {
  open: "bg-blue-100 text-blue-800",
  acknowledged: "bg-purple-100 text-purple-800",
  resolved: "bg-green-100 text-green-800",
  snoozed: "bg-gray-100 text-gray-800",
};

function AlertCard({
  alert,
  onAction,
}: {
  alert: AlertData;
  onAction: (id: string, status: string) => void;
}) {
  return (
    <div
      className={`bg-white shadow rounded-lg border-l-4 p-4 ${
        alertTypeColors[alert.type] ?? "border-l-gray-400"
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900">
              {alertTypeLabels[alert.type] ?? alert.type}
            </span>
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                severityStyles[alert.severity] ?? ""
              }`}
            >
              {alert.severity}
            </span>
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                statusStyles[alert.status] ?? ""
              }`}
            >
              {alert.status}
            </span>
          </div>
          <p className="text-xs text-gray-500">{formatRelativeTime(alert.created_at)}</p>
          <div className="mt-2 text-sm text-gray-600">
            <AlertDetails details={alert.details_json} type={alert.type} />
          </div>
        </div>
        {alert.status === "open" && (
          <div className="flex gap-2 ml-4">
            <button
              onClick={() => onAction(alert.id, "acknowledged")}
              className="px-2 py-1 text-xs font-medium text-purple-700 bg-purple-50 rounded hover:bg-purple-100"
            >
              Ack
            </button>
            <button
              onClick={() => onAction(alert.id, "resolved")}
              className="px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100"
            >
              Resolve
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function AlertDetails({
  details,
  type,
}: {
  details: Record<string, unknown>;
  type: string;
}) {
  if (type === "schema_drift") {
    const added = details.added_columns as string[] | undefined;
    const removed = details.removed_columns as string[] | undefined;
    const changed = details.changed_columns as string[] | undefined;
    return (
      <div className="space-y-1">
        {added && added.length > 0 && (
          <div>
            <span className="text-green-600">+ Added:</span>{" "}
            {added.join(", ")}
          </div>
        )}
        {removed && removed.length > 0 && (
          <div>
            <span className="text-red-600">- Removed:</span>{" "}
            {removed.join(", ")}
          </div>
        )}
        {changed && changed.length > 0 && (
          <div>
            <span className="text-yellow-600">~ Changed:</span>{" "}
            {changed.join(", ")}
          </div>
        )}
      </div>
    );
  }

  if (type === "row_count") {
    return (
      <div>
        Expected: {String(details.expected_range ?? details.expected ?? "—")}
        {", "}Actual: {String(details.actual ?? "—")}
        {details.z_score != null && ` (z-score: ${Number(details.z_score).toFixed(2)})`}
      </div>
    );
  }

  if (type === "null_rate") {
    return (
      <div>
        Column: {String(details.column ?? "—")}
        {", "}Baseline: {String(details.baseline_rate ?? "—")}
        {", "}Current: {String(details.current_rate ?? "—")}
      </div>
    );
  }

  // Fallback: render as JSON
  return (
    <pre className="text-xs whitespace-pre-wrap break-words">
      {JSON.stringify(details, null, 2)}
    </pre>
  );
}

export default TableDetail;
