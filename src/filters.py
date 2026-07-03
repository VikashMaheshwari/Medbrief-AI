# Keywords that identify non-clinical social/lifestyle conditions logged by Synthea.
# If any of these appear in a condition description, we treat it as noise and drop it.
NON_CLINICAL_KEYWORDS = [
    "employment", "education", "housing", "stress",
    "social contact", "criminal record", "refugee",
    "migrant", "income", "insurance", "address",
    "language", "hispanic", "race", "armed forces",
    "partner", "jail", "prison", "transportation",
    "utilities", "farm work", "losing your housing",
    "people are living", "physically and emotionally",
    "afraid of your partner"
]

# Keywords that identify clinically significant procedures worth surfacing in the briefing.
# Routine repeated procedures (screenings, eye exams) are excluded — only notable ones are kept.
NOTABLE_PROCEDURE_KEYWORDS = [
    "intervention", "surgery", "angiography", "colonoscopy",
    "polypectomy", "biopsy", "transplant", "implant",
    "resection", "amputation", "dialysis", "chemotherapy",
    "echocardiography", "cardiovascular stress"
]


def filter_conditions(conditions: list) -> list:
    # Loops through every condition and checks if its description contains
    # any non-clinical keyword. If it does, it's social noise and gets dropped.
    # Only real medical diagnoses/disorders make it into the cleaned list.
    cleaned = []
    for condition in conditions:
        description = condition["DESCRIPTION"].lower()  # lowercase so matching is case-insensitive
        is_noise = any(keyword in description for keyword in NON_CLINICAL_KEYWORDS)
        if not is_noise:
            cleaned.append(condition)
    return cleaned


# Allowlist of keywords for clinically important vitals.
# Only vitals whose description matches one of these are kept.
# This is more precise than trying to exclude noise — the list of important vitals
# is smaller and more stable than the ever-growing list of Synthea noise.
CLINICAL_VITAL_KEYWORDS = [
    # Core vitals
    "systolic blood pressure", "diastolic blood pressure",
    "heart rate", "respiratory rate", "body weight",
    "body height", "body mass index",

    # Diabetes
    "hemoglobin a1c", "glucose",

    # Lipids
    "cholesterol", "triglyceride",

    # Kidney
    "creatinine", "glomerular filtration rate", "microalbumin",
    "urea nitrogen",

    # Blood count
    "hemoglobin [mass", "hematocrit", "leukocytes", "platelets [#",

    # Cardiac
    "troponin", "natriuretic peptide",

    # Eye
    "intraocular pressure", "visual acuity", "retina",

    # Liver
    "alanine aminotransferase", "aspartate aminotransferase",
    "bilirubin", "albumin",
]


# Units that look like measurements but are actually scores or qualitative labels.
NON_CLINICAL_UNITS = ["{nominal}", "{logmar}"]


def filter_vitals(vitals: list) -> list:
    # Two-step filter:
    # 1. Description must match a known clinical keyword (allowlist)
    # 2. Unit must not be a non-clinical scoring/qualitative unit (blocklist)
    # Both conditions must be true for a vital to be kept.
    cleaned = []
    for vital in vitals:
        description = vital.get("DESCRIPTION", "").lower()
        units = str(vital.get("UNITS", "")).strip().lower()
        is_clinical = any(keyword in description for keyword in CLINICAL_VITAL_KEYWORDS)
        is_bad_unit = any(units == bad for bad in NON_CLINICAL_UNITS)
        if is_clinical and not is_bad_unit:
            cleaned.append(vital)
    return cleaned


def filter_procedures(procedures: list) -> list:
    # Two-step filter:
    # 1. Keep only procedures that match a notable keyword (surgical, diagnostic, interventional)
    # 2. Deduplicate — the same procedure can appear dozens of times across visits;
    #    we only want one entry per unique procedure type.
    # 'seen' is a set (not a list) because checking membership in a set is much faster.
    seen = set()
    cleaned = []
    for procedure in procedures:
        description = procedure["DESCRIPTION"].lower()
        is_notable = any(keyword in description for keyword in NOTABLE_PROCEDURE_KEYWORDS)
        if is_notable and description not in seen:
            seen.add(description)
            cleaned.append(procedure)
    return cleaned
