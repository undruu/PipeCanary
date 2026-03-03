import { LineChart, Line, ResponsiveContainer, Tooltip } from "recharts";

interface SparklineChartProps {
  data: Array<{ value: number; label?: string }>;
  color?: string;
  height?: number;
}

function SparklineChart({ data, color = "#d97706", height = 32 }: SparklineChartProps) {
  if (data.length === 0) {
    return <div style={{ height }} className="flex items-center text-xs text-gray-400">No data</div>;
  }

  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <Tooltip
            formatter={(value: number | undefined) => [value != null ? value.toLocaleString() : "—", "Value"]}
            labelFormatter={(_, payload) => {
              const item = payload?.[0]?.payload as { label?: string } | undefined;
              return item?.label ?? "";
            }}
            contentStyle={{ fontSize: 12, padding: "4px 8px" }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default SparklineChart;
