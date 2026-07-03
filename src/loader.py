import pandas as pd
from functools import lru_cache
from pathlib import Path
from filters import filter_conditions, filter_vitals, filter_procedures

DATA_DIR = Path(__file__).parent.parent / "sample_data"


@lru_cache(maxsize=1)
def _load_tables() -> dict:
    # Parse all CSVs once and keep them in memory — they never change while
    # the server runs, and observations.csv alone is expensive to re-parse
    return {
        "patients": pd.read_csv(DATA_DIR / "patients.csv"),
        "medications": pd.read_csv(DATA_DIR / "medications.csv"),
        "allergies": pd.read_csv(DATA_DIR / "allergies.csv"),
        "conditions": pd.read_csv(DATA_DIR / "conditions.csv"),
        "encounters": pd.read_csv(DATA_DIR / "encounters.csv"),
        "observations": pd.read_csv(DATA_DIR / "observations.csv"),
        "procedures": pd.read_csv(DATA_DIR / "procedures.csv"),
    }


# Conditions that mark a patient as critical on the panel — kept in sync
# with the guardrails' critical list
PANEL_CRITICAL = [
    "sepsis", "septic shock", "myocardial infarction", "anaphylaxis",
    "stroke", "pulmonary embolism", "respiratory failure", "malignant neoplasm",
]


