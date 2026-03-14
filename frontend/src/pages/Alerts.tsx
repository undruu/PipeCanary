import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type AlertData,
  type TableListItemData,
} from "@/api/client";
import AlertCard, { AlertDetails } from "@/components/AlertCard";
import {
  formatRelativeTime,
  alertTypeLabels,
  severityStyles,
  statusStyles,
} from "@/components/alertUtils";
import FilterBar from "@/components/FilterBar";
import Pagination from "@/components/Pagination";
import Modal from "@/components/Modal";
import EmptyState from "@/components/EmptyState";

const PAGE_SIZE = 20;

type StatusFilter = "" | "open" | "acknowledged" | "resolved" | "snoozed";
type TypeFilter = "" | "schema_drift" | "row_count" | "null_rate" | "cardinality";

function Alerts() {
  const [alerts, setAlerts] = useState<AlertData[]>([]);
  const [tables, setTables] = useState<TableListItemData[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");
  const [hasMore, setHasMore] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("");
  const [tableFilter, setTableFilter] = useState("");

  // Detail panel
  const [selectedAlert, setSelectedAlert] = useState<AlertData | null>(null);

  // Bulk selection
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading] = useState(false);

  // Build a lookup for table names
  const tableMap = new Map(tables.map((t) => [t.id, t]));

  const buildParams = useCallback(
    (offset: number) => {
      const params: Record<string, string> = {
        limit: String(PAGE_SIZE),
        offset: String(offset),
      };
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.alert_type = typeFilter;
      if (tableFilter) params.table_id = tableFilter;
      return params;
    },
    [statusFilter, typeFilter, tableFilter]
  );

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    setSelectedIds(new Set());
    try {
      const data = await api.listAlerts(buildParams(0));
      setAlerts(data);
      setHasMore(data.length >= PAGE_SIZE);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  const fetchTables = useCallback(async () => {
    try {
      const data = await api.listMonitoredTables();
      setTables(data);
    } catch {
      // Non-critical — table names just won't show
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  async function handleLoadMore() {
    setLoadingMore(true);
    try {
      const data = await api.listAlerts(buildParams(alerts.length));
      setAlerts((prev) => [...prev, ...data]);
      setHasMore(data.length >= PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load more alerts");
    } finally {
      setLoadingMore(false);
    }
  }

  async function handleAlertAction(alertId: string, status: string) {
    try {
      const updated = await api.updateAlert(alertId, { status });
      setAlerts((prev) =>
        prev.map((a) => (a.id === updated.id ? updated : a))
      );
      if (selectedAlert?.id === updated.id) {
        setSelectedAlert(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update alert");
    }
  }

  async function handleBulkAction(status: string) {
    if (selectedIds.size === 0) return;
    setBulkLoading(true);
    try {
      const updates = await Promise.allSettled(
        Array.from(selectedIds).map((id) =>
          api.updateAlert(id, { status })
        )
      );
      const updatedAlerts = new Map<string, AlertData>();
      updates.forEach((result) => {
        if (result.status === "fulfilled") {
          updatedAlerts.set(result.value.id, result.value);
        }
      });
      setAlerts((prev) =>
        prev.map((a) => updatedAlerts.get(a.id) ?? a)
      );
      setSelectedIds(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update alerts");
    } finally {
      setBulkLoading(false);
    }
  }

  function toggleSelect(id: string, checked: boolean) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectedIds.size === alerts.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(alerts.map((a) => a.id)));
    }
  }

  // Count alerts by status for filter labels
  const statusCounts = alerts.reduce(
    (acc, a) => {
      acc[a.status] = (acc[a.status] ?? 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Alerts</h1>
          <p className="mt-2 text-gray-600">
            View and manage data quality alerts.
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

      {/* Filters */}
      <div className="mt-4">
        <FilterBar
          groups={[
            {
              key: "status",
              label: "Status",
              value: statusFilter,
              onChange: (v) => setStatusFilter(v as StatusFilter),
              options: [
                { value: "", label: "All" },
                { value: "open", label: "Open", count: statusCounts.open },
                { value: "acknowledged", label: "Acknowledged", count: statusCounts.acknowledged },
                { value: "resolved", label: "Resolved", count: statusCounts.resolved },
                { value: "snoozed", label: "Snoozed", count: statusCounts.snoozed },
              ],
            },
            {
              key: "type",
              label: "Type",
              value: typeFilter,
              onChange: (v) => setTypeFilter(v as TypeFilter),
              options: [
                { value: "", label: "All Types" },
                { value: "schema_drift", label: "Schema Drift" },
                { value: "row_count", label: "Row Count" },
                { value: "null_rate", label: "Null Rate" },
                { value: "cardinality", label: "Cardinality" },
              ],
              type: "select",
            },
            ...(tables.length > 0
              ? [
                  {
                    key: "table",
                    label: "Table",
                    value: tableFilter,
                    onChange: (v: string) => setTableFilter(v),
                    options: [
                      { value: "", label: "All Tables" },
                      ...tables.map((t) => ({
                        value: t.id,
                        label: `${t.schema_name}.${t.table_name}`,
                      })),
                    ],
                    type: "select" as const,
                  },
                ]
              : []),
          ]}
        />
      </div>

      {/* Bulk actions */}
      {selectedIds.size > 0 && (
        <div className="mt-4 p-3 bg-canary-50 border border-canary-200 rounded-lg flex items-center gap-4">
          <span className="text-sm font-medium text-canary-800">
            {selectedIds.size} alert{selectedIds.size !== 1 ? "s" : ""} selected
          </span>
          <button
            onClick={() => handleBulkAction("acknowledged")}
            disabled={bulkLoading}
            className="px-3 py-1 text-xs font-medium text-purple-700 bg-purple-50 rounded hover:bg-purple-100 disabled:opacity-50"
          >
            Acknowledge All
          </button>
          <button
            onClick={() => handleBulkAction("resolved")}
            disabled={bulkLoading}
            className="px-3 py-1 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100 disabled:opacity-50"
          >
            Resolve All
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="px-3 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
          >
            Clear Selection
          </button>
        </div>
      )}

      {/* Alert list */}
      {loading ? (
        <div className="mt-8 text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-canary-200 border-t-canary-600 rounded-full animate-spin" />
          <p className="mt-2 text-gray-500">Loading alerts...</p>
        </div>
      ) : alerts.length === 0 ? (
        <div className="mt-8 bg-white shadow rounded-lg">
          <EmptyState
            icon={
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
            }
            title={statusFilter || typeFilter || tableFilter ? "No matching alerts" : "No alerts yet"}
            description={
              statusFilter || typeFilter || tableFilter
                ? "Try adjusting your filters."
                : "Alerts will appear here when data quality issues are detected."
            }
          />
        </div>
      ) : (
        <>
          {/* Select all checkbox */}
          <div className="mt-6 mb-2 flex items-center gap-2">
            <input
              type="checkbox"
              checked={selectedIds.size === alerts.length && alerts.length > 0}
              onChange={toggleSelectAll}
              className="h-4 w-4 rounded border-gray-300 text-canary-600 focus:ring-canary-500"
            />
            <span className="text-xs text-gray-500">Select all</span>
          </div>

          <div className="space-y-3">
            {alerts.map((alert) => {
              const table = tableMap.get(alert.table_id);
              return (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onAction={handleAlertAction}
                  onClick={() => setSelectedAlert(alert)}
                  selected={selectedIds.has(alert.id)}
                  onSelect={(checked) => toggleSelect(alert.id, checked)}
                  tableName={table ? `${table.schema_name}.${table.table_name}` : undefined}
                  connectionName={table?.connection_name}
                />
              );
            })}
          </div>

          <Pagination
            hasMore={hasMore}
            loading={loadingMore}
            onLoadMore={handleLoadMore}
            loaded={alerts.length}
          />
        </>
      )}

      {/* Alert detail modal */}
      <Modal
        open={selectedAlert !== null}
        onClose={() => setSelectedAlert(null)}
        title="Alert Details"
        maxWidth="max-w-2xl"
      >
        {selectedAlert && (
          <AlertDetailPanel
            alert={selectedAlert}
            tableName={
              tableMap.get(selectedAlert.table_id)
                ? `${tableMap.get(selectedAlert.table_id)!.schema_name}.${tableMap.get(selectedAlert.table_id)!.table_name}`
                : undefined
            }
            onAction={(status) => {
              handleAlertAction(selectedAlert.id, status);
            }}
          />
        )}
      </Modal>
    </div>
  );
}

function AlertDetailPanel({
  alert,
  tableName,
  onAction,
}: {
  alert: AlertData;
  tableName?: string;
  onAction: (status: string) => void;
}) {
  return (
    <div className="space-y-6">
      {/* Header badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-lg font-medium text-gray-900">
          {alertTypeLabels[alert.type] ?? alert.type}
        </span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            severityStyles[alert.severity] ?? ""
          }`}
        >
          {alert.severity}
        </span>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
            statusStyles[alert.status] ?? ""
          }`}
        >
          {alert.status}
        </span>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-500">Created</span>
          <p className="font-medium text-gray-900">
            {new Date(alert.created_at).toLocaleString()}
            <span className="text-gray-500 font-normal ml-1">
              ({formatRelativeTime(alert.created_at)})
            </span>
          </p>
        </div>
        {tableName && (
          <div>
            <span className="text-gray-500">Table</span>
            <p className="font-medium">
              <Link
                to={`/tables/${alert.table_id}`}
                className="text-canary-600 hover:underline"
              >
                {tableName}
              </Link>
            </p>
          </div>
        )}
        {alert.acknowledged_at && (
          <div>
            <span className="text-gray-500">Acknowledged</span>
            <p className="text-gray-900">
              {new Date(alert.acknowledged_at).toLocaleString()}
            </p>
          </div>
        )}
        {alert.resolved_at && (
          <div>
            <span className="text-gray-500">Resolved</span>
            <p className="text-gray-900">
              {new Date(alert.resolved_at).toLocaleString()}
            </p>
          </div>
        )}
      </div>

      {/* Full details */}
      <div>
        <h4 className="text-sm font-medium text-gray-900 mb-2">Details</h4>
        <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700">
          <AlertDetails details={alert.details_json} type={alert.type} expanded />
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-2 border-t border-gray-200">
        {alert.status === "open" && (
          <>
            <button
              onClick={() => onAction("acknowledged")}
              className="px-4 py-2 text-sm font-medium text-purple-700 bg-purple-50 rounded-md hover:bg-purple-100"
            >
              Acknowledge
            </button>
            <button
              onClick={() => onAction("resolved")}
              className="px-4 py-2 text-sm font-medium text-green-700 bg-green-50 rounded-md hover:bg-green-100"
            >
              Resolve
            </button>
            <button
              onClick={() => onAction("snoozed")}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              Snooze
            </button>
          </>
        )}
        {alert.status === "acknowledged" && (
          <button
            onClick={() => onAction("resolved")}
            className="px-4 py-2 text-sm font-medium text-green-700 bg-green-50 rounded-md hover:bg-green-100"
          >
            Resolve
          </button>
        )}
        {alert.status === "snoozed" && (
          <button
            onClick={() => onAction("open")}
            className="px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 rounded-md hover:bg-blue-100"
          >
            Reopen
          </button>
        )}
      </div>
    </div>
  );
}

export default Alerts;
