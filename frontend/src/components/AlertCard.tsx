import { type AlertData } from "@/api/client";
import {
  alertTypeLabels,
  severityStyles,
  statusStyles,
  formatRelativeTime,
} from "@/components/alertUtils";

const alertTypeColors: Record<string, string> = {
  schema_drift: "border-l-purple-500",
  row_count: "border-l-blue-500",
  null_rate: "border-l-orange-500",
  cardinality: "border-l-teal-500",
};

export function AlertDetails({
  details,
  type,
  expanded = false,
}: {
  details: Record<string, unknown>;
  type: string;
  expanded?: boolean;
}) {
  if (type === "schema_drift") {
    const diff = (details.diff ?? details) as Record<string, unknown>;
    const added = (diff.added_columns ?? details.added_columns) as
      | Array<string | { name: string }>
      | undefined;
    const removed = (diff.removed_columns ?? details.removed_columns) as string[] | undefined;
    const changed = (diff.type_changes ?? details.changed_columns) as
      | Array<string | { column: string; old_type: string; new_type: string }>
      | undefined;
    return (
      <div className="space-y-1">
        {added && added.length > 0 && (
          <div>
            <span className="text-green-600 font-medium">+ Added:</span>{" "}
            {added
              .map((c) => (typeof c === "string" ? c : c.name))
              .join(", ")}
          </div>
        )}
        {removed && removed.length > 0 && (
          <div>
            <span className="text-red-600 font-medium">- Removed:</span>{" "}
            {removed.join(", ")}
          </div>
        )}
        {changed && changed.length > 0 && (
          <div>
            <span className="text-yellow-600 font-medium">~ Changed:</span>{" "}
            {expanded
              ? changed.map((c) =>
                  typeof c === "string"
                    ? c
                    : `${c.column} (${c.old_type} → ${c.new_type})`
                ).join(", ")
              : `${changed.length} column(s)`}
          </div>
        )}
      </div>
    );
  }

  if (type === "row_count") {
    return (
      <div>
        {expanded ? (
          <div className="space-y-1">
            <div>
              <span className="font-medium">Current Value:</span>{" "}
              {details.current_value != null
                ? Number(details.current_value).toLocaleString()
                : String(details.actual ?? "—")}
            </div>
            <div>
              <span className="font-medium">Baseline Mean:</span>{" "}
              {details.baseline_mean != null
                ? Number(details.baseline_mean).toLocaleString()
                : String(details.expected_range ?? details.expected ?? "—")}
            </div>
            {details.baseline_std != null && (
              <div>
                <span className="font-medium">Baseline Std:</span>{" "}
                {Number(details.baseline_std).toLocaleString()}
              </div>
            )}
            {details.z_score != null && (
              <div>
                <span className="font-medium">Z-Score:</span>{" "}
                {Number(details.z_score).toFixed(2)}
              </div>
            )}
            {details.message != null && (
              <div className="text-gray-500 italic">{String(details.message)}</div>
            )}
          </div>
        ) : (
          <span>
            Expected: {String(details.expected_range ?? details.baseline_mean ?? details.expected ?? "—")}
            {", "}Actual: {String(details.current_value ?? details.actual ?? "—")}
            {details.z_score != null && ` (z: ${Number(details.z_score).toFixed(1)})`}
          </span>
        )}
      </div>
    );
  }

  if (type === "null_rate") {
    const columnDetails = details.column_details as
      | Record<string, { current_rate: number; baseline_mean: number; pct_change: number; message?: string }>
      | undefined;

    if (expanded && columnDetails) {
      return (
        <div className="space-y-2">
          {details.columns_affected != null && (
            <div className="text-gray-500">{Number(details.columns_affected)} column(s) affected</div>
          )}
          {Object.entries(columnDetails).map(([col, info]) => (
            <div key={col} className="pl-2 border-l-2 border-orange-200">
              <span className="font-medium font-mono text-sm">{col}</span>
              <div className="text-xs text-gray-600">
                Baseline: {(info.baseline_mean * 100).toFixed(1)}% → Current: {(info.current_rate * 100).toFixed(1)}%
                {info.pct_change != null && ` (${info.pct_change > 0 ? "+" : ""}${info.pct_change.toFixed(0)}%)`}
              </div>
              {info.message && <div className="text-xs text-gray-500 italic">{info.message}</div>}
            </div>
          ))}
        </div>
      );
    }

    return (
      <span>
        Column: {String(details.column ?? (columnDetails ? Object.keys(columnDetails).join(", ") : "—"))}
        {", "}Baseline: {String(details.baseline_rate ?? "—")}
        {", "}Current: {String(details.current_rate ?? "—")}
      </span>
    );
  }

  if (type === "cardinality") {
    const columnDetails = details.column_details as
      | Record<string, { current_value: number; baseline_mean: number; baseline_std: number; z_score: number | null; message?: string }>
      | undefined;

    if (expanded && columnDetails) {
      return (
        <div className="space-y-2">
          {details.columns_affected != null && (
            <div className="text-gray-500">{Number(details.columns_affected)} column(s) affected</div>
          )}
          {Object.entries(columnDetails).map(([col, info]) => (
            <div key={col} className="pl-2 border-l-2 border-teal-200">
              <span className="font-medium font-mono text-sm">{col}</span>
              <div className="text-xs text-gray-600">
                Baseline: {Math.round(info.baseline_mean).toLocaleString()} → Current: {Math.round(info.current_value).toLocaleString()}
                {info.z_score != null && ` (z: ${info.z_score.toFixed(1)})`}
              </div>
              {info.message && <div className="text-xs text-gray-500 italic">{info.message}</div>}
            </div>
          ))}
        </div>
      );
    }

    return (
      <span>
        {details.columns_affected != null
          ? `${Number(details.columns_affected)} column(s) with cardinality change`
          : "Cardinality change detected"}
      </span>
    );
  }

  // Fallback
  return (
    <pre className="text-xs whitespace-pre-wrap break-words">
      {JSON.stringify(details, null, 2)}
    </pre>
  );
}

