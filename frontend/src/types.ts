export interface PartRecord {
  part_number: string;
  serial_number: string;
  qty: number;
  action: string;
}

export interface MeasurementRecord {
  name: string;
  value: number | null;
  unit: string;
  spec_min: number | null;
  spec_max: number | null;
  in_spec: boolean | null;
}

export interface MaintenanceRecord {
  id: string;
  aircraft_registration: string;
  ata_chapter_code: string;
  ata_chapter_name: string;
  component: string;
  zone: string;
  discrepancy: string;
  corrective_action: string;
  parts: PartRecord[];
  measurements: MeasurementRecord[];
  severity: string;
  ops_check_performed: boolean;
  ops_check_result: string;
  technician_id: string;
  work_order_id: string;
  confidence: Record<string, number>;
  raw_transcript: string;
  requires_signoff: boolean;
  signoff_status: string;
  signoff_by: string;
  signoff_at: string | null;
  escalated: boolean;
  escalation_reason: string;
  session_id: string;
  language_detected: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface FollowUp {
  field_name: string;
  question_text: string;
  language: string;
}

export type AgentState =
  | "LISTENING"
  | "EXTRACTING"
  | "CLARIFYING"
  | "ANSWERING_QUERY"
  | "HISTORY_READBACK"
  | "ESCALATION_CHECK"
  | "CONFIRMING"
  | "FINALIZED";

export interface AgentMessage {
  type: string;
  content: string;
  record?: MaintenanceRecord;
  state?: AgentState;
  follow_up?: FollowUp;
  data?: Record<string, unknown>;
}

export interface Metrics {
  total_records: number;
  escalated_records: number;
  escalation_rate: number;
  overdue_inspections: number;
  repeat_defects_found: number;
  avg_time_to_log_minutes: number;
}

export interface Aircraft {
  registration: string;
  type: string;
  operator: string;
  next_inspection_due: string | null;
}

export interface Notification {
  id: string;
  record_id: string;
  supervisor_id: string;
  channel: string;
  message: string;
  sent_at: string;
}
