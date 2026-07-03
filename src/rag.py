import chromadb
from pathlib import Path

# ChromaDB stores its index here — persists across server restarts
DB_PATH = str(Path(__file__).parent.parent / "chroma_db")

# Medical knowledge base — facts a doctor would want flagged automatically
MEDICAL_KNOWLEDGE = [
    # Diabetes
    {"id": "dm-001", "text": "Metformin is contraindicated when eGFR drops below 30 mL/min/1.73m². Dose reduction recommended at eGFR 30-45. Monitor renal function every 3-6 months in diabetic patients."},
    {"id": "dm-002", "text": "Hemoglobin A1c target for most Type 2 Diabetes patients is below 7%. A1c above 9% indicates poor glycemic control and urgent medication review is warranted."},
    {"id": "dm-003", "text": "Diabetic patients on ACE inhibitors (e.g., Lisinopril) require regular potassium monitoring due to risk of hyperkalemia, especially with renal impairment."},
    {"id": "dm-004", "text": "SGLT2 inhibitors (e.g., empagliflozin, dapagliflozin) reduce cardiovascular mortality in Type 2 Diabetes patients with established heart disease."},

    # Cardiovascular
    {"id": "cv-001", "text": "Patients on dual antiplatelet therapy (aspirin + clopidogrel or prasugrel) have significantly elevated bleeding risk. Concomitant NSAIDs or anticoagulants should be avoided."},
    {"id": "cv-002", "text": "Beta-blockers (metoprolol, carvedilol) should not be abruptly stopped in cardiac patients — withdrawal can precipitate rebound tachycardia or angina."},
    {"id": "cv-003", "text": "Statin therapy (simvastatin, atorvastatin) is first-line for LDL reduction in cardiovascular disease. LDL target is below 70 mg/dL in high-risk patients."},
    {"id": "cv-004", "text": "Warfarin patients require INR monitoring every 4 weeks when stable. Concurrent aspirin use increases major bleeding risk by 2-3x."},
    {"id": "cv-005", "text": "Troponin elevation above 0.04 ng/mL in the context of chest pain is diagnostic of acute myocardial infarction and requires emergency cardiology consultation."},

    # Renal
    {"id": "renal-001", "text": "Chronic Kidney Disease staging: Stage 3 (GFR 30-59), Stage 4 (GFR 15-29), Stage 5 (GFR <15, dialysis). Multiple medications require dose adjustment in Stage 3+."},
    {"id": "renal-002", "text": "Renal transplant patients require lifelong immunosuppression (tacrolimus, mycophenolate). Infection risk is elevated. Any fever must be taken seriously."},
    {"id": "renal-003", "text": "NSAIDs (ibuprofen, naproxen) are contraindicated in CKD patients — they reduce renal blood flow and can precipitate acute kidney injury."},
    {"id": "renal-004", "text": "ACE inhibitors and ARBs are nephroprotective in CKD with proteinuria but require potassium and creatinine monitoring within 2 weeks of initiation or dose change."},

    # Respiratory
    {"id": "resp-001", "text": "COPD patients on long-acting bronchodilators (tiotropium, salmeterol) should receive annual influenza vaccine and pneumococcal vaccine every 5 years."},
    {"id": "resp-002", "text": "Non-selective beta-blockers (propranolol) are contraindicated in asthma and COPD — they can precipitate severe bronchospasm. Use cardioselective beta-blockers (metoprolol) with caution."},

    # Oncology
    {"id": "onco-001", "text": "Lung cancer patients on chemotherapy require CBC monitoring before each cycle. Neutrophil count below 1.0 x10^9/L warrants dose delay or G-CSF support."},
    {"id": "onco-002", "text": "Colon cancer post-resection patients require colonoscopy surveillance at 1 year, then every 3-5 years. CEA monitoring every 3-6 months for 5 years."},

    # Allergy / Anaphylaxis
    {"id": "allergy-001", "text": "Patients with documented anaphylaxis history should carry epinephrine auto-injector at all times. Prescribers should also consider referral to allergy/immunology."},
    {"id": "allergy-002", "text": "Penicillin allergy is reported in 10% of patients but only 1% have true IgE-mediated reactions. Cross-reactivity with cephalosporins is less than 2%."},

    # Sepsis
    {"id": "sepsis-001", "text": "Sepsis bundle (Hour-1): blood cultures before antibiotics, broad-spectrum antibiotics within 1 hour, 30ml/kg IV crystalloid for hypotension, vasopressors if MAP <65 after fluids."},
    {"id": "sepsis-002", "text": "Post-sepsis patients are at high risk for long-term cognitive impairment, fatigue, and secondary infections. Follow-up within 30 days of discharge is recommended."},
]


def build_knowledge_base() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=DB_PATH)

    # Delete and rebuild if already exists (ensures clean state on restart)
    try:
        client.delete_collection("medical_knowledge")
    except Exception:
        pass

    collection = client.create_collection(
        name="medical_knowledge",
        # ChromaDB uses its built-in sentence transformer for embeddings — no API key needed
        metadata={"hnsw:space": "cosine"}
    )

    collection.add(
        ids=[k["id"] for k in MEDICAL_KNOWLEDGE],
        documents=[k["text"] for k in MEDICAL_KNOWLEDGE],
    )

    return collection


def get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=DB_PATH)
    try:
        return client.get_collection("medical_knowledge")
    except Exception:
        return build_knowledge_base()


def retrieve(query: str, top_k: int = 3) -> list[str]:
    # Finds the most relevant medical facts for a given patient query
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, len(MEDICAL_KNOWLEDGE))
    )
    return results["documents"][0]  # list of matching fact strings


def build_rag_query(record: dict) -> str:
    # Builds a natural-language query from the patient record
    # ChromaDB will find facts semantically similar to this
    parts = []

    conditions = [c.get("DESCRIPTION", "") for c in record.get("active_conditions", [])]
    if conditions:
        parts.append("Conditions: " + ", ".join(conditions[:5]))

    meds = [m.get("DESCRIPTION", "") for m in record.get("active_medications", [])]
    if meds:
        parts.append("Medications: " + ", ".join(meds[:5]))

    allergies = [a.get("DESCRIPTION", "") for a in record.get("allergies", [])]
    if allergies:
        parts.append("Allergies: " + ", ".join(allergies[:3]))

    return ". ".join(parts)


if __name__ == "__main__":
    print("Building knowledge base...")
    build_knowledge_base()
    print("Done. Testing retrieval...")

    query = "Type 2 Diabetes patient on Metformin with renal impairment"
    facts = retrieve(query)
    print(f"\nQuery: {query}")
    print("\nTop matches:")
    for i, fact in enumerate(facts, 1):
        print(f"\n{i}. {fact}")
