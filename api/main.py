import sys
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loader import load_patient, list_patients
from agent import generate_briefing_with_loop, load_rules, format_patient_record
from guardrails import run_input_guardrails, run_chat_guardrails
from evals import evaluate
from llmops import log_request, compute_metrics, RequestLog, Timer
from memory import add_recent, get_recent
from providers import chat_completion, status as provider_status, set_active as set_provider

app = FastAPI(
    title="MedBrief AI",
    description="Enterprise clinical patient briefing system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store, capped so it can't grow without bound
sessions: dict[str, list] = {}
MAX_SESSIONS = 50
MAX_CHAT_MESSAGES = 30  # chat messages kept beyond the base context


def _trim_history(history: list) -> list:
    # Keep system prompt + patient record + first briefing, then only the
    # most recent chat turns — otherwise the history eventually exceeds
    # the model's context window and every request starts failing
    base, rest = history[:3], history[3:]
    if len(rest) > MAX_CHAT_MESSAGES:
        rest = rest[-MAX_CHAT_MESSAGES:]
    return base + rest


class ChatMessage(BaseModel):
    message: str


class ProviderChoice(BaseModel):
    provider: str


@app.get("/provider")
def get_provider():
    # Which model providers are configured (key present in .env) and active
    return provider_status()


@app.post("/provider")
def switch_provider(body: ProviderChoice):
    try:
        set_provider(body.provider.lower())
        return provider_status()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/")
def root():
    return {"status": "MedBrief AI is running"}


@app.get("/metrics")
def get_metrics():
    return compute_metrics()


@app.get("/recent")
def recent_patients():
    # Persistent memory — patients the doctor has recently viewed
    return {"recent": get_recent()}


@app.get("/patients")
def patient_panel(q: str = ""):
    # Doctor's patient panel — triage roster sorted sickest-first
    try:
        roster = list_patients(query=q)
        return {"patients": roster, "total": len(roster)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patient/{patient_id}")
def get_patient(patient_id: str):
    try:
        record = load_patient(patient_id)
        info = record["patient_info"]
        return {
            "patient_id": patient_id,
            "name": f"{info.get('FIRST')} {info.get('LAST')}",
            "dob": info.get("BIRTHDATE"),
            "gender": info.get("GENDER"),
            "active_medications": record["active_medications"],
            "allergies": record["allergies"],
            "active_conditions": record["active_conditions"],
            "recent_vitals": record["recent_vitals"],
            "past_procedures": record["past_procedures"],
            "last_encounter": str(record["last_encounter"]),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patient/{patient_id}/briefing")
def get_briefing(patient_id: str):
    try:
        record = load_patient(patient_id)
        info = record["patient_info"]

        input_guard = run_input_guardrails(record)
        if input_guard.blocked:
            raise HTTPException(status_code=400, detail={
                "errors": input_guard.errors,
                "warnings": input_guard.warnings
            })

        with Timer() as t:
            loop_result = generate_briefing_with_loop(record, max_retries=3)

        briefing = loop_result["briefing"]
        result = loop_result["validation"]
        output_guard = loop_result["guardrails"]
        attempts = loop_result["attempts"]

        # Evals only run when a ground truth file exists for this patient
        eval_result = evaluate(patient_id, briefing)
        eval_payload = None
        eval_score_for_log = -1.0
        if eval_result is not None:
            eval_score_for_log = eval_result.overall_score
            eval_payload = {
                "overall_score": eval_result.overall_score,
                "section_score": eval_result.section_score,
                "med_coverage": eval_result.med_coverage,
                "condition_coverage": eval_result.condition_coverage,
                "flag_coverage": eval_result.flag_coverage,
            }

        log_request(RequestLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            patient_id=patient_id,
            latency_ms=t.elapsed_ms,
            attempts=attempts,
            validation_passed=result.passed,
            guardrail_input_warnings=len(input_guard.warnings),
            guardrail_output_errors=len(output_guard.errors),
            guardrail_output_warnings=len(output_guard.warnings),
            eval_score=eval_score_for_log,
        ))

        patient_name = f"{info.get('FIRST')} {info.get('LAST')}"

        # Persistent memory — remember this patient in the recent list
        add_recent(patient_id, patient_name)

        # Evict the oldest session if the store is full
        if patient_id not in sessions and len(sessions) >= MAX_SESSIONS:
            sessions.pop(next(iter(sessions)))

        sessions[patient_id] = [
            {"role": "system", "content": load_rules()},
            {"role": "user", "content": format_patient_record(record)},
            {"role": "assistant", "content": briefing},
        ]

        return {
            "patient_id": patient_id,
            "patient_name": patient_name,
            "briefing": briefing,
            "attempts": attempts,
            "latency_ms": t.elapsed_ms,
            "blocked": output_guard.blocked,
            "guardrails": {
                "input_warnings": input_guard.warnings,
                "output_errors": output_guard.errors,
                "output_warnings": output_guard.warnings,
            },
            "validation": {
                "passed": result.passed,
                "missing_medications": result.missing_medications,
                "missing_allergies": result.missing_allergies,
                "missing_conditions": result.missing_conditions,
            },
            "eval": eval_payload,
        }
    except HTTPException:
        # Guardrail blocks raise a 400 inside the try block — re-raise it
        # as-is instead of letting the generic handler turn it into a 500
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # Rate limit exhaustion from the agent surfaces as a clean 503
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/patient/{patient_id}/chat")
def chat(patient_id: str, body: ChatMessage):
    if patient_id not in sessions:
        raise HTTPException(
            status_code=400,
            detail="No active session for this patient. Call /briefing first."
        )

    sessions[patient_id].append({"role": "user", "content": body.message})
    sessions[patient_id] = _trim_history(sessions[patient_id])

    try:
        with Timer() as t:
            response = chat_completion(sessions[patient_id], max_tokens=500)
    except Exception:
        # Roll back the unanswered question so a retry doesn't duplicate it
        sessions[patient_id].pop()
        raise HTTPException(
            status_code=503,
            detail="AI service is unavailable right now — please try again."
        )

    reply = response.choices[0].message.content or ""
    sessions[patient_id].append({"role": "assistant", "content": reply})

    # Chat answers get guardrails too — briefings aren't the only door
    warnings = []
    try:
        record = load_patient(patient_id)
        warnings = run_chat_guardrails(reply, record).warnings
    except Exception:
        pass

    log_request(RequestLog(
        timestamp=datetime.now(timezone.utc).isoformat(),
        patient_id=patient_id,
        latency_ms=t.elapsed_ms,
        attempts=1,
        validation_passed=True,
        guardrail_input_warnings=0,
        guardrail_output_errors=0,
        guardrail_output_warnings=len(warnings),
        endpoint="chat",
    ))

    return {
        "patient_id": patient_id,
        "question": body.message,
        "answer": reply,
        "warnings": warnings,
        "turns": len([m for m in sessions[patient_id] if m["role"] == "user"]) - 1
    }


@app.delete("/patient/{patient_id}/session")
def clear_session(patient_id: str):
    if patient_id in sessions:
        del sessions[patient_id]
        return {"status": "Session cleared", "patient_id": patient_id}
    return {"status": "No session found", "patient_id": patient_id}
