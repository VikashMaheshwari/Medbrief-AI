from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    passed: bool
    missing_medications: list = field(default_factory=list)
    missing_allergies: list = field(default_factory=list)
    missing_conditions: list = field(default_factory=list)


# Words to strip when extracting key searchable terms from a long description.
# e.g. "24 HR Metformin hydrochloride 500 MG Extended Release Oral Tablet" → "metformin"
STRIP_WORDS = {
    "oral", "tablet", "capsule", "mg", "ml", "hr", "24", "12", "72",
    "extended", "release", "hydrochloride", "sodium", "potassium",
    "bitartrate", "succinate", "mucosal", "spray", "transdermal",
    "system", "inject", "solution", "actuat", "nda020800",
    # generic clinical filler — never distinctive enough to match on
    "disorder", "finding", "situation", "history", "acute", "chronic",
}


def extract_keywords(description: str, max_keywords: int = 2) -> list:
    # Return the most DISTINCTIVE words, not the first ones.
    # First-word matching was too generous: "History of myocardial infarction"
    # gave "history", which matches almost any briefing. Longest words like
    # "myocardial" are far more specific.
    candidates = []
    for word in description.lower().split():
        cleaned = word.strip("()[].,/")
        if (cleaned
                and cleaned not in STRIP_WORDS
                and len(cleaned) > 3
                and not any(ch.isdigit() for ch in cleaned)):
            candidates.append(cleaned)

    if not candidates:
        return [description.lower()]

    # sort is stable — equal-length words keep their original order
    candidates.sort(key=len, reverse=True)
    return candidates[:max_keywords]


def validate(briefing: str, record: dict) -> ValidationResult:
    briefing_lower = briefing.lower()

    missing_meds = []
    missing_allergies = []
    missing_conditions = []

    # An item counts as present if ANY of its distinctive keywords appears
    def _found(description: str) -> bool:
        return any(kw in briefing_lower for kw in extract_keywords(description))

    for med in record["active_medications"]:
        if not _found(med["DESCRIPTION"]):
            missing_meds.append(med["DESCRIPTION"])

    for allergy in record["allergies"]:
        if not _found(allergy["DESCRIPTION"]):
            missing_allergies.append(allergy["DESCRIPTION"])

    for condition in record["active_conditions"]:
        if not _found(condition["DESCRIPTION"]):
            missing_conditions.append(condition["DESCRIPTION"])

    passed = not missing_meds and not missing_allergies and not missing_conditions

    return ValidationResult(
        passed=passed,
        missing_medications=missing_meds,
        missing_allergies=missing_allergies,
        missing_conditions=missing_conditions,
    )


def print_result(result: ValidationResult) -> None:
    # Print a clear PASS/FAIL report with details of any missing items
    if result.passed:
        print("\n✓ VALIDATION PASSED — all required items found in briefing")
    else:
        print("\n✗ VALIDATION FAILED — the following items are missing from the briefing:")
        if result.missing_medications:
            print("\n  Missing Medications:")
            for m in result.missing_medications:
                print(f"    - {m}")
        if result.missing_allergies:
            print("\n  Missing Allergies:")
            for a in result.missing_allergies:
                print(f"    - {a}")
        if result.missing_conditions:
            print("\n  Missing Conditions:")
            for c in result.missing_conditions:
                print(f"    - {c}")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from loader import load_patient
    from agent import generate_briefing

    test_id = "b084297c-c410-108c-9499-aa99d25e761c"
    record = load_patient(test_id)
    briefing = generate_briefing(record)

    print("=== GENERATED BRIEFING ===")
    print(briefing)

    result = validate(briefing, record)
    print_result(result)
