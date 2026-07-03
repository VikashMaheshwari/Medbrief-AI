"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Search, Zap, FolderOpen, MessageSquare, ShieldAlert, Timer } from "lucide-react";
import { Card, Badge } from "./ui";
import {
  cleanName, acuity, estReviewMinutes, chartCompleteness,
  ACUITY_LABEL, ACUITY_DOT,
  type PanelPatient, type RecentPatient, type Acuity,
} from "../lib/api";

type Filter = "all" | Acuity | "recent";
type Sort = "severity" | "age" | "name";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "critical", label: "Critical" },
  { id: "complex", label: "High risk" },
  { id: "stable", label: "Stable" },
  { id: "recent", label: "Recently reviewed" },
];

const SEVERITY_ORDER: Record<Acuity, number> = { critical: 0, complex: 1, stable: 2, deceased: 3 };

export default function PanelView({
  patients, recent, onOpenPatient,
}: {
  patients: PanelPatient[];
  recent: RecentPatient[];
  onOpenPatient: (id: string, focus?: "brief" | "chart" | "chat") => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [sort, setSort] = useState<Sort>("severity");

  const recentIds = useMemo(() => new Set(recent.map(r => r.patient_id)), [recent]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = patients.filter(p => !p.deceased);

    if (q) list = list.filter(p => cleanName(p.name).toLowerCase().includes(q));
    if (filter === "recent") list = list.filter(p => recentIds.has(p.patient_id));
    else if (filter !== "all") list = list.filter(p => acuity(p) === filter);

    const sorted = [...list];
    if (sort === "severity") {
      sorted.sort((a, b) =>
        SEVERITY_ORDER[acuity(a)] - SEVERITY_ORDER[acuity(b)] ||
        b.active_conditions - a.active_conditions
      );
    } else if (sort === "age") {
      sorted.sort((a, b) => (b.age ?? 0) - (a.age ?? 0));
    } else {
      sorted.sort((a, b) => cleanName(a.name).localeCompare(cleanName(b.name)));
    }
    return sorted;
  }, [patients, query, filter, sort, recentIds]);

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name…"
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white border border-slate-200 text-[15px] text-slate-900 placeholder-slate-400 shadow-sm focus:outline-none focus:border-[#2563EB] focus:ring-2 focus:ring-blue-100 transition-all"
          />
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {FILTERS.map(f => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`px-3.5 py-1.5 rounded-full text-[13px] font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                filter === f.id
                  ? "bg-slate-900 text-white shadow-sm"
                  : "bg-white border border-slate-200 text-slate-500 hover:text-slate-900 hover:border-slate-300"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          className="ml-auto px-3 py-2 rounded-xl bg-white border border-slate-200 text-[13px] font-semibold text-slate-600 shadow-sm focus:outline-none focus:border-[#2563EB]"
        >
          <option value="severity">Sort · Severity</option>
          <option value="age">Sort · Age</option>
          <option value="name">Sort · Name</option>
        </select>
      </div>

      <p className="text-[13px] text-slate-400 font-medium">
        {visible.length} patient{visible.length === 1 ? "" : "s"}
      </p>

      {/* Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {visible.map((p, i) => {
          const level = acuity(p);
          const completeness = chartCompleteness(p);
          return (
            <motion.div
              key={p.patient_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: Math.min(i * 0.03, 0.3) }}
            >
              <Card className="group relative overflow-hidden" lift>
                <div className="p-5">
                  {/* Top row */}
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="min-w-0">
                      <h3 className="text-slate-900 font-bold text-[16px] truncate">{cleanName(p.name)}</h3>
                      <p className="font-mono text-[13px] text-slate-400 mt-0.5">
                        {p.age ?? "—"} · {p.gender === "M" ? "Male" : "Female"}
                      </p>
                    </div>
                    <span className="flex items-center gap-1.5 shrink-0 px-2 py-1 rounded-md bg-slate-50 border border-slate-100">
                      <span className={`w-2 h-2 rounded-full ${ACUITY_DOT[level]}`} />
                      <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wide">
                        {ACUITY_LABEL[level]}
                      </span>
                    </span>
                  </div>

                  {/* Primary diagnosis */}
                  <p className={`text-[13px] font-medium truncate mb-3 ${
                    level === "critical" ? "text-[#DC2626]" : "text-slate-600"
                  }`}>
                    {p.critical[0] || p.primary_condition || "No active diagnoses"}
                  </p>

                  {/* Data row */}
                  <div className="flex items-center gap-2 flex-wrap mb-3">
                    <Badge variant="neutral">{p.active_conditions} conditions</Badge>
                    <Badge variant="neutral">{p.active_medications} meds</Badge>
                    {p.allergies > 0 && (
                      <Badge variant="warning">
                        <ShieldAlert className="w-3 h-3" />
                        {p.allergies} allerg{p.allergies > 1 ? "ies" : "y"}
                      </Badge>
                    )}
                    {recentIds.has(p.patient_id) && <Badge variant="info">Reviewed</Badge>}
                  </div>

                  {/* Footer row */}
                  <div className="flex items-center justify-between text-[12px] text-slate-400 font-medium">
                    <span className="flex items-center gap-1">
                      <Timer className="w-3.5 h-3.5" />
                      chart ≈ {estReviewMinutes(p)} min → brief ≈ 2 min
                    </span>
                    <span className="font-mono tabular-nums">chart data {completeness}%</span>
                  </div>
                </div>

                {/* Hover actions */}
                <div className="absolute inset-x-0 bottom-0 translate-y-full group-hover:translate-y-0 transition-transform duration-200 ease-out bg-white/95 backdrop-blur border-t border-slate-100 px-3 py-2.5 flex gap-2">
                  <button
                    onClick={() => onOpenPatient(p.patient_id, "brief")}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#2563EB] text-white text-[13px] font-semibold hover:bg-blue-700 active:scale-[0.98] transition-all shadow-sm"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    Quick brief
                  </button>
                  <button
                    onClick={() => onOpenPatient(p.patient_id, "chart")}
                    className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 text-slate-600 text-[13px] font-semibold hover:bg-slate-50 active:scale-[0.98] transition-all"
                  >
                    <FolderOpen className="w-3.5 h-3.5" />
                    Chart
                  </button>
                  <button
                    onClick={() => onOpenPatient(p.patient_id, "chat")}
                    className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border border-slate-200 text-slate-600 text-[13px] font-semibold hover:bg-slate-50 active:scale-[0.98] transition-all"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                    Ask AI
                  </button>
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {visible.length === 0 && (
        <Card className="py-14 text-center">
          <p className="text-slate-500 text-[15px] font-medium">No patients match your filters.</p>
          <p className="text-slate-400 text-sm mt-1">Try clearing the search or choosing “All”.</p>
        </Card>
      )}
    </div>
  );
}
