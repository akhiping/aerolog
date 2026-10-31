import type { Metrics } from "../types";

function Tile({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="bg-gray-800 rounded-lg px-4 py-3 flex flex-col">
      <span className="text-xs text-gray-400 uppercase tracking-wide">{label}</span>
      <span className={`text-2xl font-bold ${color}`}>{value}</span>
    </div>
  );
}

export default function MetricsBar({ metrics }: { metrics: Metrics | null }) {
  if (!metrics) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-lg px-4 py-3 h-16 animate-pulse" />
        ))}
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
      <Tile label="Records Logged" value={metrics.total_records} color="text-blue-400" />
      <Tile
        label="Escalation Rate"
        value={`${metrics.escalation_rate}%`}
        color={metrics.escalation_rate > 15 ? "text-red-400" : "text-green-400"}
      />
      <Tile
        label="Overdue Inspections"
        value={metrics.overdue_inspections}
        color={metrics.overdue_inspections > 0 ? "text-amber-400" : "text-green-400"}
      />
      <Tile label="Repeat Defects" value={metrics.repeat_defects_found} color="text-amber-400" />
      <Tile
        label="Avg Log Time"
        value={`${metrics.avg_time_to_log_minutes} min`}
        color="text-blue-400"
      />
    </div>
  );
}
