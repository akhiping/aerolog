from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.repository import MaintenanceRepository, NotificationRepository, SupervisorRepository
from app.llm.base import LLMProvider
from app.llm.tools import AGENT_TOOLS
from app.normalize.normalize import normalize_full_transcript, normalize_registration, normalize_ata_chapter
from app.rag.engine import RAGEngine
from app.schemas.maintenance import (
    AgentMessage,
    AgentState,
    ATA_CHAPTERS,
    FollowUpQuestion,
    MaintenanceRecord,
    Measurement,
    PartRecord,
    Severity,
)
from app.agent.escalation import EscalationManager

logger = logging.getLogger(__name__)

FOLLOWUP_TEMPLATES = {
    "aircraft_registration": {
        "en": "I didn't catch the aircraft tail number. Can you give me the registration?",
        "hi": "Aircraft ka tail number nahi mila. Registration bata sakte hain?",
        "te": "Aircraft tail number dorakaledu. Registration cheppagalara?",
    },
    "ata_chapter_code": {
        "en": "Which ATA chapter does this fall under?",
        "hi": "Yeh kis ATA chapter mein aata hai?",
        "te": "Idi e ATA chapter lo vastundi?",
    },
    "discrepancy": {
        "en": "Can you describe what you found — the discrepancy or defect?",
        "hi": "Kya defect mila? Describe karein.",
        "te": "Emi defect dorikindi? Describe cheyandi.",
    },
    "corrective_action": {
        "en": "What corrective action was taken?",
        "hi": "Kya corrective action liya gaya?",
        "te": "E corrective action teesukunnarru?",
    },
    "technician_id": {
        "en": "Can you give me your technician ID?",
        "hi": "Aapka technician ID kya hai?",
        "te": "Mee technician ID enti?",
    },
    "work_order_id": {
        "en": "What's the work order number for this task?",
        "hi": "Is task ka work order number kya hai?",
        "te": "E task work order number enti?",
    },
}


class AgentSession:
    def __init__(self, session_id: str, technician_id: str = "", language: str = "en"):
        self.session_id = session_id
        self.state = AgentState.LISTENING
        self.record = MaintenanceRecord(
            id=str(uuid.uuid4()),
            session_id=session_id,
            technician_id=technician_id,
            language_detected=language,
        )
        self.transcript_parts: list[str] = []
        self.messages: list[dict] = []
        self.pending_followups: list[str] = []
        self.language = language
        self.finalized = False


