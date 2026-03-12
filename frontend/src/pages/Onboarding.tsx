import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import WizardLayout from "@/components/wizard/WizardLayout";
import { api } from "@/api/client";

type WarehouseType = "snowflake" | "bigquery";

const STEPS = ["Connect Warehouse", "Select Tables", "Configure Alerts"];

const warehouseOptions: { value: WarehouseType; label: string; description: string; icon: string }[] = [
  { value: "snowflake", label: "Snowflake", description: "Cloud data warehouse", icon: "S" },
  { value: "bigquery", label: "BigQuery", description: "Google Cloud analytics", icon: "B" },
];

const snowflakeFields = [
  { key: "account", label: "Account", placeholder: "org-account_name", required: true },
  { key: "user", label: "Username", placeholder: "my_user", required: true },
  { key: "password", label: "Password", placeholder: "Enter password", required: true, type: "password" },
  { key: "warehouse", label: "Warehouse", placeholder: "COMPUTE_WH", required: false },
  { key: "database", label: "Database", placeholder: "MY_DATABASE", required: false },
  { key: "role", label: "Role", placeholder: "SYSADMIN", required: false },
];

const bigqueryFields = [
  { key: "project", label: "Project ID", placeholder: "my-gcp-project", required: true },
  { key: "credentials_json", label: "Service Account JSON", placeholder: "Paste service account JSON here", required: true, multiline: true },
  { key: "location", label: "Location", placeholder: "US", required: false },
];

const frequencyOptions = [
  { value: "hourly", label: "Hourly", description: "Best for critical production tables" },
  { value: "daily", label: "Daily", description: "Recommended for most tables" },
  { value: "weekly", label: "Weekly", description: "For stable, low-change tables" },
];

interface TableInfo {
  table_name: string;
  table_type: string;
  row_count: number;
}

