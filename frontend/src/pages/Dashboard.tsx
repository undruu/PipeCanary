import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { api, type DashboardSummaryData } from "@/api/client";

function formatRelativeTime(dateStr: string | null): string {
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

const cards = [
  {
    key: "active_connections" as const,
    label: "Active Connections",
    icon: (
      <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    ),
    color: "bg-blue-50",
    link: "/connections",
  },
  {
    key: "monitored_tables" as const,
    label: "Monitored Tables",
    icon: (
      <svg className="w-6 h-6 text-canary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
      </svg>
    ),
    color: "bg-canary-50",
    link: "/tables",
  },
  {
    key: "open_alerts" as const,
    label: "Open Alerts",
    icon: (
      <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
    ),
    color: "bg-red-50",
    link: "/alerts",
  },
];

function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchSummary = useCallback(async () => {
    try {
      const data = await api.getDashboardSummary();
      setSummary(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  function getCardValue(key: "active_connections" | "monitored_tables" | "open_alerts"): string {
    if (!summary) return "—";
    return String(summary[key]);
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
      <p className="mt-2 text-gray-600">
        Monitor your data quality at a glance.
      </p>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
          <button onClick={() => { setError(""); fetchSummary(); }} className="ml-2 underline">
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-white overflow-hidden shadow rounded-lg animate-pulse">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="w-10 h-10 bg-gray-200 rounded-lg" />
                  <div className="ml-5 flex-1">
                    <div className="h-3 bg-gray-200 rounded w-24 mb-2" />
                    <div className="h-6 bg-gray-200 rounded w-12" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {cards.map((card) => (
              <Link
                key={card.key}
                to={card.link}
                className="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow"
              >
                <div className="p-5">
                  <div className="flex items-center">
                    <div className={`flex-shrink-0 p-2 rounded-lg ${card.color}`}>
                      {card.icon}
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">
                          {card.label}
                        </dt>
                        <dd className="text-2xl font-semibold text-gray-900">
                          {getCardValue(card.key)}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Alert severity breakdown */}
          {summary && summary.open_alerts > 0 && (
            <div className="mt-6 bg-white shadow rounded-lg p-5">
              <h2 className="text-sm font-medium text-gray-700 mb-3">Alert Breakdown</h2>
              <div className="flex gap-6">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-red-500" />
                  <span className="text-sm text-gray-600">
                    {summary.critical_alerts} Critical
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-yellow-500" />
                  <span className="text-sm text-gray-600">
                    {summary.warning_alerts} Warning
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Last check info */}
          <div className="mt-4 text-sm text-gray-500">
            Last check: {formatRelativeTime(summary?.last_check_at ?? null)}
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;
