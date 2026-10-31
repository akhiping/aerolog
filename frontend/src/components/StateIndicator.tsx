import type { AgentState } from "../types";

const STATE_CONFIG: Record<string, { label: string; color: string }> = {
  LISTENING: { label: "Listening", color: "bg-blue-500" },
  EXTRACTING: { label: "Extracting", color: "bg-yellow-500" },
  CLARIFYING: { label: "Clarifying", color: "bg-amber-500" },
  ANSWERING_QUERY: { label: "Answering", color: "bg-purple-500" },
  HISTORY_READBACK: { label: "History", color: "bg-cyan-500" },
  ESCALATION_CHECK: { label: "Escalation!", color: "bg-red-500" },
  CONFIRMING: { label: "Confirming", color: "bg-indigo-500" },
  FINALIZED: { label: "Finalized", color: "bg-green-500" },
};

export default function StateIndicator({ state }: { state: AgentState | null }) {
  if (!state) return null;
  const cfg = STATE_CONFIG[state] ?? { label: state, color: "bg-gray-500" };
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium text-white ${cfg.color}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-white/60 animate-pulse" />
      {cfg.label}
    </span>
  );
}
