---
name: patient-briefing
description: >
  Generate a validated, doctor-facing pre-visit briefing for a synthetic
  Synthea patient. Use when the user asks to "brief me on patient <id>",
  "prepare a pre-visit summary", or mentions a patient UUID from the
  MedBrief sample data. Never use with real patient data.
---

# Patient Briefing Skill

## When to use
The user wants a pre-visit briefing for a patient in `sample_data/`
(identified by UUID). This skill wraps the MedBrief harness so the output
is validated, not just generated.

## Workflow
1. **Validate input first.** The patient ID must be a UUID present in
   `sample_data/patients.csv`. If it isn't, stop and say so — do not guess
   or invent a patient. (Input gate: corrupt/missing records are a hard stop.)
2. **Gather facts only through tools.** Run the ADK pipeline:
   ```
   python adk_app/run.py <patient_id>
   ```
   or call the MCP server tools directly (`get_patient_summary`,
   `patient_drug_interactions`, `patient_abnormal_vitals`,
   `get_patient_age`, `verify_medication`). Never state a clinical fact
   that did not come from a tool result.
3. **Structure the briefing** in exactly these sections, 150–250 words:
   PATIENT, ACTIVE CONDITIONS, MEDICATIONS, ALLERGIES, FLAGS.
4. **Audit before delivering.** Every active medication, allergy, and
   condition on the record must appear in the briefing; any drug mentioned
   must exist on the record (no hallucinated meds). If the pipeline reports
   FAIL after 3 attempts, deliver the briefing WITH its failure list —
   never hide a failed audit.

## Hard rules
- Synthetic data only. If input looks like real PHI, refuse.
- The briefing is decision support for a clinician, never medical advice.
- Do not diagnose; only restate and flag what is on the record.
