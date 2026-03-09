interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

interface FilterGroup {
  key: string;
  label: string;
  options: FilterOption[];
  value: string;
  onChange: (value: string) => void;
  type?: "pill" | "select";
}

interface FilterBarProps {
  groups: FilterGroup[];
}

function FilterBar({ groups }: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      {groups.map((group) => {
        if (group.type === "select") {
          return (
            <div key={group.key} className="flex items-center gap-2">
              <label className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                {group.label}
              </label>
              <select
                value={group.value}
                onChange={(e) => group.onChange(e.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-canary-500 focus:ring-canary-500"
              >
                {group.options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                    {opt.count != null ? ` (${opt.count})` : ""}
                  </option>
                ))}
              </select>
            </div>
          );
        }

        // Default: pill buttons
        return (
          <div key={group.key} className="flex items-center gap-1">
            {group.options.map((opt) => (
              <button
                key={opt.value}
                onClick={() => group.onChange(opt.value)}
                className={`px-3 py-1 text-sm rounded-full font-medium transition-colors ${
                  group.value === opt.value
                    ? "bg-canary-100 text-canary-800"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {opt.label}
                {opt.count != null ? ` (${opt.count})` : ""}
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}

export default FilterBar;
