"""
Persistent memory — remembers which patients the doctor has recently viewed.
Stored as a JSON file so it survives server restarts.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

RECENT_FILE = Path(__file__).parent.parent / "logs" / "recent_patients.json"
MAX_RECENT = 8


def get_recent() -> list:
    if not RECENT_FILE.exists():
        return []
    try:
        return json.loads(RECENT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def add_recent(patient_id: str, name: str) -> None:
    recents = get_recent()
    # If already in the list, remove the old entry so it moves to the top
    recents = [r for r in recents if r.get("patient_id") != patient_id]
    recents.insert(0, {
        "patient_id": patient_id,
        "name": name,
        "viewed_at": datetime.now(timezone.utc).isoformat(),
    })
    RECENT_FILE.parent.mkdir(exist_ok=True)
    RECENT_FILE.write_text(
        json.dumps(recents[:MAX_RECENT], indent=2),
        encoding="utf-8",
    )
