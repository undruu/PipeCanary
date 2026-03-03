const healthStyles: Record<string, { dot: string; label: string }> = {
  healthy: { dot: "bg-green-500", label: "Healthy" },
  warning: { dot: "bg-yellow-500", label: "Warning" },
  critical: { dot: "bg-red-500", label: "Critical" },
  unknown: { dot: "bg-gray-400", label: "Unknown" },
  paused: { dot: "bg-gray-400", label: "Paused" },
};

function getHealthStatus(openAlerts: number, isActive: boolean): string {
  if (!isActive) return "paused";
  if (openAlerts === 0) return "healthy";
  if (openAlerts >= 3) return "critical";
  return "warning";
}

interface HealthIndicatorProps {
  openAlerts: number;
  isActive: boolean;
  showLabel?: boolean;
}

function HealthIndicator({ openAlerts, isActive, showLabel = true }: HealthIndicatorProps) {
  const status = getHealthStatus(openAlerts, isActive);
  const style = healthStyles[status] ?? healthStyles.unknown;

  return (
    <div className="flex items-center gap-1.5" title={style.label}>
      <span className={`inline-block w-2.5 h-2.5 rounded-full ${style.dot}`} />
      {showLabel && (
        <span className="text-xs text-gray-600">{style.label}</span>
      )}
    </div>
  );
}

export default HealthIndicator;
