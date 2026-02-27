import { useState, useEffect, useCallback } from "react";
import { api, type ConnectionData, type ConnectionTestResultData } from "@/api/client";
import StatusBadge from "@/components/StatusBadge";
import AddConnectionModal from "@/components/AddConnectionModal";
import Modal from "@/components/Modal";

const typeLabels: Record<string, string> = {
  snowflake: "Snowflake",
  bigquery: "BigQuery",
  databricks: "Databricks",
};

function formatDate(dateStr: string | null) {
  if (!dateStr) return "Never";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function Connections() {
  const [connections, setConnections] = useState<ConnectionData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<ConnectionData | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<ConnectionTestResultData | null>(null);

  const fetchConnections = useCallback(async () => {
    try {
      const data = await api.listConnections();
      setConnections(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connections");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  function handleCreated(connection: ConnectionData) {
    setConnections((prev) => [connection, ...prev]);
  }

  async function handleTest(connection: ConnectionData) {
    setActionLoading(connection.id);
    setTestResult(null);
    try {
      const result = await api.testConnection(connection.id);
      setTestResult(result);
      // Refresh to get updated status
      const updated = await api.getConnection(connection.id);
      setConnections((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      if (selectedConnection?.id === updated.id) {
        setSelectedConnection(updated);
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : "Test failed",
        tested_at: new Date().toISOString(),
      });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleDelete() {
    if (!selectedConnection) return;
    setActionLoading(selectedConnection.id);
    try {
      await api.deleteConnection(selectedConnection.id);
      setConnections((prev) => prev.filter((c) => c.id !== selectedConnection.id));
      setSelectedConnection(null);
      setShowDeleteConfirm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete connection");
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900">Connections</h1>
          <p className="mt-2 text-gray-600">
            Manage your warehouse connections.
          </p>
        </div>
        <div className="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="block rounded-md bg-canary-600 px-3 py-2 text-center text-sm font-semibold text-white shadow-sm hover:bg-canary-500"
          >
            Add Connection
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
          <button onClick={() => setError("")} className="ml-2 underline">Dismiss</button>
        </div>
      )}

      {loading ? (
        <div className="mt-8 text-center py-12">
          <div className="inline-block w-8 h-8 border-4 border-canary-200 border-t-canary-600 rounded-full animate-spin" />
          <p className="mt-2 text-gray-500">Loading connections...</p>
        </div>
      ) : connections.length === 0 ? (
        <div className="mt-8 bg-white shadow rounded-lg p-6">
          <p className="text-gray-500 text-center py-8">
            No connections yet. Add a warehouse connection to get started.
          </p>
        </div>
      ) : (
        <div className="mt-8 bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Connection
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Tested
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {connections.map((conn) => (
                <tr
                  key={conn.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => {
                    setSelectedConnection(conn);
                    setTestResult(null);
                  }}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{conn.name}</div>
                    <div className="text-xs text-gray-400 font-mono">{conn.id.slice(0, 8)}...</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <span className="flex-shrink-0 w-6 h-6 rounded bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500">
                        {conn.type === "snowflake" ? "S" : conn.type === "bigquery" ? "B" : "D"}
                      </span>
                      <span className="text-sm text-gray-700">{typeLabels[conn.type] || conn.type}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <StatusBadge status={conn.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(conn.last_tested_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(conn.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTest(conn);
                      }}
                      disabled={actionLoading === conn.id}
                      className="text-canary-600 hover:text-canary-800 font-medium disabled:opacity-50 mr-3"
                    >
                      {actionLoading === conn.id ? "Testing..." : "Test"}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedConnection(conn);
                        setShowDeleteConfirm(true);
                      }}
                      className="text-red-600 hover:text-red-800 font-medium"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Connection Modal */}
      <AddConnectionModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onCreated={handleCreated}
      />

      {/* Connection Detail Modal */}
      <Modal
        open={selectedConnection !== null && !showDeleteConfirm}
        onClose={() => {
          setSelectedConnection(null);
          setTestResult(null);
        }}
        title="Connection Details"
        maxWidth="max-w-xl"
      >
        {selectedConnection && (
          <div className="space-y-4">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
              <div>
                <dt className="text-sm font-medium text-gray-500">Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{selectedConnection.name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Type</dt>
                <dd className="mt-1 text-sm text-gray-900">{typeLabels[selectedConnection.type] || selectedConnection.type}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1"><StatusBadge status={selectedConnection.status} /></dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Last Tested</dt>
                <dd className="mt-1 text-sm text-gray-900">{formatDate(selectedConnection.last_tested_at)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Created</dt>
                <dd className="mt-1 text-sm text-gray-900">{formatDate(selectedConnection.created_at)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">ID</dt>
                <dd className="mt-1 text-xs text-gray-500 font-mono">{selectedConnection.id}</dd>
              </div>
            </dl>

            {testResult && (
              <div className={`p-3 rounded text-sm ${testResult.success ? "bg-green-50 border border-green-200 text-green-700" : "bg-red-50 border border-red-200 text-red-700"}`}>
                {testResult.message}
              </div>
            )}

            <div className="flex justify-between pt-4 border-t border-gray-200">
              <button
                onClick={() => {
                  setShowDeleteConfirm(true);
                }}
                className="px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-300 rounded-md hover:bg-red-50"
              >
                Delete Connection
              </button>
              <button
                onClick={() => handleTest(selectedConnection)}
                disabled={actionLoading === selectedConnection.id}
                className="px-4 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50"
              >
                {actionLoading === selectedConnection.id ? "Testing..." : "Test Connection"}
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        open={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Delete Connection"
        maxWidth="max-w-md"
      >
        <div>
          <p className="text-sm text-gray-600">
            Are you sure you want to delete <span className="font-medium text-gray-900">{selectedConnection?.name}</span>?
            This will also remove all monitored tables associated with this connection.
          </p>
          <div className="flex justify-end gap-3 mt-6">
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={actionLoading !== null}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-500 disabled:opacity-50"
            >
              {actionLoading ? "Deleting..." : "Delete"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default Connections;
