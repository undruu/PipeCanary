function Alerts() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900">Alerts</h1>
      <p className="mt-2 text-gray-600">
        View and manage data quality alerts.
      </p>

      <div className="mt-4 flex space-x-2">
        <button className="px-3 py-1 text-sm rounded-full bg-canary-100 text-canary-800 font-medium">
          All
        </button>
        <button className="px-3 py-1 text-sm rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200">
          Open
        </button>
        <button className="px-3 py-1 text-sm rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200">
          Acknowledged
        </button>
        <button className="px-3 py-1 text-sm rounded-full bg-gray-100 text-gray-600 hover:bg-gray-200">
          Resolved
        </button>
      </div>

      <div className="mt-8 bg-white shadow rounded-lg p-6">
        <p className="text-gray-500 text-center py-8">
          No alerts yet. Alerts will appear here when data quality issues are
          detected.
        </p>
      </div>
    </div>
  );
}

export default Alerts;
