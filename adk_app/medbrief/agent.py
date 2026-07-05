"""
MedBrief AI — ADK multi-agent pipeline (Google Agent Development Kit).

This is the ADK re-expression of the project's harness philosophy
(Agent = Model + Harness), built from three cooperating agents:

    root_agent (SequentialAgent "medbrief_pipeline")
    │
    ├── 1. record_analyst   LlmAgent — gathers the clinical facts. Its ONLY
    │                       data source is the project's own MCP server
    │                       (mcp_server.py, stdio transport), so every fact
    │                       is tool-derived, never hallucinated.
    │
    └── 2. write_and_audit  LoopAgent (max 3 iterations) — the self-correction
            │               harness, expressed as an ADK loop:
            ├── briefing_writer  LlmAgent — drafts the doctor-facing briefing
            └── safety_auditor   LlmAgent — runs the DETERMINISTIC harness
                                 check (validator + output guardrails, re-derived
                                 from raw CSVs — it never trusts the writer),
                                 then either exits the loop or sends the
                                 failures back for a rewrite.

Security features in this file:
  * before_agent_callback input gate — rejects requests that don't carry a
    well-formed patient UUID, and blocks records that fail the corrupt-data
    input guardrail, BEFORE any LLM call is made.
  * harness_check tool — independent output validation: hallucinated
    medications, omitted critical conditions, and missing sections are caught
    by code, not by model self-assessment.

Run it:
    adk web adk_app                 # browser dev UI
    adk run adk_app/medbrief        # terminal
    python adk_app/run.py <patient_id>   # programmatic

Requires GEMINI_API_KEY (or GOOGLE_API_KEY) in .env — never hardcoded here.
"""
import os
import re
import sys
from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import exit_loop
from google.adk.models.google_llm import Gemini
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.genai import types
from mcp import StdioServerParameters

# Make the existing harness importable (src/ is not a package on purpose —
# the ADK layer wraps the harness, it does not fork it).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Override with ADK_MODEL in .env (e.g. gemini-2.5-flash-lite for higher
# free-tier RPM). Key comes from GEMINI_API_KEY — never hardcoded.
MODEL_NAME = os.getenv("ADK_MODEL", "gemini-2.5-flash")


def make_model() -> Gemini:
    """Gemini model with 429-aware retries.

    The free tier allows only a few requests/minute and this pipeline makes
    ~7 LLM calls per briefing, so instead of crashing on RESOURCE_EXHAUSTED
    we back off and retry (another bounded loop — same harness philosophy).
    """
    return Gemini(
        model=MODEL_NAME,
        retry_options=types.HttpRetryOptions(
            attempts=6,
            initial_delay=15,   # seconds; free-tier window resets each minute
            max_delay=70,
            exp_base=1.6,
            http_status_codes=[429, 500, 502, 503, 504],
        ),
    )
MCP_SERVER = PROJECT_ROOT / "mcp_server.py"
PATIENT_ID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# SECURITY FEATURE 1 — input gate (before_agent_callback)
# Runs before the first model call. A malformed request (no valid patient
# UUID, e.g. free text that could carry a prompt injection) or a corrupt
# patient record never reaches the LLM.
# ---------------------------------------------------------------------------
def input_gate(callback_context: CallbackContext) -> Optional[types.Content]:
    user_text = ""
    if callback_context.user_content and callback_context.user_content.parts:
        user_text = " ".join(
            p.text or "" for p in callback_context.user_content.parts
        )

    match = PATIENT_ID_RE.search(user_text)
    if not match:
        # Returning Content short-circuits the whole pipeline — no LLM call.
        return types.Content(
            role="model",
            parts=[types.Part(text=(
                "Request blocked by input gate: no valid patient ID found. "
                "Provide a patient UUID, e.g. "
                "'Brief me on patient b084297c-c410-108c-9499-aa99d25e761c'."
            ))],
        )

    patient_id = match.group(0).lower()
    # Reuse the harness's deterministic input guardrail: corrupt or
    # incomplete records are rejected before generation, same as the API's
    # HTTP 400 gate.
    try:
        from guardrails import run_input_guardrails
        from loader import load_patient

        record = load_patient(patient_id)
        gate = run_input_guardrails(record)
        if not gate.passed:
            return types.Content(
                role="model",
                parts=[types.Part(text=(
                    "Request blocked by input gate — record failed guardrails:\n"
                    + "\n".join(f"- {e}" for e in gate.errors)
                ))],
            )
    except Exception as e:
        return types.Content(
            role="model",
            parts=[types.Part(text=f"Request blocked: could not load patient ({e}).")],
        )

    # Stash the validated ID in session state for downstream agents/tools.
    callback_context.state["patient_id"] = patient_id
    return None  # gate passed — continue normally


