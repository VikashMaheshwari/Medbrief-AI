"use client";

import { motion } from "framer-motion";
import {
  Users, AlertTriangle, Layers, FileClock, Gauge, FileCheck2, ShieldCheck, BadgeCheck,
} from "lucide-react";
import { Card, Counter, Eyebrow, Badge } from "./ui";
import {
  acuity, cleanName, type PanelPatient, type Metrics, type RecentPatient,
} from "../lib/api";

/* ------------------------------------------------------------------ */
/* Stat card                                                           */
/* ------------------------------------------------------------------ */
function Stat({
  icon: Icon, label, value, decimals = 0, suffix = "", tone = "default", delay = 0,
}: {
  icon: React.ElementType; label: string; value: number;
  decimals?: number; suffix?: string; tone?: "default" | "critical" | "warning" | "success"; delay?: number;
}) {
  const tones = {
    default: { ring: "bg-blue-50 text-[#2563EB]", num: "text-slate-900" },
    critical: { ring: "bg-red-50 text-[#DC2626]", num: "text-[#DC2626]" },
    warning: { ring: "bg-amber-50 text-[#F59E0B]", num: "text-slate-900" },
    success: { ring: "bg-green-50 text-[#16A34A]", num: "text-slate-900" },
  }[tone];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
    >
      <Card className="px-5 py-4 flex items-center gap-4" lift>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${tones.ring}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="min-w-0">
          <Counter value={value} decimals={decimals} suffix={suffix} className={`font-mono text-2xl font-bold leading-none tabular-nums ${tones.num}`} />
          <p className="text-slate-500 text-[13px] font-medium mt-1 truncate">{label}</p>
        </div>
      </Card>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/* Charts (shared with Metrics view)                                   */
/* ------------------------------------------------------------------ */
export function LatencyChart({ metrics }: { metrics: Metrics | null }) {
  const points = (metrics?.recent_requests ?? []).map(r => r.latency_ms / 1000);
  if (points.length < 2) {
    return <p className="text-sm text-slate-400 py-8 text-center">Generate a few briefings to see the latency trend.</p>;
  }
  const w = 320, h = 96, pad = 8;
  const max = Math.max(...points) * 1.15;
  const step = (w - pad * 2) / (points.length - 1);
  const xy = points.map((v, i) => [pad + i * step, h - pad - (v / max) * (h - pad * 2)]);
  const path = xy.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-24">
      <defs>
        <linearGradient id="latfill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2563EB" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#2563EB" stopOpacity="0" />
        </linearGradient>
      </defs>
      <motion.path
        d={`${path} L${xy[xy.length - 1][0]},${h} L${xy[0][0]},${h} Z`}
        fill="url(#latfill)"
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }}
      />
      <motion.path
        d={path} fill="none" stroke="#2563EB" strokeWidth="2" strokeLinecap="round"
        initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.8, ease: "easeOut" }}
      />
      {xy.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r="3" fill="#fff" stroke="#2563EB" strokeWidth="1.5" />
      ))}
    </svg>
  );
}

export function AccuracyChart({ metrics }: { metrics: Metrics | null }) {
  const scores = (metrics?.recent_requests ?? []).filter(r => r.eval_score >= 0);
  if (scores.length === 0) {
    return <p className="text-sm text-slate-400 py-8 text-center">No scored briefings yet.</p>;
  }
  return (
    <div className="flex items-end gap-2 h-24 pt-2">
      {scores.map((r, i) => {
        const pct = Math.round(r.eval_score * 100);
        const color = pct >= 85 ? "#16A34A" : pct >= 70 ? "#2563EB" : "#F59E0B";
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 min-w-0">
            <span className="font-mono text-[10px] font-bold" style={{ color }}>{pct}</span>
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: `${pct * 0.72}px` }}
              transition={{ duration: 0.5, delay: i * 0.06, ease: "easeOut" }}
              className="w-full max-w-8 rounded-t-md"
              style={{ backgroundColor: color, opacity: 0.85 }}
            />
          </div>
        );
      })}
    </div>
  );
}

