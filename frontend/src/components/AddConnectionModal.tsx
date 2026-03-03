import { useState, type FormEvent } from "react";
import Modal from "./Modal";
import { api, type ConnectionData } from "@/api/client";

interface AddConnectionModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (connection: ConnectionData) => void;
}

type WarehouseType = "snowflake" | "bigquery";

const warehouseOptions: { value: WarehouseType; label: string; description: string }[] = [
  { value: "snowflake", label: "Snowflake", description: "Cloud data warehouse" },
  { value: "bigquery", label: "BigQuery", description: "Google Cloud analytics" },
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

type Step = "type" | "credentials" | "testing";

function AddConnectionModal({ open, onClose, onCreated }: AddConnectionModalProps) {
  const [step, setStep] = useState<Step>("type");
  const [selectedType, setSelectedType] = useState<WarehouseType | null>(null);
  const [name, setName] = useState("");
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; error_detail: string | null } | null>(null);

  function reset() {
    setStep("type");
    setSelectedType(null);
    setName("");
    setFields({});
    setError("");
    setIsSubmitting(false);
    setTestResult(null);
  }

  function handleClose() {
    reset();
    onClose();
  }

  function handleSelectType(type: WarehouseType) {
    setSelectedType(type);
    setFields({});
    setStep("credentials");
  }

  function setField(key: string, value: string) {
    setFields((prev) => {
      const updated = { ...prev, [key]: value };
      // Auto-populate project from service account JSON when project is empty
      if (key === "credentials_json" && selectedType === "bigquery" && !prev.project) {
        try {
          const parsed = JSON.parse(value);
          if (parsed.project_id) {
            updated.project = parsed.project_id;
          }
        } catch {
          // ignore parse errors while user is still typing
        }
      }
      return updated;
    });
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!selectedType || !name.trim()) return;

    setError("");
    setIsSubmitting(true);
    setStep("testing");

    try {
      // Build credentials and config from fields
      const credentials: Record<string, unknown> = {};
      const config: Record<string, unknown> = {};

      if (selectedType === "snowflake") {
        credentials.account = fields.account;
        credentials.user = fields.user;
        credentials.password = fields.password;
        if (fields.warehouse) config.warehouse = fields.warehouse;
        if (fields.database) config.database = fields.database;
        if (fields.role) config.role = fields.role;
      } else if (selectedType === "bigquery") {
        try {
          credentials.credentials_info = JSON.parse(fields.credentials_json || "{}");
        } catch {
          setError("Invalid JSON in Service Account credentials");
          setStep("credentials");
          setIsSubmitting(false);
          return;
        }
        credentials.project = fields.project;
        if (fields.location) config.location = fields.location;
      }

      const connection = await api.createConnection({
        type: selectedType,
        name: name.trim(),
        credentials,
        config: Object.keys(config).length > 0 ? config : null,
      });

      // Connection created — notify parent so it appears in the list
      onCreated(connection);

      // Now test the connection
      try {
        const result = await api.testConnection(connection.id);
        setTestResult(result);

        // Refresh connection to get updated status
        const updated = await api.getConnection(connection.id);
        onCreated(updated);
      } catch (testErr) {
        setTestResult({
          success: false,
          message: testErr instanceof Error ? testErr.message : "Connection test failed",
          error_detail: null,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create connection");
      setStep("credentials");
    } finally {
      setIsSubmitting(false);
    }
  }

  const fieldDefs = selectedType === "snowflake" ? snowflakeFields : bigqueryFields;

  return (
    <Modal open={open} onClose={handleClose} title="Add Connection" maxWidth="max-w-xl">
      {step === "type" && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600 mb-4">Select your data warehouse type.</p>
          {warehouseOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleSelectType(opt.value)}
              className="w-full flex items-center gap-4 p-4 border border-gray-200 rounded-lg hover:border-canary-500 hover:bg-canary-50 transition-colors text-left"
            >
              <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center text-lg font-bold text-gray-600">
                {opt.value === "snowflake" ? "S" : "B"}
              </div>
              <div>
                <div className="font-medium text-gray-900">{opt.label}</div>
                <div className="text-sm text-gray-500">{opt.description}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {step === "credentials" && selectedType && (
        <form onSubmit={handleSubmit} className="space-y-4">
          <button
            type="button"
            onClick={() => setStep("type")}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="conn-name" className="block text-sm font-medium text-gray-700 mb-1">
              Connection Name
            </label>
            <input
              id="conn-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500"
              placeholder={`My ${selectedType === "snowflake" ? "Snowflake" : "BigQuery"} Connection`}
            />
          </div>

          {fieldDefs.map((field) => (
            <div key={field.key}>
              <label htmlFor={`field-${field.key}`} className="block text-sm font-medium text-gray-700 mb-1">
                {field.label}
                {!field.required && <span className="text-gray-400 ml-1">(optional)</span>}
              </label>
              {"multiline" in field && field.multiline ? (
                <textarea
                  id={`field-${field.key}`}
                  required={field.required}
                  value={fields[field.key] || ""}
                  onChange={(e) => setField(field.key, e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500 font-mono text-sm"
                  placeholder={field.placeholder}
                />
              ) : (
                <input
                  id={`field-${field.key}`}
                  type={"type" in field ? field.type : "text"}
                  required={field.required}
                  value={fields[field.key] || ""}
                  onChange={(e) => setField(field.key, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-canary-500 focus:border-canary-500"
                  placeholder={field.placeholder}
                />
              )}
            </div>
          ))}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? "Creating..." : "Create & Test"}
            </button>
          </div>
        </form>
      )}

      {step === "testing" && (
        <div className="text-center py-8">
          {isSubmitting && !testResult && (
            <>
              <div className="inline-block w-8 h-8 border-4 border-canary-200 border-t-canary-600 rounded-full animate-spin mb-4" />
              <p className="text-gray-600">Creating connection and testing credentials...</p>
            </>
          )}
          {testResult && (
            <>
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
              <p className={`font-medium ${testResult.success ? "text-green-700" : "text-red-700"}`}>
                {testResult.message}
              </p>
              {testResult.error_detail && (
                <p className="mt-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3 text-left font-mono whitespace-pre-wrap break-words max-h-32 overflow-y-auto">
                  {testResult.error_detail}
                </p>
              )}
              <div className="mt-6">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 text-sm font-medium text-white bg-canary-600 rounded-md hover:bg-canary-500"
                >
                  Done
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </Modal>
  );
}

export default AddConnectionModal;
