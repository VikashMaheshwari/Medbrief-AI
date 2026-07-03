"use client";

import { useState, useEffect } from "react";
import { ChevronDown, Database } from "lucide-react";
import { Card, VerifiedBadge, Skeleton, Eyebrow } from "./ui";
import { API } from "../lib/api";

interface MedRow { DESCRIPTION: string; START?: string; REASONDESCRIPTION?: string }
interface AllergyRow { DESCRIPTION: string; DESCRIPTION1?: string; SEVERITY1?: string }
interface ConditionRow { DESCRIPTION: string; START?: string }
interface VitalRow { DESCRIPTION: string; VALUE?: string | number; UNITS?: string; DATE?: string }
interface ProcedureRow { DESCRIPTION: string; START?: string }

interface RecordData {
  name: string;
  dob: string;
  gender: string;
  active_medications: MedRow[];
  allergies: AllergyRow[];
  active_conditions: ConditionRow[];
  recent_vitals: VitalRow[];
  past_procedures: ProcedureRow[];
  last_encounter: string;
}

function show(v: unknown): string {
  const s = String(v ?? "").trim();
  return s && s.toLowerCase() !== "nan" ? s : "";
}
function dateOnly(v: unknown): string {
  const s = show(v);
  return s ? s.slice(0, 10) : "";
}

function Section({ title, count, children, defaultOpen = false }: {
  title: string; count: number; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-slate-100 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-slate-50/70 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset"
      >
        <span className="text-[13px] font-bold text-slate-800">{title}</span>
        <span className="font-mono text-[11px] font-bold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded tabular-nums">{count}</span>
        <span className="ml-auto flex items-center gap-2">
          <VerifiedBadge label="Source verified" />
          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`} />
        </span>
      </button>
      {open && <div className="px-5 pb-4">{children}</div>}
    </div>
  );
}

export default function RecordAccordion({ patientId }: { patientId: string }) {
  const [record, setRecord] = useState<RecordData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setRecord(null);
    setFailed(false);
    fetch(`${API}/patient/${patientId}`)
      .then(r => { if (!r.ok) throw new Error(); return r.json(); })
      .then(setRecord)
      .catch(() => setFailed(true));
  }, [patientId]);

  if (failed) return null;

  if (!record) {
    return (
      <Card className="p-5 space-y-3">
        <Skeleton className="h-5 w-56" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-4/5" />
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
          <Database className="w-4.5 h-4.5 text-slate-500" />
        </div>
        <div>
          <Eyebrow>Raw patient record</Eyebrow>
          <p className="text-slate-900 font-bold text-[15px] mt-0.5">
            Source data · DOB <span className="font-mono font-semibold">{show(record.dob)}</span> · {record.gender === "M" ? "Male" : "Female"}
          </p>
        </div>
        <span className="ml-auto font-mono text-[11px] font-semibold text-slate-400 bg-slate-50 border border-slate-100 px-2 py-1 rounded-lg hidden sm:block">
          {patientId.slice(0, 8)}
        </span>
      </div>

      <Section title="Allergies" count={record.allergies.length} defaultOpen={record.allergies.length > 0}>
        {record.allergies.length === 0 ? (
          <p className="text-slate-400 text-[13px] font-medium">None documented</p>
        ) : (
          <div className="space-y-1.5">
            {record.allergies.map((a, i) => (
              <div key={i} className="flex items-baseline gap-2.5 text-[13px]">
                <span className="text-slate-900 font-semibold">{show(a.DESCRIPTION)}</span>
                {show(a.SEVERITY1) && (
                  <span className="text-[#DC2626] font-bold uppercase text-[10px] bg-red-50 border border-red-200 px-1.5 py-0.5 rounded">
                    {show(a.SEVERITY1)}
                  </span>
                )}
                {show(a.DESCRIPTION1) && <span className="text-slate-500">{show(a.DESCRIPTION1)}</span>}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Medications" count={record.active_medications.length}>
        <div className="space-y-1.5">
          {record.active_medications.map((m, i) => (
            <div key={i} className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-slate-800 font-medium min-w-0">
                {show(m.DESCRIPTION)}
                {show(m.REASONDESCRIPTION) && <span className="text-slate-400"> — {show(m.REASONDESCRIPTION)}</span>}
              </span>
              <span className="font-mono text-[11px] text-slate-400 shrink-0 tabular-nums">{dateOnly(m.START)}</span>
            </div>
          ))}
          {record.active_medications.length === 0 && <p className="text-slate-400 text-[13px]">None documented</p>}
        </div>
      </Section>

      <Section title="Conditions" count={record.active_conditions.length}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1.5">
          {record.active_conditions.map((c, i) => (
            <div key={i} className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-slate-800 font-medium min-w-0">{show(c.DESCRIPTION)}</span>
              <span className="font-mono text-[11px] text-slate-400 shrink-0 tabular-nums">{dateOnly(c.START)}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Vitals & labs" count={record.recent_vitals.length}>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-left text-slate-400">
                <th className="font-bold uppercase text-[10px] tracking-wider pb-2">Test</th>
                <th className="font-bold uppercase text-[10px] tracking-wider pb-2 text-right">Value</th>
                <th className="font-bold uppercase text-[10px] tracking-wider pb-2 pl-4">Units</th>
                <th className="font-bold uppercase text-[10px] tracking-wider pb-2 pl-4">Date</th>
              </tr>
            </thead>
            <tbody>
              {record.recent_vitals.map((v, i) => (
                <tr key={i} className="border-t border-slate-50">
                  <td className="py-1.5 text-slate-800 font-medium">{show(v.DESCRIPTION)}</td>
                  <td className="py-1.5 font-mono font-bold text-slate-900 text-right tabular-nums">{show(v.VALUE)}</td>
                  <td className="py-1.5 font-mono text-slate-400 pl-4">{show(v.UNITS)}</td>
                  <td className="py-1.5 font-mono text-slate-400 pl-4 tabular-nums">{dateOnly(v.DATE)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Procedures" count={record.past_procedures.length}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1.5">
          {record.past_procedures.map((p, i) => (
            <div key={i} className="flex items-baseline justify-between gap-3 text-[13px]">
              <span className="text-slate-800 font-medium min-w-0">{show(p.DESCRIPTION)}</span>
              <span className="font-mono text-[11px] text-slate-400 shrink-0 tabular-nums">{dateOnly(p.START)}</span>
            </div>
          ))}
        </div>
      </Section>

      {show(record.last_encounter) && show(record.last_encounter) !== "{}" && (
        <div className="px-5 py-3 bg-slate-50/60 border-t border-slate-100">
          <p className="text-[13px] text-slate-500">
            <span className="font-bold text-slate-700">Last encounter:</span>{" "}
            <span className="font-mono text-[12px]">{show(record.last_encounter)}</span>
          </p>
        </div>
      )}
    </Card>
  );
}