class AgentPipeline:
    def __init__(self, llm: LLMProvider, db_session=None, rag_engine: RAGEngine | None = None):
        self.llm = llm
        self.db = db_session
        self.rag = rag_engine
        self.sessions: dict[str, AgentSession] = {}
        self.escalation_manager = EscalationManager()
        self._ws_broadcast = None

    def set_ws_broadcast(self, broadcast_fn):
        self._ws_broadcast = broadcast_fn
        self.escalation_manager.set_ws_broadcast(broadcast_fn)

    def set_db(self, db_session):
        self.db = db_session

    async def start_session(self, session_id: str, technician_id: str = "", language: str = "en") -> AgentMessage:
        session = AgentSession(session_id, technician_id, language)
        self.sessions[session_id] = session

        greeting = "AeroLog ready. Go ahead with your maintenance finding — I'll capture everything."
        if language == "hi":
            greeting = "AeroLog ready hai. Apna maintenance finding bataiye — main sab capture karunga."
        elif language == "te":
            greeting = "AeroLog ready. Mee maintenance finding cheppandi — nenu antha capture chestanu."

        return AgentMessage(
            type="state_change",
            content=greeting,
            state=AgentState.LISTENING,
        )

    async def process_input(self, session_id: str, text: str) -> list[AgentMessage]:
        session = self.sessions.get(session_id)
        if not session:
            session = AgentSession(session_id)
            self.sessions[session_id] = session

        if session.finalized:
            return [AgentMessage(
                type="state_change",
                content="This record has been finalized. Start a new session for a new entry.",
                state=AgentState.FINALIZED,
            )]

        session.transcript_parts.append(text)
        session.record.raw_transcript = " | ".join(session.transcript_parts)

        normalized = normalize_full_transcript(text)
        messages = await self._run_tool_loop(session, normalized, text)

        if self._ws_broadcast and messages:
            for msg in messages:
                try:
                    await self._ws_broadcast(msg.model_dump())
                except Exception:
                    pass

        return messages

    async def _run_tool_loop(self, session: AgentSession, normalized_text: str, original_text: str) -> list[AgentMessage]:
        agent_messages: list[AgentMessage] = []

        session.state = AgentState.EXTRACTING
        agent_messages.append(AgentMessage(type="state_change", state=AgentState.EXTRACTING))

        system_prompt = self._build_system_prompt(session)
        session.messages.append({"role": "user", "content": original_text})

        llm_messages = [{"role": "system", "content": system_prompt}] + session.messages

        from app.llm.rule_based import RuleBasedLLM
        is_rule_based = isinstance(self.llm, RuleBasedLLM)

        for iteration in range(4):
            try:
                response = await self.llm.chat(
                    messages=llm_messages,
                    tools=AGENT_TOOLS,
                )
            except Exception as exc:
                logger.exception("LLM call failed")
                agent_messages.append(AgentMessage(type="error", content=f"Processing error: {exc}"))
                break

            if response.get("content") and not response.get("tool_calls"):
                content = response["content"]
                session.messages.append({"role": "assistant", "content": content})
                agent_messages.append(AgentMessage(type="transcript", content=content))
                break

            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                break

            tool_results = []
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_input = tc.get("arguments", tc.get("input", {}))

                new_state = self._get_state_for_action(tool_name)
                if new_state != session.state:
                    session.state = new_state
                    agent_messages.append(AgentMessage(type="state_change", state=new_state))

                try:
                    result_text, tool_messages = await self._handle_tool_call(session, tool_name, tool_input)
                except Exception as exc:
                    logger.exception("Tool %s failed", tool_name)
                    result_text = f"Error: {exc}"
                    tool_messages = []

                agent_messages.extend(tool_messages)
                tool_results.append(f"{tool_name}: {result_text}")

            summary = "; ".join(tool_results)
            session.messages.append({"role": "assistant", "content": f"[Processed: {summary}]"})

            if is_rule_based:
                break

            llm_messages = [{"role": "system", "content": system_prompt}] + session.messages

        record_msg = AgentMessage(
            type="record_update",
            record=session.record,
            state=session.state,
        )
        agent_messages.append(record_msg)

        return agent_messages

    async def _handle_tool_call(self, session: AgentSession, tool_name: str, tool_input: dict) -> tuple[str, list[AgentMessage]]:
        handlers = {
            "extract_fields": self._handle_extract_fields,
            "ask_followup": self._handle_ask_followup,
            "lookup_history": self._handle_lookup_history,
            "search_manual": self._handle_search_manual,
            "escalate": self._handle_escalate,
            "save_record": self._handle_save_record,
            "read_back": self._handle_read_back,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return f"Unknown tool: {tool_name}", []
        return await handler(session, tool_input)

    async def _handle_extract_fields(self, session: AgentSession, fields: dict) -> tuple[str, list[AgentMessage]]:
        record = session.record
        extracted = []

        field_map = {
            "aircraft_registration": "aircraft_registration",
            "ata_chapter_code": "ata_chapter_code",
            "ata_chapter_name": "ata_chapter_name",
            "component": "component",
            "zone": "zone",
            "discrepancy": "discrepancy",
            "corrective_action": "corrective_action",
            "work_order_id": "work_order_id",
            "technician_id": "technician_id",
        }

        for src, dst in field_map.items():
            val = fields.get(src)
            if val and isinstance(val, str) and val.strip():
                existing = getattr(record, dst, "")
                if not existing:
                    setattr(record, dst, val.strip())
                    extracted.append(src)
                elif dst in ("technician_id", "work_order_id", "aircraft_registration", "ata_chapter_code"):
                    setattr(record, dst, val.strip())
                    extracted.append(f"{src}(updated)")

        severity_rank = {"ROUTINE": 0, "CAT-C": 1, "CAT-B": 2, "CAT-A": 3}
        if fields.get("severity"):
            sev_str = fields["severity"]
            try:
                if sev_str.startswith("CAT_"):
                    sev_str = sev_str.replace("CAT_", "CAT-")
                new_sev = Severity(sev_str)
                if severity_rank.get(new_sev.value, 0) >= severity_rank.get(record.severity.value, 0):
                    record.severity = new_sev
            except (ValueError, KeyError):
                pass

        if fields.get("ops_check_performed"):
            record.ops_check_performed = True
            record.ops_check_result = fields.get("ops_check_result", "satisfactory")
            extracted.append("ops_check")

        if fields.get("parts"):
            existing_pns = {p.part_number.upper() for p in record.parts}
            for p in fields["parts"]:
                pn = p.get("part_number", "")
                if pn and pn.upper() not in existing_pns:
                    part = PartRecord(
                        part_number=pn,
                        serial_number=p.get("serial_number", ""),
                        qty=p.get("quantity", p.get("qty", 1)),
                        action=p.get("action", "installed"),
                    )
                    record.parts.append(part)
                    existing_pns.add(pn.upper())
                    extracted.append(f"part:{pn}")

        if fields.get("measurements"):
            existing_meas = {(m.name, m.value, m.unit) for m in record.measurements}
            for m in fields["measurements"]:
                meas = Measurement(
                    name=m.get("name", "measurement"),
                    value=m.get("value"),
                    unit=m.get("unit", ""),
                    spec_min=m.get("spec_min"),
                    spec_max=m.get("spec_max"),
                )
                key = (meas.name, meas.value, meas.unit)
                if key not in existing_meas:
                    if m.get("in_spec") is not None:
                        meas.in_spec = m["in_spec"]
                    record.measurements.append(meas)
                    existing_meas.add(key)
                    extracted.append(f"measurement:{meas.name}")

        record.resolve_ata_name()

        if record.should_escalate():
            record.requires_signoff = True

        result = f"Extracted fields: {', '.join(extracted)}" if extracted else "No new fields extracted"
        return result, []

    async def _handle_ask_followup(self, session: AgentSession, data: dict) -> tuple[str, list[AgentMessage]]:
        field_name = data.get("field_name", "")
        question = data.get("question", "")

        if not question and field_name in FOLLOWUP_TEMPLATES:
            lang = session.language
            templates = FOLLOWUP_TEMPLATES[field_name]
            question = templates.get(lang, templates["en"])

        if not question:
            question = f"Can you provide the {field_name.replace('_', ' ')}?"

        session.state = AgentState.CLARIFYING
        followup = FollowUpQuestion(
            field_name=field_name,
            question_text=question,
            language=session.language,
        )
        msg = AgentMessage(
            type="follow_up",
            content=question,
            follow_up=followup,
            state=AgentState.CLARIFYING,
        )
        return f"Asked follow-up for {field_name}: {question}", [msg]

    async def _handle_lookup_history(self, session: AgentSession, data: dict) -> tuple[str, list[AgentMessage]]:
        session.state = AgentState.HISTORY_READBACK

        aircraft_reg = data.get("aircraft_registration", session.record.aircraft_registration)
        component = data.get("component")
        ata_chapter = data.get("ata_chapter")
        limit = data.get("limit", 5)

        if not aircraft_reg:
            return "No aircraft registration provided for history lookup.", [
                AgentMessage(type="follow_up", content="Which aircraft's history would you like to check?")
            ]

        if not self.db:
            return "Database not available for history lookup.", []

        repo = MaintenanceRepository(self.db)
        records = await repo.get_history(aircraft_reg, ata_chapter, component, limit)

        if not records:
            summary = f"No previous maintenance records found for {aircraft_reg}"
            if component:
                summary += f" on {component}"
            msg = AgentMessage(type="history", content=summary, state=AgentState.HISTORY_READBACK)
            return summary, [msg]

        lines = [f"Found {len(records)} previous record(s) for {aircraft_reg}:"]
        for i, rec in enumerate(records, 1):
            date_str = rec.created_at.strftime("%Y-%m-%d") if rec.created_at else "unknown date"
            ata_info = f"ATA {rec.ata_chapter_code}" if rec.ata_chapter_code else ""
            lines.append(
                f"  {i}. {date_str} — {ata_info} {rec.component or ''}: "
                f"{rec.discrepancy or 'N/A'}. Action: {rec.corrective_action or 'N/A'}. "
                f"Severity: {rec.severity or 'ROUTINE'}"
            )

        if ata_chapter and component:
            repeat_records = await repo.find_repeat_defects(aircraft_reg, ata_chapter, component)
            if len(repeat_records) > 1:
                lines.append(
                    f"\n  ⚠ REPEAT DEFECT ALERT: {len(repeat_records)} findings on "
                    f"{component} (ATA {ata_chapter}) for {aircraft_reg} in the last 90 days."
                )

        summary = "\n".join(lines)
        msg = AgentMessage(
            type="history",
            content=summary,
            state=AgentState.HISTORY_READBACK,
            data={"record_count": len(records), "aircraft": aircraft_reg},
        )
        return summary, [msg]

    async def _handle_search_manual(self, session: AgentSession, data: dict) -> tuple[str, list[AgentMessage]]:
        session.state = AgentState.ANSWERING_QUERY
        query = data.get("query", "")
        ata_chapter = data.get("ata_chapter")

        if not self.rag:
            return "Manual search not available — RAG engine not initialized.", [
                AgentMessage(type="manual_answer", content="I don't have access to the maintenance manuals right now.")
            ]

        results = await self.rag.search(query, ata_chapter, top_k=3)

        if not results:
            answer = f"I couldn't find information about '{query}' in the maintenance manuals. Please refer to the physical manual or check with engineering."
            msg = AgentMessage(
                type="manual_answer",
                content=answer,
                state=AgentState.ANSWERING_QUERY,
            )
            return answer, [msg]

        best = results[0]
        lines = [f"From {best['doc_title']}, section '{best['section']}' (ATA {best['ata_chapter']}):"]
        lines.append(best["snippet"])

        if len(results) > 1 and results[1]["score"] > 0.1:
            lines.append(f"\nAlso see: {results[1]['doc_title']}, '{results[1]['section']}'")

        answer = "\n".join(lines)
        msg = AgentMessage(
            type="manual_answer",
            content=answer,
            state=AgentState.ANSWERING_QUERY,
            data={
                "source": best["doc_title"],
                "section": best["section"],
                "ata_chapter": best["ata_chapter"],
                "confidence": best["score"],
            },
        )
        return answer, [msg]

    async def _handle_escalate(self, session: AgentSession, data: dict) -> tuple[str, list[AgentMessage]]:
        session.state = AgentState.ESCALATION_CHECK
        session.record.escalated = True
        session.record.escalation_reason = data.get("reason", "Safety-critical finding")
        session.record.requires_signoff = True

        result = {"escalated": True, "supervisors_notified": [], "channel": "dashboard"}

        if self.db:
            try:
                result = await self.escalation_manager.escalate(
                    record_id=session.record.id,
                    aircraft_registration=session.record.aircraft_registration or data.get("aircraft_registration", ""),
                    reason=data.get("reason", "Safety-critical finding"),
                    finding_summary=data.get("finding_summary", session.record.discrepancy),
                    severity=data.get("severity", session.record.severity.value),
                    db_session=self.db,
                )
            except Exception:
                logger.exception("Escalation DB operation failed")

        supervisors = result.get("supervisors_notified", [])
        sup_text = ", ".join(supervisors) if supervisors else "duty supervisor"
        content = (
            f"This finding has been escalated to {sup_text}. "
            f"Reason: {data.get('reason', 'safety-critical')}. "
            f"Please stand by — do not proceed with further work on this component until cleared."
        )

        msg = AgentMessage(
            type="escalation",
            content=content,
            state=AgentState.ESCALATION_CHECK,
            data=result,
        )
        return content, [msg]

    async def _handle_save_record(self, session: AgentSession, data: dict) -> tuple[str, list[AgentMessage]]:
        record = session.record
        missing = record.required_fields_missing()

        if missing:
            return (
                f"Cannot finalize — missing required fields: {', '.join(missing)}",
                [AgentMessage(
                    type="error",
                    content=f"Record cannot be saved yet. Missing: {', '.join(missing)}",
                )]
            )

        if self.db:
            try:
                repo = MaintenanceRepository(self.db)
                record_data = {
                    "aircraft_registration": record.aircraft_registration,
                    "ata_chapter_code": record.ata_chapter_code,
                    "ata_chapter_name": record.ata_chapter_name,
                    "component": record.component,
                    "zone": record.zone,
                    "discrepancy": record.discrepancy,
                    "corrective_action": record.corrective_action,
                    "parts": [p.model_dump() for p in record.parts],
                    "measurements": [m.model_dump() for m in record.measurements],
                    "severity": record.severity.value,
                    "ops_check_performed": record.ops_check_performed,
                    "ops_check_result": record.ops_check_result,
                    "technician_id": record.technician_id,
                    "work_order_id": record.work_order_id,
                    "confidence": record.confidence,
                    "raw_transcript": record.raw_transcript,
                    "requires_signoff": record.requires_signoff,
                    "signoff_status": record.signoff_status.value,
                    "escalated": record.escalated,
                    "escalation_reason": record.escalation_reason,
                    "session_id": record.session_id,
                    "language_detected": record.language_detected,
                }
                await repo.create_record(record_data)
            except Exception:
                logger.exception("Failed to save record to database")

        session.state = AgentState.FINALIZED
        session.finalized = True

        content = (
            f"Record finalized and saved for {record.aircraft_registration}, "
            f"ATA {record.ata_chapter_code} — {record.ata_chapter_name}. "
            f"Severity: {record.severity.value}."
        )
        if record.escalated:
            content += " This finding has been escalated."
        if record.requires_signoff:
            content += " Requires supervisor sign-off."

        msg = AgentMessage(
            type="state_change",
            content=content,
            record=record,
            state=AgentState.FINALIZED,
        )

        if self._ws_broadcast:
            try:
                await self._ws_broadcast({
                    "type": "record_saved",
                    "data": record.model_dump(),
                })
            except Exception:
                pass

        return content, [msg]

    async def _handle_read_back(self, session: AgentSession, data: dict) -> tuple[str, list[AgentMessage]]:
        session.state = AgentState.CONFIRMING
        record = session.record

        lines = ["Here's what I have so far:"]
        if record.aircraft_registration:
            lines.append(f"  Aircraft: {record.aircraft_registration}")
        if record.ata_chapter_code:
            lines.append(f"  ATA Chapter: {record.ata_chapter_code} — {record.ata_chapter_name}")
        if record.component:
            lines.append(f"  Component: {record.component}")
        if record.discrepancy:
            lines.append(f"  Discrepancy: {record.discrepancy}")
        if record.corrective_action:
            lines.append(f"  Corrective Action: {record.corrective_action}")
        if record.parts:
            lines.append(f"  Parts ({len(record.parts)}):")
            for p in record.parts:
                lines.append(f"    - {p.part_number} ({p.action})")
        if record.measurements:
            lines.append(f"  Measurements ({len(record.measurements)}):")
            for m in record.measurements:
                spec_info = ""
                if m.in_spec is not None:
                    spec_info = " ✓ IN SPEC" if m.in_spec else " ✗ OUT OF SPEC"
                lines.append(f"    - {m.name}: {m.value} {m.unit}{spec_info}")
        lines.append(f"  Severity: {record.severity.value}")
        if record.ops_check_performed:
            lines.append(f"  Ops Check: {record.ops_check_result}")

        missing = record.required_fields_missing()
        if missing:
            lines.append(f"\n  Still needed: {', '.join(missing)}")
        else:
            lines.append("\n  All required fields present. Ready to finalize.")

        summary = "\n".join(lines)
        msg = AgentMessage(
            type="transcript",
            content=summary,
            record=record,
            state=AgentState.CONFIRMING,
        )
        return summary, [msg]

    def _build_system_prompt(self, session: AgentSession) -> str:
        record = session.record
        missing = record.required_fields_missing()

        record_state = []
        if record.aircraft_registration:
            record_state.append(f"aircraft_registration: {record.aircraft_registration}")
        if record.ata_chapter_code:
            record_state.append(f"ata_chapter: {record.ata_chapter_code} ({record.ata_chapter_name})")
        if record.component:
            record_state.append(f"component: {record.component}")
        if record.discrepancy:
            record_state.append(f"discrepancy: {record.discrepancy}")
        if record.corrective_action:
            record_state.append(f"corrective_action: {record.corrective_action}")
        if record.parts:
            record_state.append(f"parts: {len(record.parts)} logged")
        if record.measurements:
            record_state.append(f"measurements: {len(record.measurements)} logged")
        record_state.append(f"severity: {record.severity.value}")

        record_summary = "\n".join(record_state) if record_state else "Empty — no fields captured yet."
        missing_str = ", ".join(missing) if missing else "None — all required fields present."

        return f"""You are AeroLog, a voice-based aircraft maintenance logging assistant for MRO technicians.

Your job: capture structured maintenance records from spoken input. The technician's hands are busy — they're speaking to you while working on an aircraft.

CURRENT RECORD STATE:
{record_summary}

MISSING REQUIRED FIELDS: {missing_str}

LANGUAGE: {session.language} (respond in this language for spoken messages)

RULES:
1. Use extract_fields to capture any maintenance information the technician provides.
2. If required fields are still missing after extraction, use ask_followup to ask ONE question at a time.
3. If the technician asks a question about procedures, torque specs, or manuals, use search_manual. NEVER invent values.
4. If the technician asks about service history, use lookup_history.
5. If a finding is CAT-A severity or contains safety triggers (crack, fuel/hydraulic leak, corrosion beyond limits, FOD, control surface damage), use escalate IMMEDIATELY.
6. When all required fields are present, use read_back to confirm with the technician, then save_record.
7. Normalize aircraft registrations (e.g., "november one two three" → "N123").
8. Be concise — technicians are busy. Short confirmations, direct questions.
9. If confidence is low on a critical field (part number, measurement), ask for confirmation.
10. For measurements, note whether they are in-spec or out-of-spec when limits are known."""

    def _get_state_for_action(self, tool_name: str) -> AgentState:
        return {
            "extract_fields": AgentState.EXTRACTING,
            "ask_followup": AgentState.CLARIFYING,
            "lookup_history": AgentState.HISTORY_READBACK,
            "search_manual": AgentState.ANSWERING_QUERY,
            "escalate": AgentState.ESCALATION_CHECK,
            "save_record": AgentState.FINALIZED,
            "read_back": AgentState.CONFIRMING,
        }.get(tool_name, session.state if hasattr(self, '_current_session') else AgentState.EXTRACTING)

    def get_session(self, session_id: str) -> AgentSession | None:
        return self.sessions.get(session_id)
