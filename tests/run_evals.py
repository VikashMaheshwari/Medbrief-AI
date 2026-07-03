"""
Eval runner — generates briefings for all 5 ground truth patients and scores them.
Run with: python tests/run_evals.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loader import load_patient
from agent import generate_briefing_with_loop
from evals import evaluate, print_eval

PATIENTS = [
    "b084297c-c410-108c-9499-aa99d25e761c",
    "d6fc4f34-2b72-5a02-2079-b34c84bea79e",
    "4e81c560-e4ac-8ab5-2afc-8db5abae0a68",
    "e60e1ddc-b54e-a6f2-14d3-bb142465e33a",
    "ca4f2fef-12f2-faee-5f5d-43a8bf95e7e7",
]

if __name__ == "__main__":
    scores = []
    print("Running evals against ground truth...\n")

    for pid in PATIENTS:
        print(f"Generating briefing for {pid[:8]}...", end=" ", flush=True)
        try:
            record = load_patient(pid)
            loop_result = generate_briefing_with_loop(record, max_retries=2)
            briefing = loop_result["briefing"]
            attempts = loop_result["attempts"]
            print(f"done ({attempts} attempt{'s' if attempts > 1 else ''})")

            result = evaluate(pid, briefing)
            if result is None:
                print("no ground truth file — skipped")
                continue
            print_eval(result)
            scores.append(result.overall_score)
        except Exception as e:
            print(f"ERROR: {e}")

    if scores:
        avg = round(sum(scores) / len(scores) * 100, 1)
        print(f"\n{'='*50}")
        print(f"OVERALL EVAL SCORE: {avg}% across {len(scores)} patients")
        grade = "A" if avg >= 85 else "B" if avg >= 70 else "C" if avg >= 55 else "F"
        print(f"GRADE: {grade}")
