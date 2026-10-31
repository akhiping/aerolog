import type { MaintenanceRecord } from "../types";

const SEVERITY_COLORS: Record<string, string> = {
  "CAT-A": "bg-red-600 text-white",
  "CAT_A": "bg-red-600 text-white",
  "CAT-B": "bg-amber-600 text-white",
  "CAT_B": "bg-amber-600 text-white",
  "CAT-C": "bg-yellow-600 text-white",
  "CAT_C": "bg-yellow-600 text-white",
  ROUTINE: "bg-gray-600 text-gray-200",
};

export default function RecordCard({
  record,
  onClick,
}: {
  record: MaintenanceRecord;
  onClick: () => void;
}) {
  const sevClass = SEVERITY_COLORS[record.severity] ?? "bg-gray-600 text-gray-200";
  const time = record.created_at
    ? new Date(record.created_at).toLocaleString()
    : "";

  return (
    <div
      onClick={onClick}
      className={`rounded-lg p-4 cursor-pointer transition-all hover:ring-1 hover:ring-blue-500 animate-slide-up ${
        record.escalated
          ? "bg-red-950/60 border border-red-700"
          : "bg-gray-800 border border-gray-700"
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-lg text-blue-300">
            {record.aircraft_registration || "—"}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sevClass}`}>
            {record.severity}
          </span>
          {record.escalated && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-red-600 text-white font-medium">
              ESCALATED
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500">{time}</span>
      </div>

      <div className="text-sm text-gray-300 mb-1">
        {record.ata_chapter_code && (
          <span className="text-gray-400 mr-2">
            ATA {record.ata_chapter_code}
            {record.ata_chapter_name ? ` — ${record.ata_chapter_name}` : ""}
          </span>
        )}
        {record.component && (
          <span className="text-gray-400">| {record.component}</span>
        )}
      </div>

      <p className="text-sm text-gray-200 line-clamp-2">
        {record.discrepancy || "No discrepancy recorded"}
      </p>

      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
        {record.parts.length > 0 && <span>{record.parts.length} part(s)</span>}
        {record.measurements.length > 0 && (
          <span>{record.measurements.length} measurement(s)</span>
        )}
        <span
          className={`${
            record.signoff_status === "signed"
              ? "text-green-400"
              : record.requires_signoff
              ? "text-amber-400"
              : "text-gray-500"
          }`}
        >
          {record.signoff_status === "signed"
            ? "Signed off"
            : record.requires_signoff
            ? "Awaiting sign-off"
            : "No sign-off needed"}
        </span>
      </div>
    </div>
  );
}
