import { useState, useEffect, useCallback } from "react";
import MetricsBar from "../components/MetricsBar";
import RecordCard from "../components/RecordCard";
import RecordDetail from "../components/RecordDetail";
import type { MaintenanceRecord, Metrics, Notification } from "../types";

export default function SupervisorDashboard() {
  const [records, setRecords] = useState<MaintenanceRecord[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<MaintenanceRecord | null>(null);
  const [filterAircraft, setFilterAircraft] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (filterAircraft) params.set("aircraft_reg", filterAircraft);
      if (filterSeverity) params.set("severity", filterSeverity);

      const [recRes, metRes, notRes] = await Promise.all([
        fetch(`/api/records?${params}`),
        fetch("/api/metrics"),
        fetch("/api/notifications"),
      ]);
      setRecords(await recRes.json());
      setMetrics(await metRes.json());
      setNotifications(await notRes.json());
    } catch {
      /* backend may not be up yet */
    }
  }, [filterAircraft, filterSeverity]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // WebSocket for live updates
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/dashboard`);
    ws.onmessage = () => fetchData();
    ws.onerror = () => ws.close();
    return () => ws.close();
  }, [fetchData]);

  const handleSignoff = async (recordId: string, signer: string) => {
    try {
      await fetch(`/api/records/${recordId}/signoff`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ signer }),
      });
      fetchData();
      setSelectedRecord(null);
    } catch {
      alert("Sign-off failed");
    }
  };

  const escalatedRecords = records.filter((r) => r.escalated);
  const sortedRecords = [
    ...escalatedRecords,
    ...records.filter((r) => !r.escalated),
  ];
  const uniqueRecords = sortedRecords.filter(
    (r, i, arr) => arr.findIndex((x) => x.id === r.id) === i
  );

  const aircraftOptions = [...new Set(records.map((r) => r.aircraft_registration).filter(Boolean))];

  return (
    <div className="max-w-7xl mx-auto px-4 py-4">
      <MetricsBar metrics={metrics} />

      {/* Escalation alerts */}
      {escalatedRecords.length > 0 && (
        <div className="bg-red-950/70 border border-red-700 rounded-lg p-3 mb-4 animate-slide-up">
          <h3 className="text-red-300 font-bold text-sm mb-1">
            {escalatedRecords.length} ESCALATED FINDING(S)
          </h3>
          {escalatedRecords.slice(0, 3).map((r) => (
            <p key={r.id} className="text-red-200 text-sm">
              {r.aircraft_registration} — {r.discrepancy?.slice(0, 80)}
              {r.escalation_reason ? ` (${r.escalation_reason})` : ""}
            </p>
          ))}
        </div>
      )}

      {/* Notifications */}
      {notifications.length > 0 && (
        <div className="bg-amber-950/40 border border-amber-800 rounded-lg p-3 mb-4">
          <h3 className="text-amber-300 font-bold text-sm mb-1">Recent Notifications</h3>
          {notifications.slice(0, 3).map((n) => (
            <p key={n.id} className="text-amber-200 text-xs">
              [{n.channel}] {n.message.slice(0, 100)}
            </p>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <select
          value={filterAircraft}
          onChange={(e) => setFilterAircraft(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm focus:outline-none"
        >
          <option value="">All Aircraft</option>
          {aircraftOptions.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm focus:outline-none"
        >
          <option value="">All Severities</option>
          <option value="CAT-A">CAT-A</option>
          <option value="CAT-B">CAT-B</option>
          <option value="CAT-C">CAT-C</option>
          <option value="ROUTINE">Routine</option>
        </select>
        <span className="text-xs text-gray-500 self-center">
          {uniqueRecords.length} record(s)
        </span>
      </div>

      {/* Records grid */}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {uniqueRecords.map((r) => (
          <RecordCard
            key={r.id}
            record={r}
            onClick={() => setSelectedRecord(r)}
          />
        ))}
        {uniqueRecords.length === 0 && (
          <div className="col-span-full text-center py-12 text-gray-500">
            No maintenance records yet. Start a session from the Technician console.
          </div>
        )}
      </div>

      {selectedRecord && (
        <RecordDetail
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
          onSignoff={handleSignoff}
        />
      )}
    </div>
  );
}