def list_patients(query: str = "", limit: int = 100) -> list:
    # Roster for the doctor's patient panel: name, age/sex, active problem
    # counts, and critical-condition flags — enough to triage before opening
    # any chart. Sorted sickest-first, deceased last.
    tables = _load_tables()
    patients = tables["patients"]
    conditions = tables["conditions"]
    medications = tables["medications"]
    allergies = tables["allergies"]

    active_conditions = conditions[conditions["STOP"].isna()]
    active_meds = medications[medications["STOP"].isna()]

    cond_counts = active_conditions.groupby("PATIENT").size()
    med_counts = active_meds.groupby("PATIENT").size()
    allergy_counts = allergies.groupby("PATIENT").size()

    # Which patients have a critical active condition, and which one
    crit_rows = active_conditions[
        active_conditions["DESCRIPTION"].str.lower().str.contains(
            "|".join(PANEL_CRITICAL), na=False
        )
    ]
    crit_map = crit_rows.groupby("PATIENT")["DESCRIPTION"].apply(
        lambda s: sorted(set(s))
    )

    # Most recent active condition per patient — the card's "primary diagnosis"
    primary_map = (
        active_conditions.sort_values("START")
        .groupby("PATIENT")["DESCRIPTION"]
        .last()
    )

    birthdates = pd.to_datetime(patients["BIRTHDATE"], errors="coerce")
    deathdates = pd.to_datetime(patients["DEATHDATE"], errors="coerce")
    now = pd.Timestamp.now()

    roster = []
    for i, p in patients.iterrows():
        name = f"{p['FIRST']} {p['LAST']}"
        if query and query.lower() not in name.lower():
            continue

        born = birthdates.iloc[i]
        died = deathdates.iloc[i]
        deceased = pd.notna(died)
        # Age at death for deceased patients, current age otherwise
        ref = died if deceased else now
        age = int((ref - born).days // 365.25) if pd.notna(born) else None

        pid = p["Id"]
        roster.append({
            "patient_id": pid,
            "name": name,
            "age": age,
            "gender": p.get("GENDER", ""),
            "deceased": deceased,
            "active_conditions": int(cond_counts.get(pid, 0)),
            "active_medications": int(med_counts.get(pid, 0)),
            "allergies": int(allergy_counts.get(pid, 0)),
            "critical": list(crit_map.get(pid, [])),
            "primary_condition": str(primary_map.get(pid, "")),
        })

    roster.sort(key=lambda r: (r["deceased"], not r["critical"], -r["active_conditions"]))
    return roster[:limit]


def load_patient(patient_id: str) -> dict:
    tables = _load_tables()
    patients = tables["patients"]
    medications = tables["medications"]
    allergies = tables["allergies"]
    conditions = tables["conditions"]
    encounters = tables["encounters"]
    observations = tables["observations"]
    procedures = tables["procedures"]

    patient_row = patients[patients["Id"] == patient_id]
    if patient_row.empty:
        raise ValueError(f"Patient {patient_id} not found")
    patient_info = patient_row.iloc[0].to_dict()

    pt_meds = medications[medications["PATIENT"] == patient_id]
    active_meds = pt_meds[pt_meds["STOP"].isna()][
        ["DESCRIPTION", "START", "REASONDESCRIPTION"]
    ].to_dict("records")
    resolved_meds = pt_meds[pt_meds["STOP"].notna()][
        ["DESCRIPTION", "START", "STOP", "REASONDESCRIPTION"]
    ].to_dict("records")

    pt_allergies = allergies[allergies["PATIENT"] == patient_id][
        ["DESCRIPTION", "DESCRIPTION1", "SEVERITY1"]
    ].to_dict("records")

    pt_conditions = conditions[conditions["PATIENT"] == patient_id]
    active_conditions = pt_conditions[pt_conditions["STOP"].isna()][
        ["DESCRIPTION", "START"]
    ].to_dict("records")
    resolved_conditions = pt_conditions[pt_conditions["STOP"].notna()][
        ["DESCRIPTION", "START", "STOP"]
    ].to_dict("records")

    pt_encounters = encounters[encounters["PATIENT"] == patient_id].copy()
    pt_encounters["START"] = pd.to_datetime(pt_encounters["START"], utc=True)
    pt_encounters = pt_encounters.sort_values("START", ascending=False)
    last_encounter = (
        pt_encounters.iloc[0][["START", "ENCOUNTERCLASS", "DESCRIPTION"]].to_dict()
        if not pt_encounters.empty
        else {}
    )

    pt_obs = observations[observations["PATIENT"] == patient_id].copy()
    pt_obs["DATE"] = pd.to_datetime(pt_obs["DATE"], utc=True)
    pt_obs = pt_obs.sort_values("DATE", ascending=False)
    recent_vitals = pt_obs.drop_duplicates(subset="DESCRIPTION")[
        ["DESCRIPTION", "VALUE", "UNITS", "DATE"]
    ].to_dict("records")

    pt_procedures = procedures[procedures["PATIENT"] == patient_id][
        ["DESCRIPTION", "START", "REASONDESCRIPTION"]
    ].to_dict("records")

    # Apply filters so returned data is always clean
    active_conditions = filter_conditions(active_conditions)
    recent_vitals = filter_vitals(recent_vitals)
    pt_procedures = filter_procedures(pt_procedures)

    return {
        "patient_info": patient_info,
        "active_medications": active_meds,
        "resolved_medications": resolved_meds,
        "allergies": pt_allergies,
        "active_conditions": active_conditions,
        "resolved_conditions": resolved_conditions,
        "last_encounter": last_encounter,
        "recent_vitals": recent_vitals,
        "past_procedures": pt_procedures,
    }


if __name__ == "__main__":
    test_id = "b084297c-c410-108c-9499-aa99d25e761c"
    record = load_patient(test_id)

    print(f"Patient: {record['patient_info'].get('FIRST')} {record['patient_info'].get('LAST')}")
    print(f"DOB: {record['patient_info'].get('BIRTHDATE')} | Gender: {record['patient_info'].get('GENDER')}")

    print(f"\nActive Medications ({len(record['active_medications'])}):")
    for m in record["active_medications"]:
        print(f"  - {m['DESCRIPTION']}")

    print(f"\nAllergies ({len(record['allergies'])}):")
    for a in record["allergies"]:
        print(f"  - {a['DESCRIPTION']} | Severity: {a['SEVERITY1']}")

    print(f"\nActive Conditions ({len(record['active_conditions'])}):")
    for c in record["active_conditions"]:
        print(f"  - {c['DESCRIPTION']}")

    print(f"\nRecent Vitals ({len(record['recent_vitals'])}):")
    for v in record["recent_vitals"]:
        print(f"  - {v['DESCRIPTION']}: {v['VALUE']} {v['UNITS']}")

    print(f"\nPast Procedures ({len(record['past_procedures'])}):")
    for p in record["past_procedures"]:
        print(f"  - {p['DESCRIPTION']}")

    print(f"\nLast Encounter: {record['last_encounter']}")
