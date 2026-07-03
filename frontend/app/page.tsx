"use client";

import { useState, useEffect, useCallback } from "react";
import { Clock, FileText, Settings as SettingsIcon, ShieldCheck, Cpu, BrainCircuit, Database } from "lucide-react";
import TopNav from "../components/TopNav";
import Sidebar, { type View } from "../components/Sidebar";
import CommandPalette from "../components/CommandPalette";
import DashboardView, { LatencyChart, AccuracyChart, AcuityChart } from "../components/DashboardView";
import PanelView from "../components/PanelView";
import BriefingView from "../components/BriefingView";
import { Card, Eyebrow, Badge, Counter } from "../components/ui";
import {
  API, cleanName,
  type PanelPatient, type Metrics, type RecentPatient,
} from "../lib/api";

interface ProviderInfo {
  active: string;
  providers: { id: string; label: string; model: string; configured: boolean; active: boolean }[];
}

export default function Home() {
  const [view, setView] = useState<View>("dashboard");
  const [collapsed, setCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const [patients, setPatients] = useState<PanelPatient[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [recent, setRecent] = useState<RecentPatient[]>([]);

  const [activePatient, setActivePatient] = useState<string | null>(null);
  const [briefingFocus, setBriefingFocus] = useState<"brief" | "chart" | "chat" | undefined>();
  const [providerInfo, setProviderInfo] = useState<ProviderInfo | null>(null);
  const [providerError, setProviderError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    fetch(`${API}/patients`).then(r => r.json()).then(d => setPatients(d.patients || [])).catch(() => null);
    fetch(`${API}/metrics`).then(r => r.json()).then(setMetrics).catch(() => null);
    fetch(`${API}/recent`).then(r => r.json()).then(d => setRecent(d.recent || [])).catch(() => null);
    fetch(`${API}/provider`).then(r => r.json()).then(setProviderInfo).catch(() => null);
  }, []);

  const switchProvider = useCallback(async (id: string) => {
    setProviderError(null);
    try {
      const res = await fetch(`${API}/provider`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: id }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Switch failed");
      setProviderInfo(data);
    } catch (e: unknown) {
      setProviderError(e instanceof Error ? e.message : "Switch failed");
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh, view]);

  // Ctrl/Cmd+K command palette
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(o => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const openPatient = useCallback((id: string, focus?: "brief" | "chart" | "chat") => {
    setActivePatient(id);
    setBriefingFocus(focus);
    setView("briefing");
  }, []);

  const VIEW_TITLES: Record<View, { title: string; sub: string }> = {
    dashboard: { title: "Dashboard", sub: "Your panel at a glance — acuity, throughput, and AI reliability" },
    panel: { title: "Patient Panel", sub: "Sorted by severity — safety flags surfaced before you open a chart" },
    briefing: { title: "Briefing", sub: "" },
    recent: { title: "Recent Patients", sub: "Charts you reviewed — persisted across sessions" },
    metrics: { title: "Metrics", sub: "How the AI harness is performing" },
    settings: { title: "Settings", sub: "System configuration" },
  };

  return (
    <div className="min-h-screen bg-[#FAFBFD]">
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden>
        <div className="absolute inset-0 bg-grid" />
        <div className="absolute -top-32 left-1/4 w-[480px] h-[480px] rounded-full bg-blue-100/40 blur-3xl" />
        <div className="absolute top-1/3 -right-32 w-[400px] h-[400px] rounded-full bg-cyan-100/30 blur-3xl" />
      </div>

      <div className="relative flex">
        <Sidebar
          view={view}
          onNavigate={(v) => {
            if (v === "briefing" && !activePatient) { setView("panel"); return; }
            setView(v);
          }}
          collapsed={collapsed}
          onToggle={() => setCollapsed(c => !c)}
        />

        <div className="flex-1 min-w-0 flex flex-col">
          <TopNav onOpenPalette={() => setPaletteOpen(true)} />

          <main className="flex-1 px-6 lg:px-10 py-8 max-w-[1440px] w-full mx-auto">
            {/* Page heading (not shown on briefing — it has its own bar) */}
            {view !== "briefing" && (
              <div className="mb-7">
                <h1 className="text-[28px] font-bold text-slate-900 tracking-tight">
                  {VIEW_TITLES[view].title}
                </h1>
                <p className="text-slate-500 text-[15px] mt-0.5">{VIEW_TITLES[view].sub}</p>
              </div>
            )}

            {view === "dashboard" && (
              <DashboardView patients={patients} metrics={metrics} recent={recent} onOpenPatient={openPatient} />
            )}

            {view === "panel" && (
              <PanelView patients={patients} recent={recent} onOpenPatient={openPatient} />
            )}

            {view === "briefing" && activePatient && (
              <BriefingView
                patientId={activePatient}
                focus={briefingFocus}
                onBack={() => setView("panel")}
              />
            )}

            {view === "recent" && (
              <div className="space-y-3 max-w-2xl">
                {recent.length === 0 && (
                  <Card className="py-14 text-center">
                    <Clock className="w-7 h-7 text-slate-300 mx-auto mb-3" />
                    <p className="text-slate-500 text-[15px] font-medium">No patients reviewed yet.</p>
                    <p className="text-slate-400 text-sm mt-1">Open a briefing and it will appear here — even after a restart.</p>
                  </Card>
                )}
                {recent.map((r) => (
                  <Card key={r.patient_id} lift className="cursor-pointer" onClick={() => openPatient(r.patient_id)}>
                    <div className="px-5 py-4 flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#2563EB] to-[#06B6D4] flex items-center justify-center text-white text-sm font-bold shrink-0">
                        {cleanName(r.name).charAt(0)}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-slate-900 font-bold text-[15px] truncate">{cleanName(r.name)}</p>
                        <p className="text-slate-400 text-[12px] font-mono">
                          reviewed {new Date(r.viewed_at).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
                        </p>
                      </div>
                      <FileText className="w-4 h-4 text-slate-300 shrink-0" />
                    </div>
                  </Card>
                ))}
              </div>
            )}

            {view === "metrics" && (
              <div className="space-y-5">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    { label: "Briefings generated", v: metrics?.total_requests ?? 0, suffix: "" },
                    { label: "Validation pass rate", v: metrics?.validation_pass_rate_pct ?? 0, suffix: "%" },
                    { label: "Average attempts", v: metrics?.avg_attempts ?? 0, suffix: "", decimals: 2 },
                    { label: "Chat questions", v: metrics?.chat_requests ?? 0, suffix: "" },
                  ].map((s) => (
                    <Card key={s.label} className="px-5 py-4">
                      <Counter value={s.v} suffix={s.suffix} decimals={s.decimals ?? 0} className="font-mono text-2xl font-bold text-slate-900 tabular-nums" />
                      <p className="text-slate-500 text-[13px] font-medium mt-1">{s.label}</p>
                    </Card>
                  ))}
                </div>
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
              </div>
            )}

            {view === "settings" && (
              <div className="space-y-4 max-w-2xl">
                {/* Model provider selector */}
                <Card className="overflow-hidden">
                  <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0">
                      <Cpu className="w-5 h-5 text-[#2563EB]" />
                    </div>
                    <div>
                      <p className="text-slate-900 font-bold text-[14px]">Model provider</p>
                      <p className="text-slate-500 text-[13px]">
                        Add an API key to <span className="font-mono text-[12px]">.env</span> (e.g.{" "}
                        <span className="font-mono text-[12px]">GEMINI_API_KEY=…</span>), restart the API, then switch here.
                      </p>
                    </div>
                  </div>
                  <div className="divide-y divide-slate-50">
                    {(providerInfo?.providers ?? []).map((p) => (
                      <div key={p.id} className="px-5 py-3.5 flex items-center gap-4">
                        <div className="min-w-0 flex-1">
                          <p className="text-slate-900 font-semibold text-[14px]">{p.label}</p>
                          <p className="text-slate-400 text-[12px] font-mono truncate">{p.model}</p>
                        </div>
                        {!p.configured && <Badge variant="neutral">No key</Badge>}
                        {p.configured && p.active && <Badge variant="success">Active</Badge>}
                        {p.configured && !p.active && (
                          <button
                            onClick={() => switchProvider(p.id)}
                            className="px-3.5 py-1.5 rounded-lg bg-[#2563EB] text-white text-[13px] font-semibold hover:bg-blue-700 active:scale-[0.98] transition-all shadow-sm"
                          >
                            Use
                          </button>
                        )}
                      </div>
                    ))}
                    {!providerInfo && (
                      <p className="px-5 py-4 text-slate-400 text-[13px]">Loading providers…</p>
                    )}
                  </div>
                  {providerError && (
                    <p className="px-5 py-3 bg-red-50 border-t border-red-100 text-red-700 text-[13px] font-medium">
                      {providerError}
                    </p>
                  )}
                </Card>

                {[
                  { icon: ShieldCheck, label: "Guardrails", value: "Input gate · output validation · hallucination check · chat guardrails", badge: "Active" },
                  { icon: BrainCircuit, label: "RAG knowledge base", value: "22 clinical guidelines · ChromaDB local index", badge: "Active" },
                  { icon: Database, label: "Data source", value: "Synthetic Synthea dataset · 7 clinical tables", badge: "Synthetic" },
                ].map(({ icon: Icon, label, value, badge }) => (
                  <Card key={label} className="px-5 py-4 flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
                      <Icon className="w-5 h-5 text-slate-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-slate-900 font-bold text-[14px]">{label}</p>
                      <p className="text-slate-500 text-[13px] truncate">{value}</p>
                    </div>
                    <Badge variant={badge === "Synthetic" ? "neutral" : "success"}>{badge}</Badge>
                  </Card>
                ))}
                <Card className="px-5 py-4 flex items-center gap-3 border-slate-200 bg-slate-50/60">
                  <SettingsIcon className="w-4 h-4 text-slate-400 shrink-0" />
                  <p className="text-slate-500 text-[13px]">
                    This is a harness-engineering learning project. Output is AI-generated from synthetic data and is never medical advice.
                  </p>
                </Card>
              </div>
            )}
          </main>

          <footer className="border-t border-slate-200/70 bg-white/60 px-8 py-3.5">
            <div className="max-w-[1440px] mx-auto flex items-center justify-between flex-wrap gap-2">
              <p className="text-slate-400 text-[12px] font-medium">
                <span className="font-bold text-slate-500">MedBrief AI</span> · Harness engineering project
              </p>
              <p className="text-slate-400 text-[12px] font-medium">
                Synthetic Synthea dataset · AI-generated content · Not for clinical use
              </p>
            </div>
          </footer>
        </div>
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        patients={patients}
        onSelectPatient={(id) => openPatient(id)}
      />
    </div>
  );
}
