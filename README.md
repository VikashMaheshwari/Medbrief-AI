# MedBrief AI — Pre-Visit Patient Briefing Agent

An AI agent reads a synthetic patient's full medical
record and produces a short, accurate, doctor-facing briefing — wrapped in the rules, checks,
and feedback loops that make its output trustworthy.

> **Scope note:** This project uses synthetic Synthea patient data only. It is not a real
> clinical tool, must never be used with real patient data, and its output is never medical
> advice.

---

## Core concept: Agent = Model + Harness

The model (Groq `llama-3.3-70b-versatile`) provides the intelligence. The **harness** is
everything built around it so the output can be trusted:

```
patient_id
   │
   ▼
loader.py      cached CSVs → one clean patient record
   │
   ▼
guardrails.py  INPUT GATE — corrupt/incomplete records are blocked (HTTP 400)
   │
   ▼
agent.py       RAG context + AGENTS.md rules + tool-calling loop (capped rounds)
   │              ├── tools.py: age calc, drug interactions, abnormal vitals, RxNorm lookup
   │              └── rag.py:   ChromaDB retrieves relevant clinical guidelines
   │
   ▼
validator.py   every active med / allergy / condition must appear in the briefing
guardrails.py  OUTPUT GATE — missing sections, omitted critical conditions,
   │           hallucinated medications
   │
   ├── any failure? → feedback injected, agent rewrites (max 3 attempts)
   ▼
evals.py       scored against hand-written ground truth (grade A–F)
llmops.py      latency, attempts, pass rate logged to logs/requests.jsonl
memory.py      patient added to persistent "recently reviewed" list
   │
   ▼
API response → frontend
```

The validator re-derives its checklist from the raw CSVs independently — it never trusts
the agent's own claim of completeness. That is the harness doing the safety work.

---

## Features by phase

| Phase | What it adds | Where |
|-------|-------------|-------|
| 1. Context | FastAPI backend, per-patient chat sessions with memory | `api/main.py` |
| 2. Tools | Agentic tool-calling: age, drug interactions, abnormal vitals, RxNorm verification | `src/tools.py` |
| 3. Guardrails | Input gate before generation, output gate after (critical omissions, hallucinated meds), chat guardrails | `src/guardrails.py` |
| 4. Loop engineering | Self-correction: validation/guardrail failures are fed back and the agent retries (max 3) | `src/agent.py` |
| 5. RAG | ChromaDB knowledge base of clinical guidelines injected into the system prompt | `src/rag.py` |
| 6. Evals | Briefings scored against physician-written answer keys: sections, med/condition/flag coverage | `src/evals.py`, `tests/` |
| 7. LLMOps | Every request logged (latency, attempts, scores); `/metrics` aggregates | `src/llmops.py` |
| 8. MCP | Model Context Protocol server exposing 5 patient tools to any MCP client | `mcp_server.py` |
| 9. Memory | Persistent recently-viewed patients list, survives restarts | `src/memory.py` |

**Frontend** (Next.js 16 + Tailwind, light clinical theme): triage-style patient panel with
acuity color tabs, panel summary stats, name search, AI briefing with eval score bars and
guardrail warnings, clinical Q&A chat, raw patient record ("source data log") for
verification, recently-reviewed chips, live metrics in the nav.

---

## Project structure

```
harnessproject/
├── AGENTS.md              ← the harness rulebook (system prompt)
├── README.md
├── brief.py               ← CLI: python brief.py <patient_id>
├── mcp_server.py          ← MCP server (stdio transport)
├── requirements.txt
├── sample_data/           ← Synthea CSVs (patients, medications, allergies,
│                             conditions, encounters, observations, procedures)
├── src/
│   ├── loader.py          ← cached CSV loading, patient record, panel roster
│   ├── filters.py         ← removes non-clinical Synthea noise
│   ├── agent.py           ← Groq caller, RAG context, tool loop, retry loop
│   ├── tools.py           ← 4 tools + JSON schemas + dispatcher
│   ├── validator.py       ← completeness checker (distinctive-keyword matching)
│   ├── guardrails.py      ← input / output / chat guardrails
│   ├── rag.py             ← ChromaDB knowledge base + retriever
│   ├── evals.py           ← ground-truth scoring
│   ├── llmops.py          ← request logging + metrics
│   └── memory.py          ← persistent recent-patients list
├── api/
│   └── main.py            ← FastAPI app
├── frontend/              ← Next.js app (app/page.tsx + components/)
├── tests/
│   ├── ground_truth/      ← 5 hand-written answer keys
│   └── run_evals.py       ← batch eval runner
├── chroma_db/             ← persisted vector index
└── logs/
    ├── requests.jsonl     ← LLMOps log
    └── recent_patients.json
```

