"use client";

import { Search, ShieldCheck, Sparkles } from "lucide-react";

export default function TopNav({ onOpenPalette }: { onOpenPalette: () => void }) {
  return (
    <header className="sticky top-0 z-30 h-16 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl">
      <div className="h-full px-6 flex items-center gap-4">
        {/* Brand */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#2563EB] to-[#06B6D4] flex items-center justify-center shadow-sm">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-slate-900 font-bold text-[17px] tracking-tight">MedBrief AI</span>
        </div>

        {/* Command palette trigger */}
        <button
          onClick={onOpenPalette}
          className="ml-6 hidden md:flex items-center gap-2.5 w-72 px-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50/80 text-slate-400 text-sm hover:border-slate-300 hover:bg-white transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Search className="w-4 h-4" />
          <span>Find a patient…</span>
          <kbd className="ml-auto font-mono text-[11px] font-semibold text-slate-400 bg-white border border-slate-200 rounded-md px-1.5 py-0.5">
            Ctrl K
          </kbd>
        </button>

        <div className="ml-auto flex items-center gap-3">
          {/* Live AI status */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border border-green-200 bg-green-50">
            <span className="w-2 h-2 rounded-full bg-[#16A34A] live-dot" />
            <span className="text-green-700 text-xs font-semibold">AI online</span>
          </div>

          {/* Guardrails */}
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-blue-200 bg-blue-50">
            <ShieldCheck className="w-3.5 h-3.5 text-[#2563EB]" />
            <span className="text-blue-700 text-xs font-semibold">Guardrails active</span>
          </div>

          {/* Profile */}
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center text-white text-xs font-bold shadow-sm">
            Dr
          </div>
        </div>
      </div>
    </header>
  );
}
