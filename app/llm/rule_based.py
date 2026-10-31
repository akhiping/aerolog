"""Rule-based LLM fallback for demo without API keys.

Extracts structured maintenance fields using regex and the normalize module,
detects intent (log, question, history request), and generates follow-up
questions for missing required fields.
"""

from __future__ import annotations

import hashlib
import re
import struct
import uuid
from typing import Any

from app.normalize.normalize import (
    ATA_CHAPTERS,
    NATO_TO_LETTER,
    PART_PREFIXES,
    normalize_ata_chapter,
    normalize_full_transcript,
    normalize_nato_phonetic,
    normalize_part_number,
    normalize_registration,
    normalize_spoken_numbers,
)

from .base import LLMProvider

EMBED_DIM = 128

REQUIRED_FIELDS = [
    "aircraft_registration",
    "ata_chapter_code",
    "discrepancy",
    "corrective_action",
    "severity",
]

SAFETY_TRIGGERS = re.compile(
    r"\b(crack|cracked|cracking|corrosion|corroded|leak|leaking|leaks|"
    r"fuel\s+leak|hydraulic\s+leak|oil\s+leak|fod|foreign\s+object|"
    r"control\s+surface|delamination|structural\s+damage|"
    r"beyond\s+limits?|exceeds?\s+limits?)\b",
    re.IGNORECASE,
)

SEVERITY_CAT_A = re.compile(
    r"\b(crack|cracked|cracking|fuel\s+leak|hydraulic\s+leak|"
    r"control\s+surface|structural\s+damage|fod|foreign\s+object|"
    r"delamination|beyond\s+limits?)\b",
    re.IGNORECASE,
)

SEVERITY_CAT_B = re.compile(
    r"\b(worn|wear|degraded|out\s+of\s+spec|below\s+spec|"
    r"above\s+spec|needs\s+replacement|requires\s+action|oil\s+residue|"
    r"oil\s+leak|corrosion|corroded)\b",
    re.IGNORECASE,
)

DISCREPANCY_MARKERS = re.compile(
    r"\b(found|discovered|noticed|observed|detected|identified|"
    r"noted|inspection\s+revealed|saw|visible|evidence\s+of)\b",
    re.IGNORECASE,
)

ACTION_MARKERS = re.compile(
    r"\b(replaced|repaired|installed|removed|torqued|adjusted|"
    r"serviced|cleaned|lubricated|tightened|applied|sealed|"
    r"ops\s+check|operational\s+check|re-?installed)\b",
    re.IGNORECASE,
)

QUESTION_PATTERNS = re.compile(
    r"\b(what(?:'s| is| are)|how\s+(?:do|should|much|many)|"
    r"where\s+(?:is|are|do)|tell\s+me|can\s+you\s+(?:tell|look|find)|"
    r"what\s+(?:torque|spec|procedure|step))\b",
    re.IGNORECASE,
)

HISTORY_PATTERNS = re.compile(
    r"\b(last\s+(?:service|maintenance|inspection|record)|"
    r"previous\s+(?:service|maintenance|inspection|record|entry)|"
    r"history|service\s+history|prior\s+(?:work|service|maintenance)|"
    r"has\s+(?:this|that)\s+(?:been|ever)|"
    r"read\s+(?:me\s+)?(?:the\s+)?(?:last|previous|history)|"
    r"flagged\s+before|seen\s+before|repeat)\b",
    re.IGNORECASE,
)

MEASUREMENT_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(in-lbs?|ft-lbs?|Nm|PSI|mm|cm|in|inches|"
    r"inch[- ]?pounds?|foot[- ]?pounds?|newton[- ]?meters?|psi)\b",
    re.IGNORECASE,
)

PART_NUMBER_PATTERN = re.compile(
    r"\b((?:MS|AN|NAS|BAC)\s*\d[\d\s-]*[\dA-Z])\b",
    re.IGNORECASE,
)

PART_WITH_DASH_PATTERN = re.compile(
    r"\b((?:MS|AN|NAS|BAC)\d+[-][\dA-Z]+)\b",
    re.IGNORECASE,
)

REGISTRATION_PATTERN = re.compile(
    r"\b([NV][\w-]{2,8})\b|"
    r"\b(VT-[A-Z]{2,4})\b|"
    r"\btail\s+(?:number\s+)?(\S+)",
    re.IGNORECASE,
)

OPS_CHECK_PATTERN = re.compile(
    r"\b(ops\s+check(?:ed)?|operational\s+check)\s+(\w+)",
    re.IGNORECASE,
)

