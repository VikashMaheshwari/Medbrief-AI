"use client";

import {
  LayoutDashboard, Users, FileText, Clock, Activity, Settings,
  PanelLeftClose, PanelLeftOpen,
} from "lucide-react";

export type View = "dashboard" | "panel" | "briefing" | "recent" | "metrics" | "settings";

const ITEMS: { view: View; label: string; icon: React.ElementType }[] = [
  { view: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { view: "panel", label: "Patient Panel", icon: Users },
  { view: "briefing", label: "Briefings", icon: FileText },
  { view: "recent", label: "Recent Patients", icon: Clock },
  { view: "metrics", label: "Metrics", icon: Activity },
  { view: "settings", label: "Settings", icon: Settings },
];

export default function Sidebar({
  view, onNavigate, collapsed, onToggle,
}: {
  view: View;
  onNavigate: (v: View) => void;
  collapsed: boolean;
  onToggle: () => void;
}) {
  return (
    <aside
      className={`sticky top-0 h-screen shrink-0 border-r border-slate-200/70 bg-white/60 backdrop-blur-xl flex flex-col transition-all duration-200 ${
        collapsed ? "w-[68px]" : "w-56"
      }`}
    >
      <div className="h-16 shrink-0" />

      <nav className="flex-1 px-3 py-4 space-y-1">
        {ITEMS.map(({ view: v, label, icon: Icon }) => {
          const active = view === v;
          return (
            <button
              key={v}
              onClick={() => onNavigate(v)}
              title={collapsed ? label : undefined}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                active
                  ? "bg-blue-50 text-[#2563EB] font-semibold"
                  : "text-slate-500 hover:text-slate-900 hover:bg-slate-100/70"
              }`}
            >
              <Icon className={`w-[18px] h-[18px] shrink-0 ${active ? "text-[#2563EB]" : ""}`} />
              {!collapsed && <span className="truncate">{label}</span>}
              {!collapsed && active && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
              )}
            </button>
          );
        })}
      </nav>

      <div className="px-3 pb-4">
        <button
          onClick={onToggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-slate-400 hover:text-slate-700 hover:bg-slate-100/70 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          {collapsed
            ? <PanelLeftOpen className="w-[18px] h-[18px]" />
            : <><PanelLeftClose className="w-[18px] h-[18px]" /><span>Collapse</span></>}
        </button>
      </div>
    </aside>
  );
}
