# MedBrief AI — Pre-Visit Patient Briefing Agent

**Kaggle AI Agents Intensive — Capstone Submission**

Doctors get minutes to prepare for each patient. MedBrief AI is a multi-agent
system that reads a synthetic patient's full medical record and produces a
short, accurate, doctor-facing briefing — wrapped in the deterministic rules,
checks, and feedback loops (the **harness**) that make agent output trustworthy
enough for a safety-critical domain.

> **Scope note:** Synthetic Synthea patient data only. Not a real clinical
> tool, must never be used with real patient data, and its output is never
> medical advice.

---

## The problem

An LLM asked to summarize a medical record will happily omit a critical
condition or invent a medication — and sound confident doing it. In medicine,
"mostly right" is a failure mode. The interesting problem isn't generation;
it's **verification**: how do you build an agent whose output you can trust
without a human re-checking every line?

## The solution: Agent = Model + Harness

The model provides the intelligence. The harness is everything built around it
so the output can be trusted: input gates, tool-grounded facts, an independent
validator that re-derives its checklist from the raw CSVs (it never trusts the
agent's own claim of completeness), and a bounded self-correction loop.

---

## Key concepts demonstrated (course rubric)

| Key concept | Where |
|---|---|
| **Multi-agent system (ADK)** | `adk_app/medbrief/agent.py` — SequentialAgent → (record_analyst, LoopAgent(briefing_writer, safety_auditor)) |
| **MCP server** | `mcp_server.py` — FastMCP stdio server, 5 patient tools; consumed by the ADK analyst via `MCPToolset` *and* usable from Claude Desktop |
| **Security features** | `src/guardrails.py` (input/output/chat gates), `src/validator.py` (anti-hallucination completeness check), `input_gate` callback in the ADK pipeline, non-root Docker user, keys only via `.env`/Secret Manager |
| **Agent skills** | `skills/patient-briefing/SKILL.md` — reusable skill with trigger conditions and hard safety rules |
| **Deployability** | `Dockerfile` + `.dockerignore` + Cloud Run command (shown in video) |
| **Antigravity** | Development workflow (shown in video) |

---

## Architecture

### ADK multi-agent pipeline (`adk_app/`)

```
user: "Brief me on patient <uuid>"
   │
   ▼
input_gate (before_agent_callback)          ── SECURITY
   rejects requests without a valid patient UUID and
   records that fail the corrupt-data guardrail — before any LLM call
   │
   ▼
root_agent: SequentialAgent "medbrief_pipeline"
   │
   ├── 1. record_analyst (LlmAgent, gemini-2.5-flash)
   │       tools = MCPToolset ──stdio──► mcp_server.py   ── MCP
   │       every clinical fact is tool-derived, never free-generated
   │       output → state["fact_sheet"]
   │
   └── 2. write_and_audit (LoopAgent, max 3 iterations)  ── SELF-CORRECTION
           ├── briefing_writer (LlmAgent) → state["briefing"]
           └── safety_auditor (LlmAgent)
                   tool: harness_check ── deterministic re-validation
                         against raw CSVs (validator + output guardrails)
                   PASS → exit_loop → final briefing
                   FAIL → failures fed back → writer rewrites
```

### Original harness pipeline (FastAPI, `src/` + `api/`)

```
patient_id
   ▼
loader.py      cached CSVs → one clean patient record
   ▼
guardrails.py  INPUT GATE — corrupt/incomplete records blocked (HTTP 400)
   ▼
agent.py       RAG context + AGENTS.md rules + tool-calling loop (capped)
   │              ├── tools.py: age calc, drug interactions, abnormal vitals, RxNorm
   │              └── rag.py:   ChromaDB retrieves relevant clinical guidelines
   ▼
validator.py   every active med / allergy / condition must appear in the briefing
guardrails.py  OUTPUT GATE — missing sections, omitted critical conditions,
   │           hallucinated medications
   ├── any failure? → feedback injected, agent rewrites (max 3 attempts)
   ▼
evals.py       scored against hand-written ground truth (grade A–F)
llmops.py      latency, attempts, pass rate → logs/requests.jsonl
memory.py      persistent "recently reviewed" list
   ▼
API response → Next.js frontend
```

Both pipelines share one source of truth: the same loader, validator,
guardrails, and MCP tools. The ADK layer *wraps* the harness; it doesn't fork it.

---

## Project structure

```
harnessproject/
├── AGENTS.md               ← the harness rulebook (system prompt)
├── mcp_server.py           ← MCP server (stdio) — 5 patient tools
├── adk_app/                ← ADK multi-agent pipeline
│   ├── medbrief/agent.py   ←   root_agent + 3 sub-agents + security callbacks
│   └── run.py              ←   programmatic runner (streams agent handoffs)
├── skills/
│   └── patient-briefing/SKILL.md   ← agent skill definition
├── src/                    ← the harness
│   ├── loader.py  filters.py  agent.py  tools.py
│   ├── validator.py  guardrails.py  rag.py
│   └── evals.py  llmops.py  memory.py  providers.py
├── api/main.py             ← FastAPI app
├── frontend/               ← Next.js clinical UI
├── tests/                  ← ground truth + batch eval runner
├── sample_data/            ← Synthea CSVs (synthetic patients)
├── Dockerfile  .dockerignore
└── requirements.txt
```

---

## Setup & run

**Prerequisites:** Python 3.10+, Node.js, and an API key
([Gemini](https://aistudio.google.com/apikey) for the ADK pipeline;
Groq/OpenAI also work for the FastAPI harness).

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Create .env in the project root (NEVER commit it — .gitignore covers it)
#    GEMINI_API_KEY=...          (ADK pipeline + Gemini provider)
#    GROQ_API_KEY=...            (optional — Groq provider)
#    MODEL_PROVIDER=gemini       (optional default)

# 3. Build the RAG knowledge base (one time)
python src/rag.py
```

**Run the ADK multi-agent pipeline:**

```bash
python adk_app/run.py                        # demo patient, streams handoffs
python adk_app/run.py <patient_id>
adk web adk_app                              # ADK dev UI in the browser
```

**Run the full app (API + frontend):**

```bash
python -m uvicorn api.main:app --reload --port 8000   # terminal 1
cd frontend && npm install && npm run dev              # terminal 2 → :3000
```

**Other entry points:**

```bash
python brief.py <patient_id>     # CLI briefing + validation
python tests/run_evals.py        # score all 5 ground-truth patients
python mcp_server.py             # standalone MCP server (Claude Desktop etc.)
```

**Deploy (Docker / Cloud Run):**

```bash
docker build -t medbrief-api .
docker run -p 8000:8000 --env-file .env medbrief-api

# Cloud Run — key comes from Secret Manager, never the image:
gcloud run deploy medbrief-api --source . --region us-central1 \
  --set-secrets GEMINI_API_KEY=medbrief-gemini-key:latest
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

Error contract: unknown patient → `404` · input-guardrail block → `400` ·
rate-limit exhaustion → `503`.

---

## Key harness decisions (what this project argues)

- **The validator never trusts the agent.** It rebuilds the must-include list
  from the raw CSVs and matches on *distinctive* keywords ("myocardial", never
  "history"), so a passing grade means something. In the ADK pipeline this is
  the `harness_check` tool — the auditor agent can't skip it.
- **Failures fix the harness, not the output.** Every agent mistake became a
  rule in `AGENTS.md`, a validator check, or a guardrail — never a one-off patch.
- **Loops must be bounded.** Tool loop capped, retry loop capped at 3
  (LoopAgent `max_iterations=3` in ADK), chat history trimmed. Nothing spins forever.
- **Guard every door.** Briefings, chat answers, and the ADK entry point all
  pass gates — a harness with an unguarded side entrance isn't a harness.
- **Score only what you can score.** Patients without ground truth return
  `eval: null` instead of polluting metrics with fake zeros.

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

*Synthetic Synthea dataset · AI-generated content · Not for clinical use ·
No API keys or secrets in this repository.*
