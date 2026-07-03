import sys

sys.path.insert(0, "src")

from loader import load_patient
from agent import generate_briefing
from validator import validate, print_result


def main():
    if len(sys.argv) < 2:
        print("Usage: python brief.py <patient_id>")
        print("Example: python brief.py b084297c-c410-108c-9499-aa99d25e761c")
        sys.exit(1)

    patient_id = sys.argv[1]

    print(f"Loading patient {patient_id}...")
    record = load_patient(patient_id)

    print("Generating briefing...\n")
    briefing = generate_briefing(record)

    print("=== PATIENT BRIEFING ===")
    print(briefing)

    print("\n=== VALIDATION ===")
    result = validate(briefing, record)
    print_result(result)


if __name__ == "__main__":
    main()