WORK_ORDER_PATTERN = re.compile(
    r"\b(?:work\s+order|w\.o\.)\s*(?:number\s*)?[:#]?\s*([\w][\w-]+)"
    r"|\bWO(?=[^a-zA-Z])[:#-]?\s*([\w][\w-]+)",
    re.IGNORECASE,
)

UNIT_NORMALIZE = {
    "inch pounds": "in-lbs", "inch-pounds": "in-lbs", "inch pound": "in-lbs",
    "in-lbs": "in-lbs", "in lbs": "in-lbs",
    "foot pounds": "ft-lbs", "foot-pounds": "ft-lbs", "foot pound": "ft-lbs",
    "ft-lbs": "ft-lbs", "ft lbs": "ft-lbs",
    "newton meters": "Nm", "newton-meters": "Nm", "nm": "Nm",
    "psi": "PSI",
    "inches": "in", "inch": "in", "in": "in",
    "millimeters": "mm", "mm": "mm",
    "centimeters": "cm", "cm": "cm",
}

FOLLOWUP_QUESTIONS = {
    "aircraft_registration": "I didn't catch the aircraft tail number. Can you give me the registration?",
    "ata_chapter_code": "Which ATA chapter does this fall under?",
    "discrepancy": "Can you describe what you found — the discrepancy or defect?",
    "corrective_action": "What corrective action was taken?",
    "severity": "How would you classify the severity — routine, or does this need CAT A, B, or C attention?",
    "work_order_id": "What's the work order number for this task?",
    "technician_id": "Can you give me your technician ID?",
}


def _detect_intent(text: str) -> str:
    lower = text.lower()
    if HISTORY_PATTERNS.search(lower):
        return "history"
    if QUESTION_PATTERNS.search(lower):
        return "question"
    return "log"


def _extract_registration(text: str) -> str | None:
    m = re.search(r"\bVT-[A-Z]{2,4}\b", text, re.IGNORECASE)
    if m:
        return m.group(0).upper()

    m = re.search(r"\b(N\d{1,5}[A-Z]{0,3})\b", text, re.IGNORECASE)
    if m:
        return m.group(1).upper()

    lower = text.lower()
    tokens = lower.split()

    # Find runs of NATO words + number words that look like a registration
    # e.g. "november one two three" -> N123
    # e.g. "victor tango alpha bravo charlie" -> VT-ABC
    nato_and_digit_words = set(NATO_TO_LETTER.keys()) | {
        "zero", "oh", "one", "two", "three", "four", "five",
        "six", "seven", "eight", "niner", "nine",
    }
    best_run_start = -1
    best_run_len = 0
    i = 0
    while i < len(tokens):
        w = tokens[i].rstrip(".,;:!?")
        if w in nato_and_digit_words:
            run_start = i
            j = i
            while j < len(tokens) and tokens[j].rstrip(".,;:!?") in nato_and_digit_words:
                j += 1
            run_len = j - i
            if run_len >= 2 and run_len > best_run_len:
                best_run_start = run_start
                best_run_len = run_len
            i = j
        else:
            i += 1

    if best_run_start >= 0:
        # Also grab "tail" / "tail number" prefix if present
        phrase_start = best_run_start
        if phrase_start > 0 and tokens[phrase_start - 1] in ("tail", "number"):
            phrase_start -= 1
        if phrase_start > 0 and tokens[phrase_start - 1] == "tail":
            phrase_start -= 1
        segment = " ".join(t.rstrip(".,;:!?") for t in tokens[best_run_start : best_run_start + best_run_len])
        reg = normalize_registration(segment)
        if reg and reg != segment and len(reg) >= 2:
            return reg

    m = re.search(r"\btail\s+(?:number\s+)?(\S+)", text, re.IGNORECASE)
    if m:
        candidate = m.group(1)
        normalized = normalize_registration(candidate)
        if normalized:
            return normalized

    return None