---

## Setup & run

**Prerequisites:** Python 3.10+, Node.js, a free [Groq API key](https://console.groq.com).

```bash
# 1. Install backend deps
pip install -r requirements.txt

# 2. Put at least one model API key in .env (project root)
#    GROQ_API_KEY=gsk_...        (Groq — llama-3.3-70b-versatile)
#    GEMINI_API_KEY=...          (Google Gemini — gemini-2.5-flash)
#    OPENAI_API_KEY=...          (OpenAI — gpt-4o-mini)
#    MODEL_PROVIDER=groq         (optional default; also switchable in Settings)

# 3. Build the RAG knowledge base (one time)
python src/rag.py

# 4. Start the API (terminal 1)
python -m uvicorn api.main:app --reload --port 8000

# 5. Start the frontend (terminal 2)
cd frontend && npm install && npm run dev
# open http://localhost:3000
```

**Other entry points:**

```bash
python brief.py <patient_id>     # CLI briefing + validation
python tests/run_evals.py        # score all 5 ground-truth patients
python mcp_server.py             # MCP server for Claude Desktop etc.
```

---

## API reference

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/` | health check |
| GET | `/patients?q=` | triage roster, sorted sickest-first |
| GET | `/patient/{id}` | raw patient record (source data) |
| GET | `/patient/{id}/briefing` | full pipeline: guardrails → generate → validate → eval → log |
| POST | `/patient/{id}/chat` | follow-up Q&A with session memory + chat guardrails |
| DELETE | `/patient/{id}/session` | clear a chat session |
| GET | `/recent` | persistent recently-viewed patients |
| GET | `/metrics` | LLMOps aggregates (latency, pass rate, eval average) |

Error contract: unknown patient → `404` · input-guardrail block → `400` with
`{errors, warnings}` · rate-limit exhaustion → `503`.

---

## Key harness decisions (what this project teaches)

- **The validator never trusts the agent.** It rebuilds the must-include list from the raw
  CSVs and matches on *distinctive* keywords ("myocardial", never "history") so a passing
  grade means something.
- **Failures fix the harness, not the output.** Every agent mistake became a rule in
  `AGENTS.md`, a validator check, or a guardrail — never a one-off patch.
- **Loops must be bounded.** The tool-calling loop is capped (final round forces a text
  answer); the retry loop is capped at 3; chat history is trimmed; the session store is
  capped. Nothing can spin or grow forever.
- **Score only what you can score.** Patients without a ground-truth file return
  `eval: null` instead of polluting the metrics average with fake zeros.
- **Guard every door.** Briefings and chat answers both pass guardrails — a harness with
  an unguarded side entrance isn't a harness.

## Test patients (ground truth available)

| Patient | Why it's useful |
|---------|-----------------|
| Dorsey40 Macejkovic424 | diabetic retinopathy + cardiac, duplicate-medication flag |
| Cheree978 Windler79 | eye case, hypotension flag |
| Dallas143 Romaguera67 | renal transplant, lung cancer, deceased |
| Norbert530 Muller251 | sepsis + septic shock, colon cancer, GFR 6.7 (critical) |
| Haley279 Nikolaus26 | allergy-heavy, epinephrine |

Full IDs are in `tests/run_evals.py`, or search by name in the app.

---

*Synthetic Synthea dataset · AI-generated content · Not for clinical use.*
