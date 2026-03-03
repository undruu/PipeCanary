import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  api,
  type TableListItemData,
  type CheckResultData,
} from "@/api/client";
import HealthIndicator from "@/components/HealthIndicator";
import SparklineChart from "@/components/SparklineChart";
import EmptyState from "@/components/EmptyState";

const frequencyLabels: Record<string, string> = {
  hourly: "Hourly",
  every_6h: "6h",
  every_12h: "12h",
  daily: "Daily",
  weekly: "Weekly",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function Tables() {
  const navigate = useNavigate();
  const [tables, setTables] = useState<TableListItemData[]>([]);
  const [sparklines, setSparklines] = useState<Record<string, CheckResultData[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "paused">("all");

  const fetchTables = useCallback(async () => {
    try {
      const data = await api.listMonitoredTables();
      setTables(data);
      setError("");

      // Fetch sparkline data for each table (limit to first 20)
      const toFetch = data.slice(0, 20);
      const results = await Promise.allSettled(
        toFetch.map((t) =>
          api.getCheckResults(t.id, { check_type: "row_count", days: 14 })
        )
      );
      const sparks: Record<string, CheckResultData[]> = {};
      results.forEach((r, i) => {
        if (r.status === "fulfilled") {
          sparks[toFetch[i].id] = r.value;
        }
      });
      setSparklines(sparks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tables");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  async function handleToggleActive(table: TableListItemData) {
    try {
      await api.updateTableSchedule(table.id, { is_active: !table.is_active });
      setTables((prev) =>
        prev.map((t) =>
          t.id === table.id ? { ...t, is_active: !t.is_active } : t
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update table");
    }
  }

  const filteredTables = tables.filter((t) => {
    if (filter === "active") return t.is_active;
    if (filter === "paused") return !t.is_active;
    return true;
  });

  return (
    <div>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Tables</h1>
          <p className="mt-2 text-gray-600">
            Browse monitored tables and their health status.
          </p>
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

      {/* Filter tabs */}
      <div className="mt-4 flex space-x-2">
        {(["all", "active", "paused"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 text-sm rounded-full font-medium transition-colors ${
              filter === f
                ? "bg-canary-100 text-canary-800"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {f === "all" ? `All (${tables.length})` : f === "active" ? `Active (${tables.filter((t) => t.is_active).length})` : `Paused (${tables.filter((t) => !t.is_active).length})`}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="mt-8 text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-canary-200 border-t-canary-600 rounded-full animate-spin" />
          <p className="mt-2 text-gray-500">Loading tables...</p>
        </div>
      ) : filteredTables.length === 0 ? (
        <div className="mt-8 bg-white shadow rounded-lg">
          <EmptyState
            icon={
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            }
            title={filter === "all" ? "No tables monitored yet" : `No ${filter} tables`}
            description={
              filter === "all"
                ? "Add a connection and select tables to start monitoring."
                : undefined
            }
            action={
              filter === "all" ? (
                <button
                  onClick={() => navigate("/connections")}
                  className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500"
                >
                  Go to Connections
                </button>
              ) : undefined
            }
          />
        </div>
      ) : (
        <div className="mt-6 bg-white shadow rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Health
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Table
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Connection
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Row Count
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                    Trend
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Frequency
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Last Checked
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Active
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredTables.map((table) => {
                  const sparkData = (sparklines[table.id] ?? []).map((r) => ({
                    value: r.value,
                    label: new Date(r.measured_at).toLocaleDateString(),
                  }));

                  return (
                    <tr
                      key={table.id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => navigate(`/tables/${table.id}`)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <HealthIndicator
                          openAlerts={table.open_alerts_count}
                          isActive={table.is_active}
                        />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {table.table_name}
                        </div>
                        <div className="text-xs text-gray-500">
                          {table.schema_name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {table.connection_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {table.latest_row_count != null
                          ? table.latest_row_count.toLocaleString()
                          : "—"}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <SparklineChart data={sparkData} height={28} />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                          {frequencyLabels[table.check_frequency] ?? table.check_frequency}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(table.last_checked_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleToggleActive(table);
                          }}
                          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
                            table.is_active ? "bg-canary-600" : "bg-gray-300"
                          }`}
                          title={table.is_active ? "Pause monitoring" : "Resume monitoring"}
                        >
                          <span
                            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                              table.is_active ? "translate-x-4.5" : "translate-x-0.5"
                            }`}
                          />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default Tables;