interface AlertCardProps {
  alert: AlertData;
  onAction: (id: string, status: string) => void;
  onClick?: () => void;
  selected?: boolean;
  onSelect?: (checked: boolean) => void;
  tableName?: string;
  connectionName?: string;
}

function AlertCard({
  alert,
  onAction,
  onClick,
  selected,
  onSelect,
  tableName,
  connectionName,
}: AlertCardProps) {
  return (
    <div
      className={`bg-white shadow rounded-lg border-l-4 p-4 transition-colors ${
        alertTypeColors[alert.type] ?? "border-l-gray-400"
      } ${onClick ? "cursor-pointer hover:bg-gray-50" : ""} ${
        selected ? "ring-2 ring-canary-500" : ""
      }`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        {onSelect && (
          <input
            type="checkbox"
            checked={selected}
            onChange={(e) => {
              e.stopPropagation();
              onSelect(e.target.checked);
            }}
            onClick={(e) => e.stopPropagation()}
            className="mt-1 h-4 w-4 rounded border-gray-300 text-canary-600 focus:ring-canary-500"
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
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
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
            <span>{formatRelativeTime(alert.created_at)}</span>
            {tableName && (
              <>
                <span className="text-gray-300">|</span>
                <span className="font-medium text-gray-600">{tableName}</span>
              </>
            )}
            {connectionName && (
              <>
                <span className="text-gray-300">|</span>
                <span>{connectionName}</span>
              </>
            )}
          </div>
          <div className="text-sm text-gray-600">
            <AlertDetails details={alert.details_json} type={alert.type} />
          </div>
        </div>
        {alert.status === "open" && (
          <div className="flex gap-2 ml-2 shrink-0">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAction(alert.id, "acknowledged");
              }}
              className="px-2 py-1 text-xs font-medium text-purple-700 bg-purple-50 rounded hover:bg-purple-100"
            >
              Ack
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAction(alert.id, "resolved");
              }}
              className="px-2 py-1 text-xs font-medium text-green-700 bg-green-50 rounded hover:bg-green-100"
            >
              Resolve
            </button>
          </div>
        )}
        {alert.status === "acknowledged" && (
          <div className="flex gap-2 ml-2 shrink-0">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAction(alert.id, "resolved");
              }}
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

export default AlertCard;