def _extract_parts(text: str) -> list[dict]:
    parts = []
    normalized = normalize_full_transcript(text)

    # Replace spoken "dash" with actual dash before extraction
    dash_normalized = re.sub(r"\bdash\b", "-", normalized, flags=re.IGNORECASE)

    # Try the explicit dash pattern first
    seen_pns: set[str] = set()
    for m in PART_WITH_DASH_PATTERN.finditer(dash_normalized):
        pn = re.sub(r"\s+", "", m.group(1)).upper()
        if pn in seen_pns:
            continue
        seen_pns.add(pn)

        action = "installed"
        context_start = max(0, m.start() - 80)
        context = dash_normalized[context_start : m.end() + 40].lower()
        if re.search(r"\bremov", context):
            action = "removed"
        parts.append({"part_number": pn, "quantity": 1, "action": action})

    # Fall back to the broader pattern
    for m in PART_NUMBER_PATTERN.finditer(dash_normalized):
        raw_pn = m.group(1)
        pn = re.sub(r"\s+", "", raw_pn).upper()
        if pn in seen_pns:
            continue
        seen_pns.add(pn)

        action = "installed"
        context_start = max(0, m.start() - 80)
        context = dash_normalized[context_start : m.end() + 40].lower()
        if re.search(r"\bremov", context):
            action = "removed"
        parts.append({"part_number": pn, "quantity": 1, "action": action})

    return parts


def _extract_measurements(text: str) -> list[dict]:
    measurements = []
    normalized = normalize_full_transcript(text)
    for m in MEASUREMENT_PATTERN.finditer(normalized):
        value = float(m.group(1))
        raw_unit = m.group(2).lower().strip()
        unit = UNIT_NORMALIZE.get(raw_unit, raw_unit)

        context_start = max(0, m.start() - 60)
        context = normalized[context_start : m.start()].lower()
        name = "measurement"
        if "torque" in context:
            name = "torque"
        elif "pressure" in context:
            name = "pressure"
        elif "clearance" in context or "gap" in context:
            name = "clearance"
        elif "wear" in context or "depth" in context:
            name = "wear depth"
        elif "temperature" in context or "temp" in context:
            name = "temperature"

        meas: dict[str, Any] = {"name": name, "value": value, "unit": unit}
        if "below spec" in context or "out of spec" in context or "under spec" in context:
            meas["in_spec"] = False
        elif "in spec" in context or "within spec" in context or "within limits" in context:
            meas["in_spec"] = True

        measurements.append(meas)

    return measurements


def _infer_severity(text: str) -> str:
    if SEVERITY_CAT_A.search(text):
        return "CAT_A"
    if SEVERITY_CAT_B.search(text):
        return "CAT_B"
    return "ROUTINE"


def _split_discrepancy_action(text: str) -> tuple[str | None, str | None]:
    normalized = normalize_full_transcript(text)
    normalized = re.sub(r"\b(?:on\s+)?tail\s+(?:number\s+)?\S+", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bATA\s+\d{2,3}\b", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bwork\s+order\s+\S+", "", normalized, flags=re.IGNORECASE)
    sentences = re.split(r"[.,;]+\s*", normalized)

    discrepancy_parts = []
    action_parts = []

    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if DISCREPANCY_MARKERS.search(s):
            discrepancy_parts.append(s)
        elif ACTION_MARKERS.search(s):
            action_parts.append(s)
        elif not action_parts and discrepancy_parts:
            discrepancy_parts.append(s)
        elif action_parts:
            action_parts.append(s)
        else:
            discrepancy_parts.append(s)

    discrepancy = ". ".join(discrepancy_parts) if discrepancy_parts else None
    action = ". ".join(action_parts) if action_parts else None
    return discrepancy, action


def _extract_ops_check(text: str) -> tuple[bool, str | None]:
    m = OPS_CHECK_PATTERN.search(text)
    if m:
        result = m.group(2).lower()
        good_results = {"good", "satisfactory", "pass", "passed", "normal", "ok", "okay"}
        return True, "satisfactory" if result in good_results else result
    lower = text.lower()
    if "ops check" in lower or "operational check" in lower:
        return True, "satisfactory"
    return False, None


