import { useState } from "react";
import type { MaintenanceRecord } from "../types";

export default function RecordDetail({
  record,
  onClose,
  onSignoff,
}: {
  record: MaintenanceRecord;
  onClose: () => void;
  onSignoff: (recordId: string, signer: string) => void;
}) {
  const [signer, setSigner] = useState("");
  const [showSignoff, setShowSignoff] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-blue-300">
              {record.aircraft_registration || "Unknown Aircraft"}
            </h2>
            <p className="text-sm text-gray-400">
              ATA {record.ata_chapter_code} — {record.ata_chapter_name} |{" "}
              {record.component}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white text-xl leading-none"
          >
            x
          </button>
        </div>

        {record.escalated && (
          <div className="bg-red-900/50 border border-red-700 rounded-lg p-3 mb-4">
            <p className="text-red-300 font-medium text-sm">
              ESCALATED: {record.escalation_reason}
            </p>
          </div>
        )}

        <Section title="Discrepancy">
          <p className="text-gray-200">{record.discrepancy || "—"}</p>
        </Section>

        <Section title="Corrective Action">
          <p className="text-gray-200">{record.corrective_action || "—"}</p>
        </Section>

        {record.measurements.length > 0 && (
          <Section title="Measurements">
            <div className="space-y-1">
              {record.measurements.map((m, i) => (
                <div
                  key={i}
                  className={`flex items-center justify-between text-sm px-3 py-1.5 rounded ${
                    m.in_spec === false
                      ? "bg-red-900/40 border border-red-800"
                      : m.in_spec === true
                      ? "bg-green-900/30 border border-green-800"
                      : "bg-gray-800"
                  }`}
                >
                  <span className="text-gray-300">{m.name}</span>
                  <span className="font-mono">
                    {m.value} {m.unit}
                    {m.spec_min != null && m.spec_max != null && (
                      <span className="text-gray-500 ml-2 text-xs">
                        (spec: {m.spec_min}–{m.spec_max})
                      </span>
                    )}
                    {m.in_spec === true && (
                      <span className="text-green-400 ml-2">IN SPEC</span>
                    )}
                    {m.in_spec === false && (
                      <span className="text-red-400 ml-2">OUT OF SPEC</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </Section>
        )}

        {record.parts.length > 0 && (
          <Section title="Parts">
            <div className="space-y-1">
              {record.parts.map((p, i) => (
                <div key={i} className="flex justify-between text-sm bg-gray-800 rounded px-3 py-1.5">
                  <span className="font-mono text-blue-300">{p.part_number}</span>
                  <span className="text-gray-400">
                    {p.action} | qty: {p.qty}
                    {p.serial_number ? ` | S/N: ${p.serial_number}` : ""}
                  </span>
                </div>
              ))}
            </div>
          </Section>
        )}

        <Section title="Details">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <Detail label="Severity" value={record.severity} />
            <Detail label="Work Order" value={record.work_order_id || "—"} />
            <Detail label="Technician" value={record.technician_id || "—"} />
            <Detail label="Language" value={record.language_detected} />
            <Detail
              label="Ops Check"
              value={
                record.ops_check_performed
                  ? record.ops_check_result || "Performed"
                  : "Not performed"
              }
            />
            <Detail label="Sign-off" value={record.signoff_status} />
          </div>
        </Section>

        {record.raw_transcript && (
          <Section title="Raw Transcript">
            <p className="text-xs text-gray-400 bg-gray-800 rounded p-3 font-mono whitespace-pre-wrap">
              {record.raw_transcript}
            </p>
          </Section>
        )}

        <div className="flex gap-3 mt-6">
          {record.requires_signoff && record.signoff_status !== "signed" && (
            <>
              {showSignoff ? (
                <div className="flex gap-2 flex-1">
                  <input
                    type="text"
                    placeholder="Signer name"
                    value={signer}
                    onChange={(e) => setSigner(e.target.value)}
                    className="flex-1 bg-gray-800 border border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                  />
                  <button
                    onClick={() => {
                      if (signer.trim()) {
                        onSignoff(record.id, signer.trim());
                        setShowSignoff(false);
                      }
                    }}
                    className="bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded text-sm font-medium"
                  >
                    Confirm Sign-off
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowSignoff(true)}
                  className="bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded text-sm font-medium"
                >
                  Sign Off Record
                </button>
              )}
            </>
          )}
          <button
            onClick={onClose}
            className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded text-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="text-xs uppercase tracking-wide text-gray-500 mb-1">{title}</h3>
      {children}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-gray-500">{label}: </span>
      <span className="text-gray-200">{value}</span>
    </div>
  );
}
