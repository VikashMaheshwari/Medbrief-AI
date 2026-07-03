import httpx
from datetime import date, datetime


# ---------------------------------------------------------------------------
# Tool 1 — calculate_age
# ---------------------------------------------------------------------------

def calculate_age(birthdate: str) -> str:
    # Calculates exact age in years from a birthdate string (YYYY-MM-DD)
    try:
        dob = datetime.strptime(birthdate, "%Y-%m-%d").date()
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return f"{age} years old"
    except Exception as e:
        return f"Could not calculate age: {e}"


# ---------------------------------------------------------------------------
# Tool 2 — check_drug_interaction
# ---------------------------------------------------------------------------

# Known dangerous drug pairs — expand as needed
DRUG_INTERACTIONS = {
    frozenset(["warfarin", "aspirin"]): "HIGH RISK — increased bleeding risk",
    frozenset(["warfarin", "ibuprofen"]): "HIGH RISK — increased bleeding risk",
    frozenset(["metformin", "alcohol"]): "MODERATE — risk of lactic acidosis",
    frozenset(["simvastatin", "amlodipine"]): "MODERATE — increased statin exposure, myopathy risk",
    frozenset(["clopidogrel", "aspirin"]): "MODERATE — dual antiplatelet, increased bleeding risk",
    frozenset(["prasugrel", "aspirin"]): "MODERATE — dual antiplatelet, increased bleeding risk",
    frozenset(["lisinopril", "potassium"]): "MODERATE — risk of hyperkalemia",
    frozenset(["metoprolol", "verapamil"]): "HIGH RISK — severe bradycardia risk",
    frozenset(["fentanyl", "hydrocodone"]): "HIGH RISK — dual opioid, respiratory depression risk",
    frozenset(["nitroglycerin", "sildenafil"]): "HIGH RISK — severe hypotension",
}


def check_drug_interaction(med1: str, med2: str) -> str:
    # Checks if two medications have a known interaction
    # Matches by keyword so full drug names still work
    med1_lower = med1.lower()
    med2_lower = med2.lower()

    for pair, warning in DRUG_INTERACTIONS.items():
        keywords = list(pair)
        if (keywords[0] in med1_lower or keywords[0] in med2_lower) and \
           (keywords[1] in med1_lower or keywords[1] in med2_lower):
            return f"INTERACTION FOUND between {med1} and {med2}: {warning}"

    return f"No known interaction found between {med1} and {med2}"


# ---------------------------------------------------------------------------
# Tool 3 — flag_abnormal_vitals
# ---------------------------------------------------------------------------

# Normal ranges: (low, high) — values outside this range are flagged
NORMAL_RANGES = {
    "systolic blood pressure": (90, 140),
    "diastolic blood pressure": (60, 90),
    "heart rate": (60, 100),
    "respiratory rate": (12, 20),
    "hemoglobin a1c": (0, 5.7),
    "glucose": (70, 99),
    "cholesterol": (0, 200),
    "cholesterol in ldl": (0, 100),
    "triglyceride": (0, 150),
    "creatinine": (0.6, 1.2),
    "glomerular filtration rate": (60, 999),
    "hemoglobin [mass": (12.0, 17.5),
    "troponin": (0, 0.04),
    "bilirubin.total": (0, 1.2),
    "alanine aminotransferase": (0, 56),
    "aspartate aminotransferase": (0, 40),
}


def flag_abnormal_vitals(vitals: list) -> str:
    # Compares each vital against known normal ranges
    # Returns a list of flagged abnormal values
    flags = []
    for vital in vitals:
        description = vital.get("DESCRIPTION", "").lower()
        value = vital.get("VALUE")
        units = vital.get("UNITS", "")

        if value is None:
            continue

        try:
            numeric_value = float(str(value))
        except (ValueError, TypeError):
            continue

        for key, (low, high) in NORMAL_RANGES.items():
            if key in description:
                if numeric_value < low:
                    flags.append(f"LOW: {vital['DESCRIPTION']} = {value} {units} (normal: {low}-{high})")
                elif numeric_value > high:
                    flags.append(f"HIGH: {vital['DESCRIPTION']} = {value} {units} (normal: {low}-{high})")
                break

    if not flags:
        return "All checked vitals are within normal ranges"
    return "\n".join(flags)


# ---------------------------------------------------------------------------
# Tool 4 — rxnorm_verify
# ---------------------------------------------------------------------------

def rxnorm_verify(drug_name: str) -> str:
    # Calls the free RxNorm API to verify a drug name is real
    # No API key required — completely free
    try:
        url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug_name}&search=1"
        response = httpx.get(url, timeout=5)
        data = response.json()
        ids = data.get("idGroup", {}).get("rxnormId", [])
        if ids:
            return f"VERIFIED: '{drug_name}' is a recognized drug (RxNorm ID: {ids[0]})"
        return f"UNVERIFIED: '{drug_name}' was not found in RxNorm — possible hallucination"
    except Exception as e:
        return f"RxNorm check failed: {e}"


# ---------------------------------------------------------------------------
# Tool schemas — sent to Groq so the model knows what tools are available
# ---------------------------------------------------------------------------

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_age",
            "description": "Calculate a patient's exact age from their date of birth",
            "parameters": {
                "type": "object",
                "properties": {
                    "birthdate": {
                        "type": "string",
                        "description": "Date of birth in YYYY-MM-DD format"
                    }
                },
                "required": ["birthdate"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_drug_interaction",
            "description": "Check if two medications have a known dangerous interaction",
            "parameters": {
                "type": "object",
                "properties": {
                    "med1": {"type": "string", "description": "First medication name"},
                    "med2": {"type": "string", "description": "Second medication name"}
                },
                "required": ["med1", "med2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "flag_abnormal_vitals",
            "description": "Check a list of vitals against normal ranges and flag any abnormal values",
            "parameters": {
                "type": "object",
                "properties": {
                    "vitals": {
                        "type": "array",
                        "description": "List of vital objects with DESCRIPTION, VALUE, and UNITS keys",
                        "items": {"type": "object"}
                    }
                },
                "required": ["vitals"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rxnorm_verify",
            "description": "Verify a drug name exists in the RxNorm database to detect hallucinated drug names",
            "parameters": {
                "type": "object",
                "properties": {
                    "drug_name": {"type": "string", "description": "The drug name to verify"}
                },
                "required": ["drug_name"]
            }
        }
    }
]


# ---------------------------------------------------------------------------
# Tool dispatcher — routes tool call requests from the model to actual functions
# ---------------------------------------------------------------------------

def run_tool(tool_name: str, tool_args: dict) -> str:
    # Called by agent.py when Groq requests a tool call
    if tool_name == "calculate_age":
        return calculate_age(**tool_args)
    elif tool_name == "check_drug_interaction":
        return check_drug_interaction(**tool_args)
    elif tool_name == "flag_abnormal_vitals":
        return flag_abnormal_vitals(**tool_args)
    elif tool_name == "rxnorm_verify":
        return rxnorm_verify(**tool_args)
    else:
        return f"Unknown tool: {tool_name}"
