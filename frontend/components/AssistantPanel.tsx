"use client";

import { useState, useRef, useEffect } from "react";
import { Sparkles, SendHorizonal, TriangleAlert } from "lucide-react";
import { API, cleanName } from "../lib/api";

interface Message {
  role: "doctor" | "agent";
  content: string;
  warnings?: string[];
}

const SUGGESTED = [
  "Summarize today's priorities",
  "Any medication interactions?",
  "Explain the abnormal labs",
  "Show the latest encounters",
  "What information is missing?",
  "Key risk factors for this visit",
];

// Progressive word reveal — reads like streaming without a streaming API
function useReveal(text: string, active: boolean): string {
  const [shown, setShown] = useState(active ? "" : text);
  useEffect(() => {
    if (!active) { setShown(text); return; }
    const words = text.split(" ");
    let i = 0;
    const id = setInterval(() => {
      i += 3;
      setShown(words.slice(0, i).join(" "));
      if (i >= words.length) clearInterval(id);
    }, 40);
    return () => clearInterval(id);
  }, [text, active]);
  return shown;
}

function AgentMessage({ content, isLatest }: { content: string; isLatest: boolean }) {
  const shown = useReveal(content, isLatest);
  return <p className="whitespace-pre-wrap">{shown}</p>;
}

export default function AssistantPanel({
  patientId, patientName, autoFocus = false,
}: {
  patientId: string;
  patientName: string;
  autoFocus?: boolean;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async (text?: string) => {
    const question = (text || input).trim();
    if (!question || loading) return;

    setInput("");
    setMessages(prev => [...prev, { role: "doctor", content: question }]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/patient/${patientId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: "agent",
        content: data.answer ?? "The assistant could not answer — please try again.",
        warnings: data.warnings,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "agent", content: "Cannot reach the AI service. Check that the API is running, then try again." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 shadow-[0_1px_3px_rgba(15,23,42,0.05)] flex flex-col h-[calc(100vh-11rem)] sticky top-24">
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-slate-100 flex items-center gap-2.5 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#06B6D4] to-[#2563EB] flex items-center justify-center shrink-0">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div className="min-w-0">
          <h3 className="text-slate-900 font-bold text-[14px] leading-tight">Clinical AI assistant</h3>
          <p className="text-slate-400 text-[12px] truncate">Context: {cleanName(patientName)}</p>
        </div>
        <span className="ml-auto w-2 h-2 rounded-full bg-[#16A34A] live-dot shrink-0" />
      </div>

      {/* Conversation */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
        {messages.length === 0 && (
          <div className="space-y-1.5">
            <p className="text-[12px] font-bold text-slate-400 uppercase tracking-wider mb-2">Suggested</p>
            {SUGGESTED.map((s, i) => (
              <button
                key={i}
                onClick={() => sendMessage(s)}
                disabled={loading}
                className="w-full text-left px-3 py-2 rounded-lg border border-slate-100 bg-slate-50/60 text-slate-600 text-[13px] font-medium hover:border-cyan-200 hover:bg-cyan-50/50 hover:text-slate-900 transition-all"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={msg.role === "doctor" ? "flex justify-end" : "flex justify-start"}>
            <div className="max-w-[88%] space-y-1.5">
              <div className={`px-3.5 py-2.5 rounded-2xl text-[13px] leading-relaxed ${
                msg.role === "doctor"
                  ? "bg-[#2563EB] text-white rounded-br-md"
                  : "bg-slate-50 border border-slate-100 text-slate-800 rounded-bl-md"
              }`}>
                {msg.role === "agent"
                  ? <AgentMessage content={msg.content} isLatest={i === messages.length - 1} />
                  : <p className="whitespace-pre-wrap">{msg.content}</p>}
              </div>
              {msg.warnings && msg.warnings.length > 0 && (
                <div className="px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 space-y-0.5">
                  {msg.warnings.map((w, wi) => (
                    <p key={wi} className="text-amber-800 text-[12px] font-medium flex items-start gap-1">
                      <TriangleAlert className="w-3 h-3 mt-0.5 shrink-0" />{w}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-50 border border-slate-100 px-4 py-3 rounded-2xl rounded-bl-md flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#06B6D4] dot-1" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#06B6D4] dot-2" />
              <span className="w-1.5 h-1.5 rounded-full bg-[#06B6D4] dot-3" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input — fixed to bottom of the panel */}
      <div className="px-3 py-3 border-t border-slate-100 shrink-0">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="Ask about this patient…"
            disabled={loading}
            className="flex-1 px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-[13px] text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#06B6D4] focus:bg-white focus:ring-2 focus:ring-cyan-100 transition-all disabled:opacity-50"
          />
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            aria-label="Send"
            className="px-3.5 rounded-xl bg-[#2563EB] text-white hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-400 active:scale-[0.97] transition-all shadow-sm"
          >
            <SendHorizonal className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
