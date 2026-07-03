import re
from dataclasses import dataclass, field
from pathlib import Path

GROUND_TRUTH_DIR = Path(__file__).parent.parent / "tests" / "ground_truth"

REQUIRED_SECTIONS = [
    "demographics", "allergies", "active medications",
    "active conditions", "vitals", "past procedures", "last visit", "flags"
]


@dataclass
class EvalResult:
    patient_id: str
    section_score: float       # % of required sections present
    med_coverage: float        # % of ground truth meds found in briefing
    condition_coverage: float  # % of ground truth conditions found in briefing
    flag_coverage: float       # % of ground truth flags mentioned in briefing
    overall_score: float       # weighted average
    missing_meds: list = field(default_factory=list)
    missing_conditions: list = field(default_factory=list)
    missing_flags: list = field(default_factory=list)


def _extract_section(text: str, header: str) -> list[str]:
    # Pull bullet points from a named section in the ground truth file
    lines = text.split("\n")
    in_section = False
    items = []
    for line in lines:
        if header.upper() in line.upper() and "---" in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("---"):
                break
            stripped = line.strip().lstrip("- ").strip()
            if stripped:
                items.append(stripped.lower())
    return items


# Generic words that appear in almost every briefing — matching on them
# would inflate scores. Keep only truly distinctive clinical terms.
STOPWORDS = {
    "mg", "the", "of", "and", "for", "with", "a", "an", "in", "on", "at",
    "due", "to", "disorder", "finding", "situation", "history", "acute",
    "chronic", "critical", "urgent", "status", "active", "patient",
    "medication", "medications", "review", "needed", "warranted",
    "management", "possible", "level", "note", "severely", "despite",
    "concern", "found", "documented",
}


def _keywords(phrase: str, max_keywords: int = 2) -> list[str]:
    # Longest distinctive words — "simvastatin", not "critically"
    words = [
        w for w in re.split(r"\W+", phrase.lower())
        if w and w not in STOPWORDS and len(w) > 3 and not any(c.isdigit() for c in w)
    ]
    if not words:
        return [phrase.lower()[:6]]
    words.sort(key=len, reverse=True)
    return words[:max_keywords]


def _coverage(ground_truth_items: list[str], briefing_lower: str) -> tuple[float, list[str]]:
    if not ground_truth_items:
        return 1.0, []
    missing = []
    for item in ground_truth_items:
        if not any(kw in briefing_lower for kw in _keywords(item)):
            missing.append(item)
    found = len(ground_truth_items) - len(missing)
    return round(found / len(ground_truth_items), 2), missing


def evaluate(patient_id: str, briefing: str) -> EvalResult | None:
    # Find ground truth file by patient_id prefix
    short_id = patient_id[:8]
    gt_file = GROUND_TRUTH_DIR / f"{short_id}.txt"

    if not gt_file.exists():
        # No ground truth for this patient — can't score, so don't pretend to.
        # Returning 0.0 here would silently drag down the /metrics average.
        return None

    gt_text = gt_file.read_text(encoding="utf-8")
    briefing_lower = briefing.lower()

    # Section completeness
    sections_found = sum(1 for s in REQUIRED_SECTIONS if s in briefing_lower)
    section_score = round(sections_found / len(REQUIRED_SECTIONS), 2)

    # Medication coverage
    gt_meds = _extract_section(gt_text, "ACTIVE MEDICATIONS")
    med_score, missing_meds = _coverage(gt_meds, briefing_lower)

    # Condition coverage
    gt_conditions = _extract_section(gt_text, "ACTIVE CONDITIONS")
    cond_score, missing_conditions = _coverage(gt_conditions, briefing_lower)

    # Flag coverage
    gt_flags = _extract_section(gt_text, "FLAGS")
    flag_score, missing_flags = _coverage(gt_flags, briefing_lower)

    # Weighted overall: sections 20%, meds 30%, conditions 30%, flags 20%
    overall = round(
        section_score * 0.20 +
        med_score * 0.30 +
        cond_score * 0.30 +
        flag_score * 0.20,
        2
    )

    return EvalResult(
        patient_id=patient_id,
        section_score=section_score,
        med_coverage=med_score,
        condition_coverage=cond_score,
        flag_coverage=flag_score,
        overall_score=overall,
        missing_meds=missing_meds,
        missing_conditions=missing_conditions,
        missing_flags=missing_flags,
    )


def print_eval(result: EvalResult) -> None:
    grade = "A" if result.overall_score >= 0.85 else "B" if result.overall_score >= 0.70 else "C" if result.overall_score >= 0.55 else "F"
    print(f"\n{'='*50}")
    print(f"EVAL: {result.patient_id[:8]}  |  Grade: {grade}  |  Score: {result.overall_score*100:.0f}%")
    print(f"  Sections:   {result.section_score*100:.0f}%")
    print(f"  Meds:       {result.med_coverage*100:.0f}%  {'✓' if not result.missing_meds else '✗ missing: ' + ', '.join(result.missing_meds[:3])}")
    print(f"  Conditions: {result.condition_coverage*100:.0f}%  {'✓' if not result.missing_conditions else '✗ missing: ' + ', '.join(result.missing_conditions[:3])}")
    print(f"  Flags:      {result.flag_coverage*100:.0f}%  {'✓' if not result.missing_flags else '✗ missing: ' + ', '.join(result.missing_flags[:2])}")
