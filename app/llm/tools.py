"""Tool definitions for the AeroLog agent pipeline.

These are passed to the LLM so it can orchestrate the maintenance-logging workflow
by calling the right tool at each step.
"""

from __future__ import annotations

AGENT_TOOLS: list[dict] = [
    {
        "name": "extract_fields",
        "description": (
            "Extract structured maintenance record fields from the technician's "
            "spoken input. Call this whenever the technician describes findings, "
            "actions taken, or parts used."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aircraft_registration": {
                    "type": "string",
                    "description": "Aircraft tail number, e.g. N123 or VT-ABC",
                },
                "ata_chapter_code": {
                    "type": "string",
                    "description": "ATA chapter code, e.g. 72",
                },
                "ata_chapter_name": {
                    "type": "string",
                    "description": "ATA chapter name, e.g. Engine",
                },
                "component": {
                    "type": "string",
                    "description": "Specific component or sub-system",
                },
                "zone": {
                    "type": "string",
                    "description": "Aircraft zone or location",
                },
                "discrepancy": {
                    "type": "string",
                    "description": "What was found wrong — the defect or finding",
                },
                "corrective_action": {
                    "type": "string",
                    "description": "What was done to fix or address the discrepancy",
                },
                "parts": {
                    "type": "array",
                    "description": "Parts removed or installed",
                    "items": {
                        "type": "object",
                        "properties": {
                            "part_number": {"type": "string"},
                            "serial_number": {"type": "string"},
                            "quantity": {"type": "integer", "default": 1},
                            "action": {
                                "type": "string",
                                "enum": ["removed", "installed"],
                            },
                        },
                        "required": ["part_number", "action"],
                    },
                },
                "measurements": {
                    "type": "array",
                    "description": "Measurements taken during inspection",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "What was measured, e.g. torque",
                            },
                            "value": {"type": "number"},
                            "unit": {
                                "type": "string",
                                "description": "Unit of measurement, e.g. in-lbs",
                            },
                            "spec_min": {"type": "number"},
                            "spec_max": {"type": "number"},
                            "in_spec": {"type": "boolean"},
                        },
                        "required": ["name", "value", "unit"],
                    },
                },
                "severity": {
                    "type": "string",
                    "enum": ["CAT_A", "CAT_B", "CAT_C", "ROUTINE"],
                    "description": (
                        "Defect severity. CAT_A = airworthiness-critical (cracks, "
                        "leaks, control surface issues). CAT_B = requires action "
                        "before next flight. CAT_C = deferred maintenance. "
                        "ROUTINE = normal servicing."
                    ),
                },
                "ops_check_performed": {"type": "boolean"},
                "ops_check_result": {
                    "type": "string",
                    "description": "Result of operational check, e.g. 'satisfactory'",
                },
                "work_order_id": {"type": "string"},
                "technician_id": {"type": "string"},
            },
        },
    },
    {
        "name": "ask_followup",
        "description": (
            "Ask the technician a follow-up question to fill in a missing or "
            "ambiguous required field. Use this when a mandatory field is empty "
            "or when confidence is low on a critical value."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "field_name": {
                    "type": "string",
                    "description": "The schema field that needs clarification",
                },
                "question": {
                    "type": "string",
                    "description": "The spoken question to ask the technician",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this field is needed (for logging)",
                },
            },
            "required": ["field_name", "question"],
        },
    },
    {
        "name": "lookup_history",
        "description": (
            "Look up previous maintenance records for a given aircraft and/or "
            "component. Use when the technician asks about prior service history "
            "or to check for repeat defects."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "aircraft_registration": {
                    "type": "string",
                    "description": "Tail number to look up",
                },
                "component": {
                    "type": "string",
                    "description": "Optional: specific component to filter by",
                },
                "ata_chapter": {
                    "type": "string",
                    "description": "Optional: ATA chapter code to filter by",
                },
                "limit": {
                    "type": "integer",
                    "default": 5,
                    "description": "Max records to return",
                },
            },
            "required": ["aircraft_registration"],
        },
    },
    {
        "name": "search_manual",
        "description": (
            "Search the maintenance manual / AMM / task cards for procedures, "
            "torque specs, step sequences, cautions, and limits. Use when the "
            "technician asks a question about how to do something or what a "
            "spec value should be. NEVER invent values — if not found, say so."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The question or search terms",
                },
                "ata_chapter": {
                    "type": "string",
                    "description": "Optional: ATA chapter to narrow search",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "escalate",
        "description": (
            "Escalate a safety-critical finding to a supervisor. Call this when "
            "severity is CAT_A or when safety trigger language is detected "
            "(crack, corrosion beyond limits, fuel/hydraulic leak, control "
            "surface issue, FOD)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "record_id": {
                    "type": "string",
                    "description": "ID of the maintenance record being escalated",
                },
                "reason": {
                    "type": "string",
                    "description": "Why this is being escalated",
                },
                "severity": {
                    "type": "string",
                    "enum": ["CAT_A", "CAT_B"],
                },
                "aircraft_registration": {"type": "string"},
                "finding_summary": {
                    "type": "string",
                    "description": "Brief summary of the critical finding",
                },
            },
            "required": ["reason", "severity", "finding_summary"],
        },
    },
    {
        "name": "save_record",
        "description": (
            "Save the completed maintenance record to the database. Only call "
            "this after all required fields are present and the technician has "
            "confirmed the record."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "confirmed": {
                    "type": "boolean",
                    "description": "Whether the technician has confirmed the record",
                },
            },
            "required": ["confirmed"],
        },
    },
    {
        "name": "read_back",
        "description": (
            "Read back the current state of the record to the technician for "
            "confirmation. Summarize what has been captured so far."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "include_measurements": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include measurement details",
                },
                "include_parts": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include parts details",
                },
            },
        },
    },
]


def tools_for_anthropic() -> list[dict]:
    """Return tools in Anthropic Messages API format (already correct)."""
    return AGENT_TOOLS


def tools_for_openai() -> list[dict]:
    """Convert tool definitions to OpenAI function-calling format."""
    result = []
    for tool in AGENT_TOOLS:
        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
        )
    return result