export function AcuityChart({ patients }: { patients: PanelPatient[] }) {
  const living = patients.filter(p => !p.deceased);
  const rows = [
    { label: "Critical", n: living.filter(p => acuity(p) === "critical").length, color: "#DC2626" },
    { label: "High risk", n: living.filter(p => acuity(p) === "complex").length, color: "#F59E0B" },
    { label: "Stable", n: living.filter(p => acuity(p) === "stable").length, color: "#16A34A" },
  ];
  const max = Math.max(...rows.map(r => r.n), 1);
  return (
    <div className="space-y-3 pt-1">
      {rows.map((r, i) => (
        <div key={r.label} className="flex items-center gap-3">
          <span className="text-xs font-medium text-slate-500 w-16 shrink-0">{r.label}</span>
          <div className="flex-1 h-5 bg-slate-50 rounded-md overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(r.n / max) * 100}%` }}
              transition={{ duration: 0.6, delay: i * 0.08, ease: "easeOut" }}
              className="h-full rounded-md"
              style={{ backgroundColor: r.color, opacity: 0.8 }}
            />
          </div>
          <span className="font-mono text-sm font-bold text-slate-700 w-8 text-right tabular-nums">{r.n}</span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Dashboard                                                           */
/* ------------------------------------------------------------------ */
export default function DashboardView({
  patients, metrics, recent, onOpenPatient,
}: {
  patients: PanelPatient[];
  metrics: Metrics | null;
  recent: RecentPatient[];
  onOpenPatient: (id: string) => void;
}) {
  const living = patients.filter(p => !p.deceased);
  const critical = living.filter(p => acuity(p) === "critical").length;
  const complex = living.filter(p => acuity(p) === "complex").length;
  const pending = Math.max(0, living.length - recent.length);

  const total = metrics?.total_requests ?? 0;
  const guardrailPass = total > 0
    ? Math.round(((total - (metrics?.total_guardrail_errors ?? 0)) / total) * 1000) / 10
    : 100;

  const nameFor = (id: string) => {
    const p = patients.find(x => x.patient_id === id);
    return p ? cleanName(p.name) : id.slice(0, 8);
  };

  return (
    <div className="space-y-8">
      {/* Summary grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat icon={Users} label="Patients on panel" value={living.length} delay={0} />
        <Stat icon={AlertTriangle} label="Critical patients" value={critical} tone="critical" delay={0.05} />
        <Stat icon={Layers} label="Complex cases" value={complex} tone="warning" delay={0.1} />
        <Stat icon={FileClock} label="Pending briefings" value={pending} delay={0.15} />
        <Stat icon={Gauge} label="Average AI latency" value={(metrics?.avg_latency_ms ?? 0) / 1000} decimals={1} suffix="s" delay={0.2} />
        <Stat icon={FileCheck2} label="Briefings generated" value={total} delay={0.25} />
        <Stat icon={BadgeCheck} label="Validation rate" value={metrics?.validation_pass_rate_pct ?? 0} decimals={1} suffix="%" tone="success" delay={0.3} />
        <Stat icon={ShieldCheck} label="Guardrail pass rate" value={guardrailPass} decimals={1} suffix="%" tone="success" delay={0.35} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="p-5">
          <Eyebrow>Panel acuity</Eyebrow>
          <AcuityChart patients={patients} />
        </Card>
        <Card className="p-5">
          <Eyebrow>Latency — recent briefings (s)</Eyebrow>
          <LatencyChart metrics={metrics} />
        </Card>
        <Card className="p-5">
          <Eyebrow>Briefing accuracy — ground truth %</Eyebrow>
          <AccuracyChart metrics={metrics} />
        </Card>
      </div>

      {/* Recent activity */}
      <Card className="overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <Eyebrow>Recent activity</Eyebrow>
        </div>
        {(metrics?.recent_requests ?? []).length === 0 ? (
          <p className="text-sm text-slate-400 px-5 py-8 text-center">
            No briefings yet today — open a patient from the panel to generate the first one.
          </p>
        ) : (
          <div className="divide-y divide-slate-50">
            {(metrics?.recent_requests ?? []).slice().reverse().map((r, i) => (
              <button
                key={i}
                onClick={() => onOpenPatient(r.patient_id)}
                className="w-full flex items-center gap-4 px-5 py-3 text-left hover:bg-slate-50/70 transition-colors"
              >
                <span className="text-sm font-semibold text-slate-900 flex-1 truncate">
                  {nameFor(r.patient_id)}
                </span>
                {r.validation_passed
                  ? <Badge variant="success">Validated</Badge>
                  : <Badge variant="critical">Failed</Badge>}
                {r.attempts > 1 && <Badge variant="warning">{r.attempts} attempts</Badge>}
                {r.eval_score >= 0 && (
                  <span className="font-mono text-xs font-bold text-slate-500 tabular-nums">
                    {Math.round(r.eval_score * 100)}%
                  </span>
                )}
                <span className="font-mono text-xs text-slate-400 tabular-nums w-14 text-right">
                  {(r.latency_ms / 1000).toFixed(1)}s
                </span>
              </button>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
