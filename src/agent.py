import json
from pathlib import Path
from loader import load_patient
from tools import TOOL_SCHEMAS, run_tool
from rag import retrieve, build_rag_query
from providers import chat_completion

MAX_TOOL_ROUNDS = 5  # hard cap so a runaway model can't spin forever

AGENTS_MD = Path(__file__).parent.parent / "AGENTS.md"


def load_rules() -> str:
    # Read AGENTS.md — this becomes the system prompt that governs the agent's behavior
    return AGENTS_MD.read_text(encoding="utf-8")


def format_patient_record(record: dict) -> str:
    # Convert the patient dictionary into a clean readable text block for the model
    info = record["patient_info"]
    first = info.get("FIRST", "Unknown")
    last = info.get("LAST", "Unknown")
    dob = info.get("BIRTHDATE", "not documented")
    gender = info.get("GENDER", "not documented")

    lines = []
    lines.append(f"PATIENT: {first} {last}")
    lines.append(f"DOB: {dob} | Gender: {gender}")

    # Allergies — safety critical, listed first
    lines.append("\nALLERGIES:")
    if record["allergies"]:
        for a in record["allergies"]:
            severity = a.get("SEVERITY1", "not documented")
            reaction = a.get("DESCRIPTION1", "")
            reaction_str = f" | Reaction: {reaction}" if reaction and str(reaction) != "nan" else ""
            lines.append(f"  - {a['DESCRIPTION']} | Severity: {severity}{reaction_str}")
    else:
        lines.append("  - None documented")

    # Active medications
    lines.append("\nACTIVE MEDICATIONS:")
    if record["active_medications"]:
        for m in record["active_medications"]:
            reason = m.get("REASONDESCRIPTION", "")
            reason_str = f" (for: {reason})" if reason and str(reason) != "nan" else ""
            lines.append(f"  - {m['DESCRIPTION']}{reason_str}")
    else:
        lines.append("  - None documented")

    # Active conditions
    lines.append("\nACTIVE CONDITIONS:")
    if record["active_conditions"]:
        for c in record["active_conditions"]:
            lines.append(f"  - {c['DESCRIPTION']}")
    else:
        lines.append("  - None documented")

    # Vitals and labs
    lines.append("\nVITALS & LABS:")
    if record["recent_vitals"]:
        for v in record["recent_vitals"]:
            lines.append(f"  - {v['DESCRIPTION']}: {v['VALUE']} {v['UNITS']}")
    else:
        lines.append("  - None documented")

    # Past procedures
    lines.append("\nPAST PROCEDURES:")
    if record["past_procedures"]:
        for p in record["past_procedures"]:
            lines.append(f"  - {p['DESCRIPTION']}")
    else:
        lines.append("  - None documented")

    # Last encounter
    lines.append("\nLAST ENCOUNTER:")
    enc = record.get("last_encounter", {})
    if enc:
        lines.append(f"  - Date: {enc.get('START')} | Type: {enc.get('ENCOUNTERCLASS')} | {enc.get('DESCRIPTION')}")
    else:
        lines.append("  - None documented")

    return "\n".join(lines)


def build_rag_context(record: dict) -> str:
    # Retrieve relevant medical facts from ChromaDB and format as context block
    query = build_rag_query(record)
    facts = retrieve(query, top_k=3)
    if not facts:
        return ""
    lines = ["RELEVANT CLINICAL GUIDELINES (use these to enrich the briefing):"]
    for i, fact in enumerate(facts, 1):
        lines.append(f"{i}. {fact}")
    return "\n".join(lines)


def _build_messages(record: dict) -> list:
    # System prompt = harness rules + RAG-retrieved clinical guidelines
    system_prompt = load_rules()
    rag_context = build_rag_context(record)
    if rag_context:
        system_prompt += "\n\n" + rag_context
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": format_patient_record(record)},
    ]


def _chat_completion(messages: list, use_tools: bool = True):
    # Provider-agnostic call — Groq/Gemini/OpenAI chosen at runtime,
    # rate-limit retries handled inside the provider layer
    return chat_completion(
        messages,
        max_tokens=1024,
        tools=TOOL_SCHEMAS if use_tools else None,
    )


def _agentic_loop(messages: list) -> str:
    # Runs tool-calling rounds until the model produces a text answer.
    # Capped at MAX_TOOL_ROUNDS; the final round disables tools so the
    # model is forced to answer instead of requesting tools forever.
    for round_num in range(MAX_TOOL_ROUNDS + 1):
        use_tools = round_num < MAX_TOOL_ROUNDS
        response = _chat_completion(messages, use_tools=use_tools)
        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                tool_result = run_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments),
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
            continue

        return choice.message.content or "Briefing could not be generated"

    return "Briefing could not be generated"


def generate_briefing(record: dict) -> str:
    return _agentic_loop(_build_messages(record))


def generate_briefing_with_loop(record: dict, max_retries: int = 3) -> dict:
    # Self-correction loop — retries if validation or guardrails fail
    # Returns the briefing plus metadata about how many attempts it took
    from validator import validate
    from guardrails import run_output_guardrails

    attempts = 0
    messages = _build_messages(record)

    while attempts < max_retries:
        attempts += 1
        briefing = _agentic_loop(messages)

        # Check quality of this attempt
        validation = validate(briefing, record)
        guard = run_output_guardrails(briefing, record)

        # Collect all failures into a single feedback message
        failures = []
        for m in validation.missing_medications:
            failures.append(f"Missing medication: {m}")
        for a in validation.missing_allergies:
            failures.append(f"Missing allergy: {a}")
        for c in validation.missing_conditions:
            failures.append(f"Missing condition: {c}")
        for e in guard.errors:
            failures.append(f"Guardrail error: {e}")

        # If no failures, return the briefing immediately
        if not failures:
            return {
                "briefing": briefing,
                "attempts": attempts,
                "passed": True,
                "validation": validation,
                "guardrails": guard,
            }

        # If we still have retries left, inject the failures as feedback
        if attempts < max_retries:
            feedback = (
                "Your briefing was incomplete. Fix these issues and rewrite the full briefing:\n"
                + "\n".join(f"- {f}" for f in failures)
            )
            messages.append({"role": "assistant", "content": briefing})
            messages.append({"role": "user", "content": feedback})

    # Max retries hit — return whatever the last attempt produced
    return {
        "briefing": briefing,
        "attempts": attempts,
        "passed": False,
        "validation": validation,
        "guardrails": guard,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from loader import load_patient

    test_id = "b084297c-c410-108c-9499-aa99d25e761c"
    record = load_patient(test_id)
    briefing = generate_briefing(record)

    print("=== GENERATED BRIEFING ===")
    print(briefing)
