"use client";

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";

/* ------------------------------------------------------------------ */
/* Card — white, soft shadow, optional hover lift                      */
/* ------------------------------------------------------------------ */
export function Card({
  children, className = "", lift = false, onClick,
}: {
  children: React.ReactNode; className?: string; lift?: boolean; onClick?: () => void;
}) {
  return (
    <motion.div
      onClick={onClick}
      whileHover={lift ? { y: -2, boxShadow: "0 8px 24px -8px rgba(15,23,42,0.12)" } : undefined}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className={`bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_3px_rgba(15,23,42,0.05)] ${className}`}
    >
      {children}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/* Badge                                                               */
/* ------------------------------------------------------------------ */
const BADGE_VARIANTS: Record<string, string> = {
  success: "bg-green-50 text-green-700 border-green-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  critical: "bg-red-50 text-red-700 border-red-200",
  info: "bg-blue-50 text-blue-700 border-blue-200",
  neutral: "bg-slate-50 text-slate-600 border-slate-200",
  accent: "bg-cyan-50 text-cyan-700 border-cyan-200",
};

export function Badge({
  children, variant = "neutral", className = "",
}: {
  children: React.ReactNode; variant?: keyof typeof BADGE_VARIANTS; className?: string;
}) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-xs font-semibold ${BADGE_VARIANTS[variant]} ${className}`}>
      {children}
    </span>
  );
}

export function VerifiedBadge({ label = "Verified" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md border border-green-200 bg-green-50 text-green-700 text-xs font-semibold">
      <CheckCircle2 className="w-3 h-3" />
      {label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Section eyebrow label                                               */
/* ------------------------------------------------------------------ */
export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.12em]">{children}</p>
  );
}

/* ------------------------------------------------------------------ */
/* Animated counter                                                    */
/* ------------------------------------------------------------------ */
export function useCountUp(target: number, duration = 900): number {
  const [val, setVal] = useState(0);
  const prev = useRef(0);

  useEffect(() => {
    const from = prev.current;
    prev.current = target;
    let raf: number;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(from + (target - from) * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return val;
}

export function Counter({
  value, decimals = 0, suffix = "", className = "",
}: {
  value: number; decimals?: number; suffix?: string; className?: string;
}) {
  const v = useCountUp(value);
  return <span className={className}>{v.toFixed(decimals)}{suffix}</span>;
}

/* ------------------------------------------------------------------ */
/* Skeleton                                                            */
/* ------------------------------------------------------------------ */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`shimmer rounded-lg ${className}`} />;
}

/* ------------------------------------------------------------------ */
/* Score bar                                                           */
/* ------------------------------------------------------------------ */
export function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 85 ? "#16A34A" : pct >= 65 ? "#2563EB" : pct >= 45 ? "#F59E0B" : "#DC2626";
  return (
    <div className="flex items-center gap-3 min-w-0">
      <span className="text-slate-500 text-xs font-medium w-24 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
        />
      </div>
      <span className="font-mono text-xs font-bold w-9 text-right" style={{ color }}>{pct}%</span>
    </div>
  );
}
