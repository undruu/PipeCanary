import { useState, type FormEvent } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api } from "@/api/client";

interface TableInfo {
  table_name: string;
  table_type: string;
  row_count: number;
}

function SelectTables() {
  const { connectionId } = useParams<{ connectionId: string }>();
  const navigate = useNavigate();

  const [schema, setSchema] = useState("");
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fetched, setFetched] = useState(false);

  async function handleFetchTables(e: FormEvent) {
    e.preventDefault();
    if (!schema.trim() || !connectionId) return;

    setError("");
    setLoading(true);
    setFetched(false);
    setSelected(new Set());

    try {
      const data = await api.listTables(connectionId, schema.trim());
      setTables(data.tables);
      setFetched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tables");
      setTables([]);
    } finally {
      setLoading(false);
    }
  }

  function toggleTable(tableName: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(tableName)) {
        next.delete(tableName);
      } else {
        next.add(tableName);
      }
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === tables.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(tables.map((t) => t.table_name)));
    }
  }

  async function handleSave() {
    if (!connectionId || selected.size === 0) return;

    setSaving(true);
    setError("");

    try {
      await api.addMonitoredTables({
        connection_id: connectionId,
        tables: Array.from(selected).map((table_name) => ({
          schema_name: schema.trim(),
          table_name,
          check_frequency: "daily",
        })),
      });
      navigate("/connections");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save monitored tables");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="mb-6">
        <Link
          to="/connections"
          className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 mb-4"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Connections
        </Link>
        <h1 className="text-2xl font-semibold text-gray-900">Select Tables to Monitor</h1>
        <p className="mt-2 text-gray-600">
          Choose which tables you'd like PipeCanary to monitor for schema changes, row count anomalies, and data quality issues.
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {/* Schema input */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <form onSubmit={handleFetchTables} className="flex items-end gap-4">
          <div className="flex-1">
            <label htmlFor="schema" className="block text-sm font-medium text-gray-700 mb-1">
              Schema / Dataset
            </label>
            <input
              id="schema"
              type="text"
              required
              value={schema}
              onChange={(e) => setSchema(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500"
              placeholder="e.g. PUBLIC, my_dataset, analytics"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !schema.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Loading..." : "Fetch Tables"}
          </button>
        </form>
      </div>

      {/* Table list */}
      {fetched && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          {tables.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No tables found in schema "{schema}".
            </div>
          ) : (
            <>
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={selected.size === tables.length}
                    onChange={toggleAll}
                    className="h-4 w-4 rounded border-gray-300 text-canary-600 focus:ring-canary-500"
                  />
                  <span className="text-sm text-gray-700">
                    {selected.size} of {tables.length} tables selected
                  </span>
                </div>
              </div>

              <ul className="divide-y divide-gray-200">
                {tables.map((table) => (
                  <li
                    key={table.table_name}
                    onClick={() => toggleTable(table.table_name)}
                    className="flex items-center gap-4 px-6 py-3 hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(table.table_name)}
                      onChange={() => toggleTable(table.table_name)}
                      onClick={(e) => e.stopPropagation()}
                      className="h-4 w-4 rounded border-gray-300 text-canary-600 focus:ring-canary-500"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{table.table_name}</p>
                      <p className="text-xs text-gray-500">{table.table_type}</p>
                    </div>
                    <span className="text-xs text-gray-400">
                      {table.row_count.toLocaleString()} rows
                    </span>
                  </li>
                ))}
              </ul>

              <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
                <Link
                  to="/connections"
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Skip for now
                </Link>
                <button
                  onClick={handleSave}
                  disabled={selected.size === 0 || saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? "Saving..." : `Monitor ${selected.size} Table${selected.size !== 1 ? "s" : ""}`}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default SelectTables;
