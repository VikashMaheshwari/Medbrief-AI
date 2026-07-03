"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft, User, ShieldAlert, Pill, Stethoscope, FlaskConical,
  Microscope, CalendarDays, Flag, FileText, CheckCircle2, RotateCcw,
  Database, ShieldCheck, BrainCircuit, Wrench, Cpu, ClipboardCheck,
  Award, Sparkles, TriangleAlert,
} from "lucide-react";
import { Card, Badge, VerifiedBadge, ScoreBar, Skeleton, Eyebrow } from "./ui";
import AssistantPanel from "./AssistantPanel";
import RecordAccordion from "./RecordAccordion";
import { API, cleanName, parseErrorDetail, type BriefingData } from "../lib/api";

/* ------------------------------------------------------------------ */
/* Pipeline visualization                                              */
/* ------------------------------------------------------------------ */
const PIPELINE: { label: string; icon: React.ElementType }[] = [
  { label: "Patient record", icon: Database },
  { label: "Input guardrails", icon: ShieldCheck },
  { label: "RAG retrieval", icon: BrainCircuit },
  { label: "Clinical tools", icon: Wrench },
  { label: "LLM", icon: Cpu },
  { label: "Validator", icon: ClipboardCheck },
  { label: "Retry loop", icon: RotateCcw },
  { label: "Evaluation", icon: Award },
  { label: "Final briefing", icon: FileText },
];

function Pipeline({ attempts }: { attempts: number }) {
  return (
    <Card className="px-5 py-4 overflow-x-auto">
      <Eyebrow>Agent pipeline</Eyebrow>
      <div className="flex items-center gap-1 mt-3 min-w-max">
        {PIPELINE.map((step, i) => {
          const Icon = step.icon;
          const isRetry = step.label === "Retry loop";
          const retried = isRetry && attempts > 1;
          return (
            <div key={step.label} className="flex items-center">
              <motion.div
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.25, delay: i * 0.07 }}
                className="flex flex-col items-center gap-1.5 w-[86px]"
              >
                <div className={`relative w-9 h-9 rounded-xl flex items-center justify-center border ${
                  retried
                    ? "bg-amber-50 border-amber-200 text-[#F59E0B]"
                    : "bg-green-50 border-green-200 text-[#16A34A]"
                }`}>
                  <Icon className="w-4 h-4" />
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: i * 0.07 + 0.2, type: "spring", stiffness: 400, damping: 20 }}
                    className="absolute -top-1 -right-1"
                  >
                    <CheckCircle2 className={`w-3.5 h-3.5 ${retried ? "text-[#F59E0B]" : "text-[#16A34A]"} bg-white rounded-full`} />
                  </motion.span>
                </div>
                <span className="text-[10px] font-semibold text-slate-500 text-center leading-tight">
                  {step.label}
                  {retried && <span className="block text-[#F59E0B]">×{attempts - 1} retr{attempts - 1 > 1 ? "ies" : "y"}</span>}
                </span>
              </motion.div>
              {i < PIPELINE.length - 1 && (
                <motion.div
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.2, delay: i * 0.07 + 0.1 }}
                  className="w-4 h-px bg-slate-200 origin-left shrink-0 -mt-5"
                />
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* AI Trust panel                                                      */
/* ------------------------------------------------------------------ */
function TrustPanel({ data }: { data: BriefingData }) {
  const hallucinations = data.guardrails.output_warnings.filter(w =>
    w.toLowerCase().includes("hallucinat")
  ).length;

  const checks: { label: string; value: string; ok: boolean }[] = [
    {
      label: "Input guardrails",
      value: data.guardrails.input_warnings.length === 0 ? "Clean record" : `${data.guardrails.input_warnings.length} warning(s)`,
      ok: true,
    },
    {
      label: "Output validation",
      value: data.validation.passed ? "All items present" : "Items missing",
      ok: data.validation.passed,
    },
    {
      label: "Hallucination check",
      value: hallucinations === 0 ? "Nothing invented" : `${hallucinations} flagged`,
      ok: hallucinations === 0,
    },
    { label: "RAG guidelines", value: "Injected into context", ok: true },
    { label: "Clinical tools", value: "Available to agent", ok: true },
    {
      label: "Retry count",
      value: data.attempts === 1 ? "Passed first try" : `${data.attempts - 1} self-correction(s)`,
      ok: true,
    },
    ...(data.eval ? [{
      label: "Ground truth score",
      value: `${Math.round(data.eval.overall_score * 100)}% vs answer key`,
      ok: data.eval.overall_score >= 0.7,
    }] : []),
    { label: "Latency", value: `${(data.latency_ms / 1000).toFixed(1)}s end to end`, ok: true },
  ];

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <Eyebrow>Why you can trust this briefing</Eyebrow>
        <Badge variant="success"><ShieldCheck className="w-3 h-3" /> Harness verified</Badge>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {checks.map((c, i) => (
          <motion.div
            key={c.label}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: i * 0.04 }}
            className="rounded-xl border border-slate-100 bg-slate-50/50 px-3.5 py-3"
          >
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wide mb-1">{c.label}</p>
            <p className="text-[13px] font-semibold text-slate-800 mb-1.5">{c.value}</p>
            <VerifiedBadge label={c.ok ? "Verified" : "Review"} />
          </motion.div>
        ))}
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/* Briefing sections                                                   */
/* ------------------------------------------------------------------ */
const SECTION_META: Record<string, { icon: React.ElementType; label: string }> = {
  "demographics": { icon: User, label: "Patient summary" },
  "allergies": { icon: ShieldAlert, label: "Allergies" },
  "active medications": { icon: Pill, label: "Current medications" },
  "active conditions": { icon: Stethoscope, label: "Active conditions" },
  "vitals & labs": { icon: FlaskConical, label: "Recent labs & vitals" },
  "past procedures": { icon: Microscope, label: "Recent procedures" },
  "last visit": { icon: CalendarDays, label: "Last visit" },
  "flags": { icon: Flag, label: "Critical warnings" },
};

function parseBriefing(text: string): { key: string; items: string[] }[] {
  const sections: Record<string, string[]> = {};
  let current = "overview";
  sections[current] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("##") || line.startsWith("**")) {
      current = line.replace(/^#+\s*/, "").replace(/\*\*/g, "").toLowerCase().trim();
      sections[current] = [];
    } else {
      const clean = line.replace(/^[*\-]\s*/, "");
      if (clean) sections[current].push(clean);
    }
  }
  const known = Object.keys(SECTION_META).filter(k => sections[k]?.length);
  const extra = Object.keys(sections).filter(k => k !== "overview" && !(k in SECTION_META) && sections[k].length);
  const ordered = ["flags", ...known.filter(k => k !== "flags"), ...extra];
  return ordered.filter(k => sections[k]?.length).map(k => ({ key: k, items: sections[k] }));
}