class RuleBasedLLM(LLMProvider):
    """Deterministic field extraction and intent routing — no external API needed."""

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
    ) -> dict:
        user_text = ""
        for m in reversed(messages):
            if m["role"] == "user":
                if isinstance(m["content"], str):
                    user_text = m["content"]
                elif isinstance(m["content"], list):
                    for block in m["content"]:
                        if isinstance(block, dict) and block.get("type") == "text":
                            user_text = block["text"]
                            break
                break

        if not user_text:
            return {"content": "I didn't catch that. Could you repeat?", "tool_calls": None, "usage": {}}

        intent = _detect_intent(user_text)
        normalized = normalize_full_transcript(user_text)

        if intent == "history":
            reg = _extract_registration(user_text) or _extract_registration(normalized)
            component = None
            ata = normalize_ata_chapter(user_text)
            if ata:
                component = ata[1]
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "name": "lookup_history",
                        "arguments": {
                            "aircraft_registration": reg or "",
                            "component": component,
                            "ata_chapter": ata[0] if ata else None,
                            "limit": 5,
                        },
                    }
                ],
                "usage": {},
            }

        if intent == "question":
            return {
                "content": None,
                "tool_calls": [
                    {
                        "id": f"call_{uuid.uuid4().hex[:8]}",
                        "name": "search_manual",
                        "arguments": {
                            "query": normalized,
                            "ata_chapter": None,
                        },
                    }
                ],
                "usage": {},
            }

        # Intent: log — extract fields
        reg = _extract_registration(user_text) or _extract_registration(normalized)
        ata = normalize_ata_chapter(user_text)
        parts = _extract_parts(user_text)
        measurements = _extract_measurements(user_text)
        severity = _infer_severity(user_text)
        discrepancy, action = _split_discrepancy_action(user_text)
        ops_performed, ops_result = _extract_ops_check(user_text)

        wo_match = WORK_ORDER_PATTERN.search(user_text) or WORK_ORDER_PATTERN.search(normalized)
        work_order = (wo_match.group(1) or wo_match.group(2)) if wo_match else None

        component = None
        lower = user_text.lower()
        component_patterns = [
            (r"\b(?:number|no\.?|#)\s*(\w+)\s+(engine|bearing|actuator|valve|pump|filter|sensor|switch|relay|hose|line|duct)",
             lambda m: f"#{m.group(1)} {m.group(2)}"),
            (r"\b(main\s+landing\s+gear|nose\s+landing\s+gear|landing\s+gear)\b",
             lambda m: m.group(1)),
            (r"\b(flight\s+control|control\s+surface|aileron|elevator|rudder|flap|spoiler)\b",
             lambda m: m.group(1)),
            (r"\b(fuel\s+line|fuel\s+filter|fuel\s+pump|fuel\s+tank|oil\s+filter|oil\s+pump|hydraulic\s+pump)\b",
             lambda m: m.group(1)),
            (r"\b(brake\s+pad|brake\s+disc|tire|wheel|strut|exhaust|turbine|compressor)\b",
             lambda m: m.group(1)),
            (r"\b(bearing|actuator|valve|pump|filter|sensor|switch|relay|hose|line|duct|bushing|seal|gasket|o-?ring)\b",
             lambda m: m.group(1)),
        ]
        for pat, fmt in component_patterns:
            cm = re.search(pat, lower)
            if cm:
                component = fmt(cm)
                break

        fields: dict[str, Any] = {}
        if reg:
            fields["aircraft_registration"] = reg
        if ata:
            fields["ata_chapter_code"] = ata[0]
            fields["ata_chapter_name"] = ata[1]
        if component:
            fields["component"] = component
        if discrepancy:
            fields["discrepancy"] = discrepancy
        if action:
            fields["corrective_action"] = action
        if parts:
            fields["parts"] = parts
        if measurements:
            fields["measurements"] = measurements
        fields["severity"] = severity
        if ops_performed:
            fields["ops_check_performed"] = True
            fields["ops_check_result"] = ops_result
        if work_order:
            fields["work_order_id"] = work_order

        tool_calls: list[dict] = [
            {
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "name": "extract_fields",
                "arguments": fields,
            }
        ]

        if SAFETY_TRIGGERS.search(user_text) and severity == "CAT_A":
            tool_calls.append(
                {
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "name": "escalate",
                    "arguments": {
                        "reason": f"Safety-critical finding: {discrepancy or normalized}",
                        "severity": "CAT_A",
                        "aircraft_registration": reg or "",
                        "finding_summary": discrepancy or normalized,
                    },
                }
            )

        missing = [f for f in REQUIRED_FIELDS if f not in fields or not fields[f]]
        if missing:
            field = missing[0]
            tool_calls.append(
                {
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "name": "ask_followup",
                    "arguments": {
                        "field_name": field,
                        "question": FOLLOWUP_QUESTIONS.get(
                            field,
                            f"Can you provide the {field.replace('_', ' ')}?",
                        ),
                    },
                }
            )

        return {
            "content": None,
            "tool_calls": tool_calls,
            "usage": {},
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Bag-of-words hash embeddings."""
        return [self._bow_embed(t) for t in texts]

    @staticmethod
    def _bow_embed(text: str) -> list[float]:
        words = set(text.lower().split())
        vec = [0.0] * EMBED_DIM
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % EMBED_DIM
            sign = 1.0 if (h // EMBED_DIM) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = max(sum(v * v for v in vec) ** 0.5, 1e-9)
        return [v / norm for v in vec]
