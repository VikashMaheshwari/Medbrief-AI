import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone

LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
LOG_FILE = LOGS_DIR / "requests.jsonl"


@dataclass
class RequestLog:
    timestamp: str
    patient_id: str
    latency_ms: float
    attempts: int
    validation_passed: bool
    guardrail_input_warnings: int
    guardrail_output_errors: int
    guardrail_output_warnings: int
    eval_score: float = -1.0   # -1 means no ground truth was available
    endpoint: str = "briefing"


def log_request(log: RequestLog) -> None:
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(log)) + "\n")


def read_logs() -> list[dict]:
    if not LOG_FILE.exists():
        return []
    logs = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return logs


def compute_metrics() -> dict:
    logs = read_logs()
    # Old logs (before the endpoint field existed) are all briefing requests
    briefings = [l for l in logs if l.get("endpoint", "briefing") == "briefing"]
    chats = [l for l in logs if l.get("endpoint") == "chat"]

    if not briefings:
        return {"total_requests": 0, "chat_requests": len(chats)}

    total = len(briefings)
    avg_latency = round(sum(l["latency_ms"] for l in briefings) / total, 1)
    avg_attempts = round(sum(l["attempts"] for l in briefings) / total, 2)
    pass_rate = round(sum(1 for l in briefings if l["validation_passed"]) / total * 100, 1)

    # Only average eval scores where ground truth existed (score >= 0)
    scored = [l["eval_score"] for l in briefings if l.get("eval_score", -1) >= 0]
    avg_eval = round(sum(scored) / len(scored) * 100, 1) if scored else None

    retried = sum(1 for l in briefings if l["attempts"] > 1)
    total_warnings = sum(l["guardrail_output_warnings"] for l in briefings)
    total_errors = sum(l["guardrail_output_errors"] for l in briefings)

    return {
        "total_requests": total,
        "chat_requests": len(chats),
        "avg_latency_ms": avg_latency,
        "avg_attempts": avg_attempts,
        "validation_pass_rate_pct": pass_rate,
        "avg_eval_score_pct": avg_eval,
        "retried_requests": retried,
        "total_guardrail_warnings": total_warnings,
        "total_guardrail_errors": total_errors,
        "recent_requests": briefings[-5:],
    }


class Timer:
    # Context manager for measuring latency
    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.elapsed_ms = round((time.perf_counter() - self._start) * 1000, 1)