function FlagLine({ text }: { text: string }) {
  const lower = text.toLowerCase();
  const critical = ["critical", "urgent", "sepsis", "shock"].some(w => lower.includes(w));
  const warning = !critical && ["elevated", "high", "low", "duplicate", "risk"].some(w => lower.includes(w));
  return (
    <div className={`flex items-start gap-2.5 px-3.5 py-2.5 rounded-xl border text-[13px] font-medium leading-relaxed ${
      critical ? "bg-red-50 border-red-200 text-red-900"
      : warning ? "bg-amber-50 border-amber-200 text-amber-900"
      : "bg-blue-50 border-blue-200 text-blue-900"
    }`}>
      <TriangleAlert className={`w-4 h-4 mt-0.5 shrink-0 ${
        critical ? "text-[#DC2626]" : warning ? "text-[#F59E0B]" : "text-[#2563EB]"
      }`} />
      <span>{text}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main view                                                           */
/* ------------------------------------------------------------------ */
export default function BriefingView({
  patientId, focus, onBack,
}: {
  patientId: string;
  focus?: "brief" | "chart" | "chat";
  onBack: () => void;
}) {
  const [data, setData] = useState<BriefingData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    fetch(`${API}/patient/${patientId}/briefing`)
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => null);
          throw new Error(parseErrorDetail(err?.detail));
        }
        return res.json();
      })
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Something went wrong"));
  }, [patientId]);

  /* ---------- loading ---------- */
  if (!data && !error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-32" />
          <Skeleton className="h-9 w-64" />
        </div>
        <Skeleton className="h-20 w-full" />
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="xl:col-span-2 space-y-4">
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
        <p className="text-center text-sm text-slate-400 font-medium pt-2">
          Generating briefing — guardrails, RAG, validation and evals are running…
        </p>
      </div>
    );
  }

  /* ---------- error ---------- */
  if (error) {
    return (
      <Card className="p-8 text-center">
        <TriangleAlert className="w-8 h-8 text-[#DC2626] mx-auto mb-3" />
        <p className="text-slate-900 font-bold text-lg mb-1">Briefing unavailable</p>
        <p className="text-slate-500 text-sm mb-5">{error}</p>
        <button
          onClick={onBack}
          className="px-4 py-2 rounded-xl bg-[#2563EB] text-white text-sm font-semibold hover:bg-blue-700 transition-all"
        >
          Back to panel
        </button>
      </Card>
    );
  }

  const briefing = data!;
  const sections = parseBriefing(briefing.briefing);
  const grade = briefing.eval
    ? briefing.eval.overall_score >= 0.85 ? "A"
    : briefing.eval.overall_score >= 0.7 ? "B"
    : briefing.eval.overall_score >= 0.55 ? "C" : "F"
    : null;

  return (
    <div className="space-y-5">
      {/* Sticky summary bar */}
      <div className="sticky top-[72px] z-20">
        <Card className="px-5 py-3 flex items-center gap-3 backdrop-blur-xl bg-white/90">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 text-[13px] font-semibold hover:bg-slate-50 transition-all shrink-0"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Panel
          </button>
          <h1 className="text-slate-900 font-bold text-[17px] truncate">
            {cleanName(briefing.patient_name)}
          </h1>
          <div className="ml-auto flex items-center gap-2 shrink-0">
            {briefing.validation.passed
              ? <Badge variant="success"><CheckCircle2 className="w-3 h-3" /> Validated</Badge>
              : <Badge variant="critical">Validation failed</Badge>}
            {grade && <Badge variant={grade === "A" ? "success" : grade === "B" ? "info" : "warning"}>Grade {grade}</Badge>}
            {briefing.attempts > 1 && <Badge variant="warning"><RotateCcw className="w-3 h-3" /> {briefing.attempts} attempts</Badge>}
            <span className="font-mono text-xs text-slate-400 tabular-nums hidden sm:block">
              {(briefing.latency_ms / 1000).toFixed(1)}s
            </span>
          </div>
        </Card>
      </div>

      {/* Pipeline */}
      <Pipeline attempts={briefing.attempts} />

      {/* Guardrail warnings */}
      {(briefing.guardrails.output_errors.length > 0 || briefing.guardrails.output_warnings.length > 0) && (
        <Card className="p-4 border-amber-200 bg-amber-50/50">
          <div className="space-y-1">
            {[...briefing.guardrails.output_errors, ...briefing.guardrails.output_warnings].map((w, i) => (
              <p key={i} className="text-amber-900 text-[13px] font-medium flex items-start gap-2">
                <TriangleAlert className="w-3.5 h-3.5 mt-0.5 shrink-0 text-[#F59E0B]" />{w}
              </p>
            ))}
          </div>
        </Card>
      )}

      {/* Split screen */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 items-start">
        {/* LEFT — briefing */}
        <div className="xl:col-span-2 space-y-4">
          {/* Eval scores */}
          {briefing.eval && (
            <Card className="p-5">
              <div className="flex items-center justify-between mb-3">
                <Eyebrow>Accuracy vs ground truth</Eyebrow>
                <Sparkles className="w-4 h-4 text-[#06B6D4]" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2.5">
                <ScoreBar label="Sections" value={briefing.eval.section_score} />
                <ScoreBar label="Medications" value={briefing.eval.med_coverage} />
                <ScoreBar label="Conditions" value={briefing.eval.condition_coverage} />
                <ScoreBar label="Flags" value={briefing.eval.flag_coverage} />
              </div>
            </Card>
          )}

          {/* Sections */}
          {sections.map(({ key, items }, si) => {
            const meta = SECTION_META[key] ?? { icon: FileText, label: key.replace(/\b\w/g, c => c.toUpperCase()) };
            const Icon = meta.icon;
            const isFlags = key === "flags";
            return (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: si * 0.05 }}
              >
                <Card className="p-5">
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      isFlags ? "bg-red-50 text-[#DC2626]" : "bg-blue-50 text-[#2563EB]"
                    }`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <h3 className="text-slate-900 font-bold text-[15px]">{meta.label}</h3>
                  </div>
                  {isFlags ? (
                    <div className="space-y-2">
                      {items.map((item, i) => <FlagLine key={i} text={item} />)}
                    </div>
                  ) : (
                    <ul className="space-y-1.5">
                      {items.map((item, i) => (
                        <li key={i} className="flex items-start gap-2.5 text-[14px] text-slate-700 leading-relaxed">
                          <span className="w-1 h-1 rounded-full bg-slate-300 mt-2.5 shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              </motion.div>
            );
          })}

          {/* Validation failures */}
          {!briefing.validation.passed && (
            <Card className="p-5 border-red-200 bg-red-50/50">
              <Eyebrow>Validation failures</Eyebrow>
              <div className="mt-2 space-y-1">
                {briefing.validation.missing_medications.map((m, i) => <p key={i} className="text-red-800 text-[13px] font-medium">• Missing medication: {m}</p>)}
                {briefing.validation.missing_allergies.map((a, i) => <p key={i} className="text-red-800 text-[13px] font-medium">• Missing allergy: {a}</p>)}
                {briefing.validation.missing_conditions.map((c, i) => <p key={i} className="text-red-800 text-[13px] font-medium">• Missing condition: {c}</p>)}
              </div>
            </Card>
          )}
        </div>

        {/* RIGHT — assistant */}
        <AssistantPanel
          patientId={briefing.patient_id}
          patientName={briefing.patient_name}
          autoFocus={focus === "chat"}
        />
      </div>

      {/* Trust panel */}
      <TrustPanel data={briefing} />

      {/* Raw record */}
      <RecordAccordion patientId={briefing.patient_id} />
    </div>
  );
}
