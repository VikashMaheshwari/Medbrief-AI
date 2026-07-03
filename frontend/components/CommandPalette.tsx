"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, User, CornerDownLeft } from "lucide-react";
import { cleanName, acuity, ACUITY_DOT, type PanelPatient } from "../lib/api";

export default function CommandPalette({
  open, onClose, patients, onSelectPatient,
}: {
  open: boolean;
  onClose: () => void;
  patients: PanelPatient[];
  onSelectPatient: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [highlighted, setHighlighted] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setHighlighted(0);
      // Focus after the enter animation starts
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    const living = patients.filter(p => !p.deceased);
    if (!q) return living.slice(0, 7);
    return living
      .filter(p => cleanName(p.name).toLowerCase().includes(q))
      .slice(0, 7);
  }, [patients, query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted(h => Math.min(h + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted(h => Math.max(h - 1, 0));
    } else if (e.key === "Enter" && results[highlighted]) {
      onSelectPatient(results[highlighted].patient_id);
      onClose();
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-[2px]"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.97, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -8 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="fixed z-50 top-[18vh] left-1/2 -translate-x-1/2 w-[92vw] max-w-xl"
          >
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl overflow-hidden">
              <div className="flex items-center gap-3 px-4 border-b border-slate-100">
                <Search className="w-4 h-4 text-slate-400 shrink-0" />
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setHighlighted(0); }}
                  onKeyDown={handleKeyDown}
                  placeholder="Search patients by name…"
                  className="flex-1 py-3.5 text-[15px] text-slate-900 placeholder-slate-400 focus:outline-none"
                />
                <kbd className="font-mono text-[11px] font-semibold text-slate-400 bg-slate-50 border border-slate-200 rounded-md px-1.5 py-0.5">esc</kbd>
              </div>

              <div className="py-2 max-h-80 overflow-y-auto">
                {results.length === 0 && (
                  <p className="px-4 py-6 text-sm text-slate-400 text-center">No patients match “{query}”.</p>
                )}
                {results.map((p, i) => (
                  <button
                    key={p.patient_id}
                    onClick={() => { onSelectPatient(p.patient_id); onClose(); }}
                    onMouseEnter={() => setHighlighted(i)}
                    className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                      i === highlighted ? "bg-blue-50" : ""
                    }`}
                  >
                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                      <User className="w-4 h-4 text-slate-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-slate-900 truncate">{cleanName(p.name)}</p>
                      <p className="text-xs text-slate-400 font-mono">
                        {p.age ?? "—"} {p.gender} · {p.active_conditions} dx · {p.active_medications} rx
                      </p>
                    </div>
                    <span className={`w-2 h-2 rounded-full shrink-0 ${ACUITY_DOT[acuity(p)]}`} />
                    {i === highlighted && <CornerDownLeft className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                  </button>
                ))}
              </div>

              <div className="px-4 py-2 border-t border-slate-100 flex items-center gap-4 text-[11px] text-slate-400">
                <span><kbd className="font-mono font-semibold">↑↓</kbd> navigate</span>
                <span><kbd className="font-mono font-semibold">↵</kbd> open briefing</span>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
