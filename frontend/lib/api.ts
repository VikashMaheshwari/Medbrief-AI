export const API = "http://localhost:8000";

export interface PanelPatient {
  patient_id: string;
  name: string;
  age: number | null;
  gender: string;
  deceased: boolean;
  active_conditions: number;
  active_medications: number;
  allergies: number;
  critical: string[];
  primary_condition?: string;
}

export interface Metrics {
  total_requests: number;
  chat_requests?: number;
  avg_latency_ms: number;
  avg_attempts: number;
  validation_pass_rate_pct: number;
  avg_eval_score_pct: number | null;
  retried_requests: number;
  total_guardrail_warnings: number;
  total_guardrail_errors: number;
  recent_requests?: RequestLogEntry[];
}

export interface RequestLogEntry {
  timestamp: string;
  patient_id: string;
  latency_ms: number;
  attempts: number;
  validation_passed: boolean;
  eval_score: number;
}

export interface RecentPatient {
  patient_id: string;
  name: string;
  viewed_at: string;
}

export interface BriefingData {
  patient_id: string;
  patient_name: string;
  briefing: string;
  attempts: number;
  latency_ms: number;
  blocked: boolean;
  guardrails: {
    input_warnings: string[];
    output_errors: string[];
    output_warnings: string[];
  };
  validation: {
    passed: boolean;
    missing_medications: string[];
    missing_allergies: string[];
    missing_conditions: string[];
  };
  eval: {
    overall_score: number;
    section_score: number;
    med_coverage: number;
    condition_coverage: number;
    flag_coverage: number;
  } | null;
}

// Synthea names carry numeric suffixes ("Dorsey40 Macejkovic424")
export function cleanName(name: string): string {
  return name.replace(/\d+/g, "");
}

export type Acuity = "critical" | "complex" | "stable" | "deceased";

export function acuity(p: PanelPatient): Acuity {
  if (p.deceased) return "deceased";
  if (p.critical.length > 0) return "critical";
  if (p.active_conditions >= 10 || p.allergies > 0) return "complex";
  return "stable";
}

export const ACUITY_LABEL: Record<Acuity, string> = {
  critical: "Critical",
  complex: "High risk",
  stable: "Stable",
  deceased: "Deceased",
};

export const ACUITY_DOT: Record<Acuity, string> = {
  critical: "bg-[#DC2626]",
  complex: "bg-[#F59E0B]",
  stable: "bg-[#16A34A]",
  deceased: "bg-slate-300",
};

// API error `detail` can be a string OR an object (guardrail blocks)
export function parseErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const d = detail as { errors?: string[] };
    if (d.errors?.length) return `Blocked by guardrails: ${d.errors.join("; ")}`;
    return JSON.stringify(detail);
  }
  return "Something went wrong";
}

// Chart review takes ~30s per problem; the brief is a fixed 2-minute read
export function estReviewMinutes(p: PanelPatient): number {
  return Math.max(3, Math.round((p.active_conditions * 0.5 + p.active_medications * 0.3)));
}

// Honest proxy for "AI confidence": how complete the source chart is
export function chartCompleteness(p: PanelPatient): number {
  let score = 55;
  if (p.active_conditions > 0) score += 15;
  if (p.active_medications > 0) score += 15;
  if (p.allergies > 0) score += 5;
  if (p.age != null) score += 10;
  return Math.min(100, score);
}
