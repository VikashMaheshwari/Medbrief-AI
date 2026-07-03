import re
from dataclasses import dataclass, field


@dataclass
class GuardrailResult:
    passed: bool
    blocked: bool = False
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)


# Required sections every briefing must contain
REQUIRED_SECTIONS = [
    "demographics",
    "allergies",
    "active medications",
    "active conditions",
    "vitals",
    "past procedures",
    "last visit",
    "flags",
]

# Critical conditions that must always appear in the briefing if present in record
CRITICAL_CONDITIONS = [
    "sepsis",
    "septic shock",
    "myocardial infarction",
    "anaphylaxis",
    "stroke",
    "pulmonary embolism",
    "respiratory failure",
]


# ---------------------------------------------------------------------------
# Input Guardrails — run BEFORE generating the briefing
# ---------------------------------------------------------------------------

def run_input_guardrails(record: dict) -> GuardrailResult:
    errors = []
    warnings = []

    # Check patient info exists
    info = record.get("patient_info", {})
    if not info:
        errors.append("Patient record is empty or corrupt")
        return GuardrailResult(passed=False, blocked=True, errors=errors)

    # Check patient has a name
    if not info.get("FIRST") or not info.get("LAST"):
        warnings.append("Patient name is missing or incomplete")

    # Check patient has a DOB
    if not info.get("BIRTHDATE"):
        warnings.append("Patient date of birth is not documented")

    # Warn if allergies exist but no antihistamine or epinephrine is prescribed
    if record.get("allergies"):
        meds_lower = " ".join(
            m.get("DESCRIPTION", "").lower()
            for m in record.get("active_medications", [])
        )
        has_emergency_med = any(
            keyword in meds_lower
            for keyword in ["epinephrine", "fexofenadine", "cetirizine", "loratadine", "diphenhydramine", "benadryl"]
        )
        if not has_emergency_med:
            warnings.append(
                "ALLERGY WARNING: Patient has documented allergies but no antihistamine or epinephrine found in active medications"
            )

    # Warn if no active medications at all
    if not record.get("active_medications"):
        warnings.append("No active medications on record — verify this is correct")

    # Warn if no active conditions at all
    if not record.get("active_conditions"):
        warnings.append("No active conditions on record — verify this is correct")

    passed = len(errors) == 0
    blocked = any(e for e in errors)

    return GuardrailResult(passed=passed, blocked=blocked, warnings=warnings, errors=errors)


def _medication_warnings(text: str, record: dict) -> list:
    # Flags med-looking lines in the text that don't trace back to any drug
    # in the patient's actual medication list (hallucination heuristic)
    source_keywords = set()
    for med in record.get("active_medications", []):
        for word in med.get("DESCRIPTION", "").lower().split():
            cleaned = word.strip("()[].,/")
            if len(cleaned) > 4 and not cleaned.isdigit():
                source_keywords.add(cleaned)

    warnings = []
    for line in text.split("\n"):
        line_lower = line.lower()
        # Skip vitals lines — they have a "label: value units" pattern
        if re.search(r":\s*\d+\.?\d*\s*(mg|mm|%|/min|g/dl|ng|mmol)", line_lower):
            continue
        # Only check lines that look like medication bullet points
        if ("tablet" in line_lower or "capsule" in line_lower or "oral" in line_lower) and \
           ("*" in line or "-" in line):
            if not any(kw in line_lower for kw in source_keywords):
                warnings.append(f"Possible hallucinated medication: '{line.strip()}'")
    return warnings


def run_chat_guardrails(reply: str, record: dict) -> GuardrailResult:
    # Lighter guardrail for chat answers — briefings have required sections,
    # chat replies don't, so only the hallucination check applies here
    warnings = _medication_warnings(reply, record)
    return GuardrailResult(passed=True, warnings=warnings)


# ---------------------------------------------------------------------------
# Output Guardrails — run AFTER the briefing is generated
# ---------------------------------------------------------------------------

def run_output_guardrails(briefing: str, record: dict) -> GuardrailResult:
    errors = []
    warnings = []
    briefing_lower = briefing.lower()

    # Check briefing is not suspiciously short
    word_count = len(briefing.split())
    if word_count < 50:
        errors.append(f"Briefing is suspiciously short ({word_count} words) — may be truncated or incomplete")

    # Check all required sections are present
    for section in REQUIRED_SECTIONS:
        if section not in briefing_lower:
            warnings.append(f"Missing required section: '{section.title()}'")

    # Check critical conditions are mentioned in FLAGS section specifically
    active_condition_text = " ".join(
        c.get("DESCRIPTION", "").lower()
        for c in record.get("active_conditions", [])
    )
    # Extract only the FLAGS section from the briefing
    flags_section = ""
    in_flags = False
    for line in briefing.split("\n"):
        if "flag" in line.lower() and ("#" in line or "**" in line or "---" in line):
            in_flags = True
            continue
        if in_flags:
            if line.strip().startswith("#") or "---" in line:
                break
            flags_section += line.lower() + " "

    for critical in CRITICAL_CONDITIONS:
        if critical in active_condition_text:
            if critical not in briefing_lower:
                errors.append(
                    f"CRITICAL CONDITION OMITTED: '{critical}' missing from briefing entirely"
                )
            elif critical not in flags_section and flags_section:
                errors.append(
                    f"CRITICAL FLAG MISSING: '{critical}' is active but not raised in FLAGS section"
                )

    # Hallucination check — flag any drug mentioned in briefing not traceable to source
    warnings.extend(_medication_warnings(briefing, record))

    passed = len(errors) == 0
    blocked = any(
        "critical condition omitted" in e.lower() or "suspiciously short" in e.lower()
        for e in errors
    )

    return GuardrailResult(passed=passed, blocked=blocked, warnings=warnings, errors=errors)


def print_guardrail_result(label: str, result: GuardrailResult) -> None:
    if result.passed and not result.warnings:
        print(f"✓ {label} guardrails passed")
        return

    print(f"\n=== {label.upper()} GUARDRAILS ===")
    for e in result.errors:
        print(f"  ✗ ERROR: {e}")
    for w in result.warnings:
        print(f"  ⚠ WARNING: {w}")
    if result.blocked:
        print("  → BLOCKED: Briefing will not be shown to doctor")
