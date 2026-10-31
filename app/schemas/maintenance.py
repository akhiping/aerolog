from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class PartAction(str, Enum):
    REMOVED = "removed"
    INSTALLED = "installed"
    INSPECTED = "inspected"
    SERVICEABLE = "serviceable"


class Severity(str, Enum):
    CAT_A = "CAT-A"
    CAT_B = "CAT-B"
    CAT_C = "CAT-C"
    ROUTINE = "ROUTINE"


class SignoffStatus(str, Enum):
    PENDING = "pending"
    SIGNED = "signed"
    DEFERRED = "deferred"


class AgentState(str, Enum):
    LISTENING = "LISTENING"
    EXTRACTING = "EXTRACTING"
    CLARIFYING = "CLARIFYING"
    ANSWERING_QUERY = "ANSWERING_QUERY"
    HISTORY_READBACK = "HISTORY_READBACK"
    ESCALATION_CHECK = "ESCALATION_CHECK"
    CONFIRMING = "CONFIRMING"
    FINALIZED = "FINALIZED"


class PartRecord(BaseModel):
    part_number: str = ""
    serial_number: str = ""
    qty: int = 1
    action: PartAction = PartAction.INSPECTED


class Measurement(BaseModel):
    name: str = ""
    value: float | None = None
    unit: str = ""
    spec_min: float | None = None
    spec_max: float | None = None
    in_spec: bool | None = None

    @model_validator(mode="after")
    def compute_in_spec(self) -> "Measurement":
        if self.value is not None and (self.spec_min is not None or self.spec_max is not None):
            above_min = self.spec_min is None or self.value >= self.spec_min
            below_max = self.spec_max is None or self.value <= self.spec_max
            self.in_spec = above_min and below_max
        return self


ATA_CHAPTERS: dict[str, str] = {
    "05": "Time Limits/Maintenance Checks",
    "12": "Servicing",
    "20": "Standard Practices",
    "21": "Air Conditioning",
    "22": "Auto Flight",
    "23": "Communications",
    "24": "Electrical Power",
    "25": "Equipment/Furnishings",
    "26": "Fire Protection",
    "27": "Flight Controls",
    "28": "Fuel",
    "29": "Hydraulic Power",
    "30": "Ice and Rain Protection",
    "31": "Instruments",
    "32": "Landing Gear",
    "33": "Lights",
    "34": "Navigation",
    "35": "Oxygen",
    "36": "Pneumatic",
    "38": "Water/Waste",
    "49": "Airborne Auxiliary Power",
    "51": "Structures",
    "52": "Doors",
    "53": "Fuselage",
    "54": "Nacelles/Pylons",
    "55": "Stabilizers",
    "56": "Windows",
    "57": "Wings",
    "71": "Powerplant",
    "72": "Engine",
    "73": "Engine Fuel and Control",
    "74": "Ignition",
    "75": "Air",
    "76": "Engine Controls",
    "77": "Engine Indicating",
    "78": "Exhaust",
    "79": "Oil",
    "80": "Starting",
}

SAFETY_TRIGGER_WORDS = [
    "crack", "cracked", "cracking",
    "corrosion beyond limits", "severe corrosion", "corrosion exceeding",
    "fuel leak", "hydraulic leak", "oil leak",
    "control surface", "flight control",
    "fod", "foreign object",
    "structural failure", "structural damage",
    "fire damage", "burn", "overheat",
    "delamination",
]


class MaintenanceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    aircraft_registration: str = ""
    ata_chapter_code: str = ""
    ata_chapter_name: str = ""
    component: str = ""
    zone: str = ""
    discrepancy: str = ""
    corrective_action: str = ""
    parts: list[PartRecord] = Field(default_factory=list)
    measurements: list[Measurement] = Field(default_factory=list)
    severity: Severity = Severity.ROUTINE
    ops_check_performed: bool = False
    ops_check_result: str = ""
    technician_id: str = ""
    work_order_id: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: dict[str, float] = Field(default_factory=dict)
    raw_transcript: str = ""
    requires_signoff: bool = False
    signoff_status: SignoffStatus = SignoffStatus.PENDING
    signoff_by: str = ""
    signoff_at: datetime | None = None
    escalated: bool = False
    escalation_reason: str = ""
    session_id: str = ""
    language_detected: str = "en"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("ata_chapter_code")
    @classmethod
    def validate_ata_chapter(cls, v: str) -> str:
        if v and not (v.isdigit() and 2 <= len(v) <= 3):
            raise ValueError(f"ATA chapter code must be 2-3 digits, got '{v}'")
        return v

    @field_validator("aircraft_registration")
    @classmethod
    def validate_registration(cls, v: str) -> str:
        if v:
            v = v.upper().strip()
        return v

    def resolve_ata_name(self) -> None:
        if self.ata_chapter_code and not self.ata_chapter_name:
            self.ata_chapter_name = ATA_CHAPTERS.get(self.ata_chapter_code, "")

    def required_fields_missing(self) -> list[str]:
        missing = []
        required = {
            "aircraft_registration": self.aircraft_registration,
            "ata_chapter_code": self.ata_chapter_code,
            "discrepancy": self.discrepancy,
            "corrective_action": self.corrective_action,
            "technician_id": self.technician_id,
        }
        for field_name, value in required.items():
            if not value:
                missing.append(field_name)
        return missing

    def check_safety_triggers(self) -> list[str]:
        triggers_found = []
        text = f"{self.discrepancy} {self.corrective_action}".lower()
        for trigger in SAFETY_TRIGGER_WORDS:
            if trigger in text:
                triggers_found.append(trigger)
        return triggers_found

    def should_escalate(self) -> bool:
        if self.severity == Severity.CAT_A:
            return True
        return len(self.check_safety_triggers()) > 0


class MaintenanceRecordCreate(BaseModel):
    aircraft_registration: str = ""
    ata_chapter_code: str = ""
    component: str = ""
    zone: str = ""
    discrepancy: str = ""
    corrective_action: str = ""
    parts: list[PartRecord] = Field(default_factory=list)
    measurements: list[Measurement] = Field(default_factory=list)
    severity: Severity = Severity.ROUTINE
    ops_check_performed: bool = False
    ops_check_result: str = ""
    technician_id: str = ""
    work_order_id: str = ""
    raw_transcript: str = ""
    session_id: str = ""
    language_detected: str = "en"


class MaintenanceRecordUpdate(BaseModel):
    aircraft_registration: Optional[str] = None
    ata_chapter_code: Optional[str] = None
    ata_chapter_name: Optional[str] = None
    component: Optional[str] = None
    zone: Optional[str] = None
    discrepancy: Optional[str] = None
    corrective_action: Optional[str] = None
    parts: Optional[list[PartRecord]] = None
    measurements: Optional[list[Measurement]] = None
    severity: Optional[Severity] = None
    ops_check_performed: Optional[bool] = None
    ops_check_result: Optional[str] = None
    technician_id: Optional[str] = None
    work_order_id: Optional[str] = None
    confidence: Optional[dict[str, float]] = None
    requires_signoff: Optional[bool] = None
    signoff_status: Optional[SignoffStatus] = None
    signoff_by: Optional[str] = None
    signoff_at: Optional[datetime] = None
    escalated: Optional[bool] = None
    escalation_reason: Optional[str] = None
    language_detected: Optional[str] = None


class RecordResponse(BaseModel):
    record: MaintenanceRecord
    message: str = ""
    warnings: list[str] = Field(default_factory=list)


class FollowUpQuestion(BaseModel):
    field_name: str
    question_text: str
    language: str = "en"


class AgentMessage(BaseModel):
    type: str  # transcript, follow_up, state_change, record_update, escalation, history, manual_answer, error, metrics
    content: str = ""
    record: Optional[MaintenanceRecord] = None
    state: Optional[AgentState] = None
    follow_up: Optional[FollowUpQuestion] = None
    data: Optional[dict[str, Any]] = None
