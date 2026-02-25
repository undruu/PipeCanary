function Connections() {
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
            className="block rounded-md bg-canary-600 px-3 py-2 text-center text-sm font-semibold text-white shadow-sm hover:bg-canary-500"
          >
            Add Connection
          </button>
        </div>
      </div>

      <div className="mt-8 bg-white shadow rounded-lg p-6">
        <p className="text-gray-500 text-center py-8">
          No connections yet. Add a warehouse connection to get started.
        </p>
      </div>
    </div>
  );
}

export default Connections;
