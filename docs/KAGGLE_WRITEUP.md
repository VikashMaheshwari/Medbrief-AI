# MedBrief AI — Kaggle Capstone Writeup

## The problem

A primary-care doctor gets a handful of minutes to prepare for each visit,
against a chart that can span decades: dozens of encounters, active and
discontinued medications, allergies, labs, procedures. Missing one item — an
anticoagulant, a severe allergy, a critical GFR value — has real consequences.

The obvious answer, "have an LLM summarize the chart," fails in the way that
matters most: LLMs omit and invent with equal confidence. In a safety-critical
domain, the hard problem is not generation, it is **verification** — how do
you know the summary is complete and contains nothing fabricated, without a
human re-reading the whole chart to check?

## Why agents

A single prompt cannot solve this because verification requires *work the
model must not be trusted to do about itself*. Agents can:

- **ground every fact in a tool call** instead of free generation (drug
  interactions, exact age, abnormal-vital thresholds, RxNorm lookups);
- **separate roles**: the agent that writes the briefing is not the agent
  that judges it, and the judge's verdict comes from deterministic code, not
  model opinion;
- **self-correct in a bounded loop**: validation failures are fed back as
  concrete rewrite instructions, with a hard iteration cap.

This is the project's thesis: **Agent = Model + Harness**. The model supplies
intelligence; the harness — input gates, tool grounding, independent
validation, bounded loops — supplies trust.

## Architecture

**ADK multi-agent pipeline** (`adk_app/medbrief/agent.py`), built with
Google's Agent Development Kit:

1. A `before_agent_callback` **input gate** rejects any request that doesn't
   carry a valid patient UUID, and any record that fails the corrupt-data
   guardrail — before a single LLM call is made.
2. `record_analyst` (LlmAgent, Gemini 2.5 Flash) gathers the clinical facts.
   Its only data source is the project's **MCP server** (`mcp_server.py`,
   stdio transport, 5 tools) via ADK's `MCPToolset` — the same server works
   standalone with Claude Desktop.
3. `write_and_audit` (LoopAgent, max 3 iterations) runs the self-correction
   cycle: `briefing_writer` drafts; `safety_auditor` calls the deterministic
   `harness_check` tool, which re-derives the completeness checklist from the
   raw CSVs and scans for hallucinated medications. PASS exits the loop; FAIL
   returns the exact failure list for a rewrite.

The ADK layer wraps — never forks — the original harness (`src/`): the same
loader, validator, and guardrails also power a FastAPI backend with a Next.js
clinical UI, RAG over clinical guidelines (ChromaDB), ground-truth evals
(A–F grades against physician-written answer keys), and LLMOps logging.

## Course concepts demonstrated

Multi-agent system with ADK (code) · MCP server (code) · Security features
(code: input/output gates, anti-hallucination validator, non-root container,
secrets only via env/Secret Manager) · Agent skills (code:
`skills/patient-briefing/SKILL.md`) · Deployability (Dockerfile + Cloud Run,
shown in video) · Antigravity (development workflow, shown in video).

## The journey

The project began as a plain Groq tool-calling loop that produced fluent,
subtly wrong briefings. Every failure became harness, not patchwork: an
omitted cancer diagnosis became the validator's re-derived checklist; an
invented medication became the RxNorm verification tool and the hallucination
scan; a runaway tool loop became hard iteration caps. Migrating to ADK made
this philosophy structural — the writer and the auditor are now literally
different agents, and the auditor's only power is a function that runs
deterministic code. The lesson we'd offer other builders: in high-stakes
domains, spend your effort on the checks around the model, because that is
where trust actually comes from.

*All data is synthetic (Synthea). This is a learning project, not a clinical
tool, and its output is never medical advice.*
