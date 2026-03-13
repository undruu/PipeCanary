export const alertTypeLabels: Record<string, string> = {
  schema_drift: "Schema Drift",
  row_count: "Row Count",
  null_rate: "Null Rate",
  cardinality: "Cardinality",
};

export const severityStyles: Record<string, string> = {
  warning: "bg-yellow-100 text-yellow-800",
  critical: "bg-red-100 text-red-800",
};

export const statusStyles: Record<string, string> = {
  open: "bg-blue-100 text-blue-800",
  acknowledged: "bg-purple-100 text-purple-800",
  resolved: "bg-green-100 text-green-800",
  snoozed: "bg-gray-100 text-gray-800",
};

export function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}
