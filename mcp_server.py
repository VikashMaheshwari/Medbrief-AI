"""
MedBrief AI — MCP Server
Exposes patient briefing tools via the Model Context Protocol.
Any MCP-compatible AI agent (Claude Desktop, etc.) can call these tools.

Run with: python mcp_server.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp.server.fastmcp import FastMCP
from loader import load_patient
from tools import calculate_age, check_drug_interaction, flag_abnormal_vitals, rxnorm_verify

mcp = FastMCP("MedBrief AI")


@mcp.tool()
def get_patient_summary(patient_id: str) -> str:
    """Load and return a structured summary of a patient's medical record."""
    try:
        record = load_patient(patient_id)
        info = record["patient_info"]
        name = f"{info.get('FIRST', '?')} {info.get('LAST', '?')}"
        dob = info.get("BIRTHDATE", "unknown")

        meds = [m.get("DESCRIPTION", "") for m in record.get("active_medications", [])]
        conditions = [c.get("DESCRIPTION", "") for c in record.get("active_conditions", [])]
        allergies = [a.get("DESCRIPTION", "") for a in record.get("allergies", [])]

        # Return COMPLETE lists — truncating here would guarantee the first
        # briefing draft omits items and waste audit-loop iterations. The
        # harness validates completeness downstream; the data feed must not
        # be the reason it fails.
        return (
            f"Patient: {name} | DOB: {dob}\n"
            f"Conditions ({len(conditions)}): {', '.join(conditions)}\n"
            f"Medications ({len(meds)}): {', '.join(meds)}\n"
            f"Allergies ({len(allergies)}): {', '.join(allergies) if allergies else 'None'}"
        )
    except Exception as e:
        return f"Error loading patient: {e}"


@mcp.tool()
def patient_drug_interactions(patient_id: str) -> str:
    """Check all active medication pairs for known dangerous interactions."""
    try:
        record = load_patient(patient_id)
        meds = [m.get("DESCRIPTION", "") for m in record.get("active_medications", [])]

        if len(meds) < 2:
            return "Patient has fewer than 2 active medications — no interactions to check."

        results = []
        for i in range(len(meds)):
            for j in range(i + 1, len(meds)):
                result = check_drug_interaction(meds[i], meds[j])
                if "INTERACTION FOUND" in result:
                    results.append(result)

        if not results:
            return f"No known interactions found among {len(meds)} active medications."
        return "\n".join(results)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def patient_abnormal_vitals(patient_id: str) -> str:
    """Check a patient's recent vitals for abnormal values."""
    try:
        record = load_patient(patient_id)
        vitals = record.get("recent_vitals", [])
        if not vitals:
            return "No recent vitals on record."
        return flag_abnormal_vitals(vitals)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def verify_medication(drug_name: str) -> str:
    """Verify that a drug name exists in the RxNorm database (hallucination check)."""
    return rxnorm_verify(drug_name)


@mcp.tool()
def get_patient_age(patient_id: str) -> str:
    """Calculate the exact current age of a patient from their date of birth."""
    try:
        record = load_patient(patient_id)
        dob = record["patient_info"].get("BIRTHDATE", "")
        if not dob:
            return "Date of birth not available."
        return calculate_age(dob)
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    # stdout belongs to the JSON-RPC protocol on stdio transport —
    # any print to stdout would corrupt it, so log to stderr instead
    print("Starting MedBrief AI MCP Server...", file=sys.stderr)
    mcp.run(transport="stdio")