# ---------------------------------------------------------------------------
# SECURITY FEATURE 2 — deterministic harness check (FunctionTool)
# The auditor agent MUST call this. It re-derives the completeness checklist
# from the raw CSVs, so the pipeline never grades its own homework.
# ---------------------------------------------------------------------------
def harness_check(patient_id: str, briefing: str) -> str:
    """Validate a draft briefing against the patient's raw record.

    Checks (all deterministic, no LLM involved):
      - every active medication, allergy and condition appears in the briefing
      - required sections are present
      - no hallucinated medications (drugs mentioned but not on the record)

    Returns 'PASS' or a bullet list of failures the writer must fix.
    """
    from guardrails import run_output_guardrails
    from loader import load_patient
    from validator import validate

    try:
        record = load_patient(patient_id)
    except Exception as e:
        return f"FAIL\n- could not load record for validation: {e}"

    validation = validate(briefing, record)
    guard = run_output_guardrails(briefing, record)

    failures = (
        [f"Missing medication: {m}" for m in validation.missing_medications]
        + [f"Missing allergy: {a}" for a in validation.missing_allergies]
        + [f"Missing condition: {c}" for c in validation.missing_conditions]
        + [f"Guardrail error: {e}" for e in guard.errors]
    )
    if failures:
        return "FAIL\n" + "\n".join(f"- {f}" for f in failures)
    return "PASS"


# ---------------------------------------------------------------------------
# MCP toolset — the analyst's ONLY window into patient data.
# ADK spawns mcp_server.py as a subprocess and speaks MCP over stdio;
# the same server also works standalone with Claude Desktop or any MCP client.
# ---------------------------------------------------------------------------
medbrief_mcp = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[str(MCP_SERVER)],
        ),
        timeout=30,
    ),
)


# --- Sub-agent 1: gather facts through MCP tools only ----------------------
record_analyst = LlmAgent(
    name="record_analyst",
    model=make_model(),
    description="Gathers a patient's clinical facts exclusively via MCP tools.",
    instruction=(
        "You are a clinical data analyst. The validated patient ID is "
        "{patient_id}.\n"
        "Use your tools to gather, in order: the patient summary, exact age, "
        "drug-interaction check across all active medications, and abnormal "
        "vitals. Do NOT state any clinical fact that did not come from a tool "
        "result. Output a compact FACT SHEET with sections: DEMOGRAPHICS, "
        "ALLERGIES, ACTIVE MEDICATIONS, ACTIVE CONDITIONS, DRUG INTERACTIONS, "
        "ABNORMAL VITALS."
    ),
    tools=[medbrief_mcp],
    output_key="fact_sheet",  # → session state, read by the writer
)

# --- Sub-agent 2a: write the briefing ---------------------------------------
briefing_writer = LlmAgent(
    name="briefing_writer",
    model=make_model(),
    description="Writes the doctor-facing pre-visit briefing from the fact sheet.",
    instruction=(
        "You write pre-visit briefings for doctors. Source material:\n\n"
        "{fact_sheet}\n\n"
        "If auditor feedback exists below, this is a REWRITE — fix every "
        "listed issue:\n{audit_feedback?}\n\n"
        "Rules: 150-250 words. Sections: PATIENT, ACTIVE CONDITIONS, "
        "MEDICATIONS, ALLERGIES, FLAGS. Mention EVERY active medication, "
        "condition and allergy from the fact sheet. Never invent a medication "
        "or diagnosis that is not in the fact sheet. Flag drug interactions "
        "and abnormal vitals prominently."
    ),
    output_key="briefing",
)

# --- Sub-agent 2b: audit with the deterministic harness ---------------------
safety_auditor = LlmAgent(
    name="safety_auditor",
    model=make_model(),
    description="Audits the briefing with deterministic harness checks.",
    instruction=(
        "You are a safety auditor. The draft briefing is:\n\n{briefing}\n\n"
        "Step 1: call harness_check with patient_id='{patient_id}' and the "
        "full briefing text.\n"
        "Step 2: if it returns PASS, call exit_loop, then output the final "
        "briefing exactly as written.\n"
        "Step 3: if it returns FAIL, output the failure list verbatim as "
        "feedback for the writer. Do not rewrite the briefing yourself."
    ),
    tools=[harness_check, exit_loop],
    output_key="audit_feedback",
)

# --- Self-correction loop: write → audit → (rewrite …), max 3 attempts ------
# Mirrors generate_briefing_with_loop() in src/agent.py, expressed natively
# in ADK: the LoopAgent re-runs writer+auditor until exit_loop or the cap.
write_and_audit = LoopAgent(
    name="write_and_audit",
    max_iterations=3,
    sub_agents=[briefing_writer, safety_auditor],
)

# --- Root: the pipeline the ADK runner discovers ----------------------------
root_agent = SequentialAgent(
    name="medbrief_pipeline",
    description=(
        "Generates a validated pre-visit patient briefing: MCP fact gathering "
        "→ write → deterministic audit loop."
    ),
    sub_agents=[record_analyst, write_and_audit],
    before_agent_callback=input_gate,
)
