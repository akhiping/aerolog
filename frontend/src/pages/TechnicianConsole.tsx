import { useState, useRef, useEffect, useCallback } from "react";
import MicButton from "../components/MicButton";
import StateIndicator from "../components/StateIndicator";
import type { AgentMessage, AgentState, MaintenanceRecord } from "../types";

interface ChatEntry {
  role: "user" | "agent";
  text: string;
  type?: string;
  timestamp: Date;
}

export default function TechnicianConsole() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [state, setState] = useState<AgentState | null>(null);
  const [chat, setChat] = useState<ChatEntry[]>([]);
  const [record, setRecord] = useState<MaintenanceRecord | null>(null);
  const [language, setLanguage] = useState("en");
  const [textInput, setTextInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat]);

  const startSession = useCallback(async () => {
    try {
      const res = await fetch("/api/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language }),
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setState(data.state as AgentState);
      setChat([{ role: "agent", text: data.greeting, type: "greeting", timestamp: new Date() }]);
      setRecord(null);
    } catch {
      setChat((c) => [...c, { role: "agent", text: "Failed to start session. Is the backend running?", type: "error", timestamp: new Date() }]);
    }
  }, [language]);

  useEffect(() => {
    startSession();
  }, [startSession]);

  const processResponses = (responses: AgentMessage[]) => {
    for (const msg of responses) {
      if (msg.state) setState(msg.state);
      if (msg.record) setRecord(msg.record);

      if (msg.content && msg.type !== "state_change" && msg.type !== "record_update") {
        setChat((c) => [...c, { role: "agent", text: msg.content, type: msg.type, timestamp: new Date() }]);
      }
      if (msg.type === "state_change" && msg.content) {
        setChat((c) => [...c, { role: "agent", text: msg.content, type: msg.type, timestamp: new Date() }]);
      }
    }
  };

  const sendInput = async (text: string) => {
    if (!sessionId || !text.trim()) return;
    setChat((c) => [...c, { role: "user", text, timestamp: new Date() }]);
    setLoading(true);
    try {
      const res = await fetch(`/api/session/${sessionId}/input`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      processResponses(data.responses);
    } catch {
      setChat((c) => [...c, { role: "agent", text: "Connection error.", type: "error", timestamp: new Date() }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitText = () => {
    if (textInput.trim()) {
      sendInput(textInput.trim());
      setTextInput("");
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-44px)] max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
        <StateIndicator state={state} />
        <div className="flex items-center gap-2">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-gray-800 text-xs rounded px-2 py-1 border border-gray-700 focus:outline-none"
          >
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="te">Telugu</option>
          </select>
          <button
            onClick={startSession}
            className="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded"
          >
            New Session
          </button>
        </div>
      </div>

      {/* Chat + Record area */}
      <div className="flex-1 overflow-y-auto flex">
        {/* Chat column */}
        <div className="flex-1 p-4 space-y-3 overflow-y-auto">
          {chat.map((entry, i) => (
            <div
              key={i}
              className={`animate-slide-up flex ${
                entry.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                  entry.role === "user"
                    ? "bg-blue-700 text-white"
                    : entry.type === "escalation"
                    ? "bg-red-900/70 border border-red-700 text-red-100"
                    : entry.type === "follow_up"
                    ? "bg-amber-900/60 border border-amber-700 text-amber-100"
                    : entry.type === "manual_answer"
                    ? "bg-purple-900/50 border border-purple-700 text-purple-100"
                    : entry.type === "history"
                    ? "bg-cyan-900/50 border border-cyan-700 text-cyan-100"
                    : entry.type === "error"
                    ? "bg-red-900/50 text-red-300"
                    : "bg-gray-800 text-gray-200"
                }`}
              >
                {entry.type && entry.type !== "transcript" && entry.type !== "state_change" && entry.type !== "greeting" && (
                  <span className="text-[10px] uppercase tracking-wider opacity-60 block mb-0.5">
                    {entry.type.replace("_", " ")}
                  </span>
                )}
                {entry.text}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-800 rounded-lg px-4 py-2 text-sm text-gray-400">
                Processing...
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Live record sidebar (desktop only) */}
        {record && (
          <div className="hidden md:block w-72 border-l border-gray-800 p-3 overflow-y-auto text-xs">
            <h3 className="text-gray-500 uppercase tracking-wide mb-2 text-[10px]">
              Live Record
            </h3>
            <div className="space-y-1.5">
              <Field label="Aircraft" value={record.aircraft_registration} />
              <Field
                label="ATA"
                value={
                  record.ata_chapter_code
                    ? `${record.ata_chapter_code} — ${record.ata_chapter_name}`
                    : ""
                }
              />
              <Field label="Component" value={record.component} />
              <Field label="Discrepancy" value={record.discrepancy} />
              <Field label="Action" value={record.corrective_action} />
              <Field label="Severity" value={record.severity} highlight={record.severity?.startsWith("CAT")} />
              {record.parts.length > 0 && (
                <div>
                  <span className="text-gray-500">Parts:</span>
                  {record.parts.map((p, i) => (
                    <div key={i} className="text-blue-300 font-mono">
                      {p.part_number} ({p.action})
                    </div>
                  ))}
                </div>
              )}
              {record.measurements.length > 0 && (
                <div>
                  <span className="text-gray-500">Measurements:</span>
                  {record.measurements.map((m, i) => (
                    <div
                      key={i}
                      className={
                        m.in_spec === false
                          ? "text-red-400"
                          : m.in_spec === true
                          ? "text-green-400"
                          : "text-gray-300"
                      }
                    >
                      {m.name}: {m.value} {m.unit}
                    </div>
                  ))}
                </div>
              )}
              <Field label="Work Order" value={record.work_order_id} />
              <Field label="Technician" value={record.technician_id} />
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex items-center gap-3 justify-center">
          <div className="flex-1 max-w-md flex gap-2">
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmitText()}
              placeholder="Type or use mic..."
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={handleSubmitText}
              disabled={!textInput.trim() || loading}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm"
            >
              Send
            </button>
          </div>
          <MicButton
            onTranscript={sendInput}
            language={language}
            disabled={loading || state === "FINALIZED"}
          />
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, highlight }: { label: string; value?: string; highlight?: boolean }) {
  if (!value) return null;
  return (
    <div>
      <span className="text-gray-500">{label}: </span>
      <span className={highlight ? "text-amber-400 font-medium" : "text-gray-200"}>
        {value}
      </span>
    </div>
  );
}