function Onboarding() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);

  // Step 1 state
  const [selectedType, setSelectedType] = useState<WarehouseType | null>(null);
  const [connectionName, setConnectionName] = useState("");
  const [credFields, setCredFields] = useState<Record<string, string>>({});
  const [connectionError, setConnectionError] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createdConnectionId, setCreatedConnectionId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Step 2 state
  const [schema, setSchema] = useState("");
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set());
  const [fetchingTables, setFetchingTables] = useState(false);
  const [tablesFetched, setTablesFetched] = useState(false);
  const [tablesError, setTablesError] = useState("");

  // Step 3 state
  const [checkFrequency, setCheckFrequency] = useState("daily");
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [notificationEmail, setNotificationEmail] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  // Completion state
  const [completed, setCompleted] = useState(false);

  function setCredField(key: string, value: string) {
    setCredFields((prev) => {
      const updated = { ...prev, [key]: value };
      if (key === "credentials_json" && selectedType === "bigquery" && !prev.project) {
        try {
          const parsed = JSON.parse(value);
          if (parsed.project_id) {
            updated.project = parsed.project_id;
          }
        } catch {
          // ignore parse errors while typing
        }
      }
      return updated;
    });
  }

  async function handleCreateConnection(e: FormEvent) {
    e.preventDefault();
    if (!selectedType || !connectionName.trim()) return;

    setConnectionError("");
    setIsCreating(true);

    try {
      const credentials: Record<string, unknown> = {};
      const config: Record<string, unknown> = {};

      if (selectedType === "snowflake") {
        credentials.account = credFields.account;
        credentials.user = credFields.user;
        credentials.password = credFields.password;
        if (credFields.warehouse) config.warehouse = credFields.warehouse;
        if (credFields.database) config.database = credFields.database;
        if (credFields.role) config.role = credFields.role;
      } else {
        try {
          credentials.credentials_info = JSON.parse(credFields.credentials_json || "{}");
        } catch {
          setConnectionError("Invalid JSON in Service Account credentials");
          setIsCreating(false);
          return;
        }
        credentials.project = credFields.project;
        if (credFields.location) config.location = credFields.location;
      }

      const connection = await api.createConnection({
        type: selectedType,
        name: connectionName.trim(),
        credentials,
        config: Object.keys(config).length > 0 ? config : null,
      });

      setCreatedConnectionId(connection.id);

      // Test the connection
      try {
        const result = await api.testConnection(connection.id);
        setTestResult({ success: result.success, message: result.message });
      } catch (testErr) {
        setTestResult({
          success: false,
          message: testErr instanceof Error ? testErr.message : "Connection test failed",
        });
      }
    } catch (err) {
      setConnectionError(err instanceof Error ? err.message : "Failed to create connection");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleFetchTables(e: FormEvent) {
    e.preventDefault();
    if (!schema.trim() || !createdConnectionId) return;

    setTablesError("");
    setFetchingTables(true);
    setTablesFetched(false);
    setSelectedTables(new Set());

    try {
      const data = await api.listWarehouseTables(createdConnectionId, schema.trim());
      setTables(data.tables);
      setTablesFetched(true);
    } catch (err) {
      setTablesError(err instanceof Error ? err.message : "Failed to fetch tables");
      setTables([]);
    } finally {
      setFetchingTables(false);
    }
  }

  function toggleTable(tableName: string) {
    setSelectedTables((prev) => {
      const next = new Set(prev);
      if (next.has(tableName)) {
        next.delete(tableName);
      } else {
        next.add(tableName);
      }
      return next;
    });
  }

  function toggleAllTables() {
    if (selectedTables.size === tables.length) {
      setSelectedTables(new Set());
    } else {
      setSelectedTables(new Set(tables.map((t) => t.table_name)));
    }
  }

  async function handleFinish() {
    if (!createdConnectionId || selectedTables.size === 0) return;

    setIsSaving(true);
    setSaveError("");

    try {
      // Monitor selected tables with chosen frequency
      await api.addMonitoredTables({
        connection_id: createdConnectionId,
        tables: Array.from(selectedTables).map((table_name) => ({
          schema_name: schema.trim(),
          table_name,
          check_frequency: checkFrequency,
        })),
      });

      // Configure notifications if provided
      const hasSlack = slackWebhookUrl.trim().length > 0;
      const hasEmail = notificationEmail.trim().length > 0;

      if (hasSlack || hasEmail) {
        const notifConfig: Record<string, unknown> = {};
        if (hasSlack) notifConfig.slack_webhook_url = slackWebhookUrl.trim();
        if (hasEmail) notifConfig.email = notificationEmail.trim();
        notifConfig.enabled = true;

        try {
          await api.updateNotificationConfig(notifConfig);
        } catch {
          // Non-critical — don't block completion
        }
      }

      setCompleted(true);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save configuration");
    } finally {
      setIsSaving(false);
    }
  }

  const fieldDefs = selectedType === "snowflake" ? snowflakeFields : bigqueryFields;

  // Completion screen
  if (completed) {
    return (
      <WizardLayout steps={STEPS} currentStep={4}>
        <div className="text-center py-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-6">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-2">You're all set!</h2>
          <p className="text-gray-600 mb-2">
            PipeCanary is now monitoring {selectedTables.size} table{selectedTables.size !== 1 ? "s" : ""} for schema changes, row count anomalies, and data quality issues.
          </p>
          <p className="text-sm text-gray-500 mb-8">
            Checks will run <span className="font-medium">{checkFrequency}</span> and you'll be notified of any anomalies.
          </p>
          <button
            onClick={() => navigate("/", { replace: true })}
            className="px-6 py-3 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      </WizardLayout>
    );
  }

  return (
    <WizardLayout steps={STEPS} currentStep={currentStep}>
      {/* Step 1: Connect Warehouse */}
      {currentStep === 1 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Connect your data warehouse</h2>
          <p className="text-sm text-gray-600 mb-6">
            Select your warehouse type and enter your credentials to get started.
          </p>

          {!selectedType && (
            <div className="space-y-3">
              {warehouseOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => {
                    setSelectedType(opt.value);
                    setCredFields({});
                    setTestResult(null);
                    setCreatedConnectionId(null);
                  }}
                  className="w-full flex items-center gap-4 p-4 border border-gray-200 rounded-lg hover:border-canary-500 hover:bg-canary-50 transition-colors text-left"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-lg font-bold text-gray-600">
                    {opt.icon}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{opt.label}</div>
                    <div className="text-sm text-gray-500">{opt.description}</div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {selectedType && !testResult && (
            <form onSubmit={handleCreateConnection} className="space-y-4">
              <button
                type="button"
                onClick={() => {
                  setSelectedType(null);
                  setCredFields({});
                  setConnectionName("");
                  setConnectionError("");
                }}
                className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Change type
              </button>

              {connectionError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                  {connectionError}
                </div>
              )}

              <div>
                <label htmlFor="onb-conn-name" className="block text-sm font-medium text-gray-700 mb-1">
                  Connection Name
                </label>
                <input
                  id="onb-conn-name"
                  type="text"
                  required
                  value={connectionName}
                  onChange={(e) => setConnectionName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500"
                  placeholder={`My ${selectedType === "snowflake" ? "Snowflake" : "BigQuery"} Connection`}
                />
              </div>

              {fieldDefs.map((field) => (
                <div key={field.key}>
                  <label htmlFor={`onb-${field.key}`} className="block text-sm font-medium text-gray-700 mb-1">
                    {field.label}
                    {!field.required && <span className="text-gray-400 ml-1">(optional)</span>}
                  </label>
                  {"multiline" in field && field.multiline ? (
                    <textarea
                      id={`onb-${field.key}`}
                      required={field.required}
                      value={credFields[field.key] || ""}
                      onChange={(e) => setCredField(field.key, e.target.value)}
                      rows={4}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500 font-mono text-sm"
                      placeholder={field.placeholder}
                    />
                  ) : (
                    <input
                      id={`onb-${field.key}`}
                      type={"type" in field ? field.type : "text"}
                      required={field.required}
                      value={credFields[field.key] || ""}
                      onChange={(e) => setCredField(field.key, e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500"
                      placeholder={field.placeholder}
                    />
                  )}
                </div>
              ))}

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={isCreating}
                  className="px-5 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCreating ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Connecting...
                    </span>
                  ) : (
                    "Connect & Test"
                  )}
                </button>
              </div>
            </form>
          )}

          {selectedType && testResult && (
            <div className="text-center py-4">
              <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full mb-4 ${testResult.success ? "bg-green-100" : "bg-red-100"}`}>
                {testResult.success ? (
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                )}
              </div>
              <p className={`font-medium mb-4 ${testResult.success ? "text-green-700" : "text-red-700"}`}>
                {testResult.message}
              </p>
              <div className="flex justify-center gap-3">
                {testResult.success ? (
                  <button
                    onClick={() => setCurrentStep(2)}
                    className="px-5 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500"
                  >
                    Next: Select Tables
                  </button>
                ) : (
                  <button
                    onClick={() => {
                      setTestResult(null);
                      setCreatedConnectionId(null);
                    }}
                    className="px-5 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500"
                  >
                    Try Again
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Step 2: Select Tables */}
      {currentStep === 2 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Select tables to monitor</h2>
          <p className="text-sm text-gray-600 mb-6">
            Enter a schema or dataset name to browse available tables, then select which ones to monitor.
          </p>

          {tablesError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {tablesError}
              <button onClick={() => setTablesError("")} className="ml-2 underline">Dismiss</button>
            </div>
          )}

          <form onSubmit={handleFetchTables} className="flex items-end gap-3 mb-6">
            <div className="flex-1">
              <label htmlFor="onb-schema" className="block text-sm font-medium text-gray-700 mb-1">
                Schema / Dataset
              </label>
              <input
                id="onb-schema"
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
              disabled={fetchingTables || !schema.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {fetchingTables ? "Loading..." : "Fetch Tables"}
            </button>
          </form>

          {tablesFetched && (
            <>
              {tables.length === 0 ? (
                <div className="p-6 text-center text-gray-500 border border-gray-200 rounded-lg">
                  No tables found in schema "{schema}".
                </div>
              ) : (
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={tables.length > 0 && selectedTables.size === tables.length}
                      onChange={toggleAllTables}
                      className="h-4 w-4 rounded border-gray-300 text-canary-600 focus:ring-canary-500"
                    />
                    <span className="text-sm text-gray-700">
                      {selectedTables.size} of {tables.length} tables selected
                    </span>
                  </div>

                  <ul className="divide-y divide-gray-200 max-h-64 overflow-y-auto">
                    {tables.map((table) => (
                      <li
                        key={table.table_name}
                        onClick={() => toggleTable(table.table_name)}
                        className="flex items-center gap-4 px-4 py-2.5 hover:bg-gray-50 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedTables.has(table.table_name)}
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
                </div>
              )}
            </>
          )}

          <div className="flex justify-between pt-6">
            <button
              onClick={() => setCurrentStep(1)}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setCurrentStep(3)}
              disabled={selectedTables.size === 0}
              className="px-5 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next: Configure Alerts
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Configure Alerts */}
      {currentStep === 3 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Configure monitoring</h2>
          <p className="text-sm text-gray-600 mb-6">
            Set how often PipeCanary checks your tables and where to send alerts.
          </p>

          {saveError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {saveError}
              <button onClick={() => setSaveError("")} className="ml-2 underline">Dismiss</button>
            </div>
          )}

          {/* Check frequency */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">Check Frequency</label>
            <div className="space-y-2">
              {frequencyOptions.map((opt) => (
                <label
                  key={opt.value}
                  className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                    checkFrequency === opt.value
                      ? "border-canary-500 bg-canary-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="frequency"
                    value={opt.value}
                    checked={checkFrequency === opt.value}
                    onChange={(e) => setCheckFrequency(e.target.value)}
                    className="h-4 w-4 text-canary-600 focus:ring-canary-500"
                  />
                  <div>
                    <div className="text-sm font-medium text-gray-900">{opt.label}</div>
                    <div className="text-xs text-gray-500">{opt.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Notifications */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Notifications <span className="text-gray-400 font-normal">(optional)</span>
            </label>

            <div className="space-y-4">
              <div>
                <label htmlFor="onb-slack" className="block text-xs font-medium text-gray-600 mb-1">
                  Slack Webhook URL
                </label>
                <input
                  id="onb-slack"
                  type="url"
                  value={slackWebhookUrl}
                  onChange={(e) => setSlackWebhookUrl(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500 text-sm"
                  placeholder="https://hooks.slack.com/services/..."
                />
              </div>

              <div>
                <label htmlFor="onb-email" className="block text-xs font-medium text-gray-600 mb-1">
                  Email for alerts
                </label>
                <input
                  id="onb-email"
                  type="email"
                  value={notificationEmail}
                  onChange={(e) => setNotificationEmail(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500 text-sm"
                  placeholder="alerts@yourcompany.com"
                />
              </div>
            </div>
          </div>

          {/* Alert preview */}
          <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Preview</h3>
            <div className="text-sm text-gray-700 space-y-1">
              <p>
                Monitoring <span className="font-medium">{selectedTables.size} table{selectedTables.size !== 1 ? "s" : ""}</span> in{" "}
                <span className="font-medium">{schema}</span>
              </p>
              <p>
                Checks run <span className="font-medium">{checkFrequency}</span> for schema drift, row count anomalies, and null rate changes
              </p>
              {(slackWebhookUrl.trim() || notificationEmail.trim()) && (
                <p>
                  Alerts sent to{" "}
                  {[
                    slackWebhookUrl.trim() ? "Slack" : "",
                    notificationEmail.trim() ? notificationEmail.trim() : "",
                  ]
                    .filter(Boolean)
                    .join(" and ")}
                </p>
              )}
            </div>
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => setCurrentStep(2)}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={handleFinish}
              disabled={isSaving}
              className="px-5 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? (
                <span className="flex items-center gap-2">
                  <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Setting up...
                </span>
              ) : (
                "Finish Setup"
              )}
            </button>
          </div>
        </div>
      )}
    </WizardLayout>
  );
}

export default Onboarding;
