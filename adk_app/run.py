"""
Programmatic runner for the MedBrief ADK pipeline.

Usage:
    python adk_app/run.py <patient_id>
    python adk_app/run.py            # uses a demo patient from sample_data

Streams each pipeline event (which sub-agent acted, tool calls, loop
iterations) so you can watch the multi-agent handoffs — useful for the
demo video.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from google.adk.runners import InMemoryRunner
from google.genai import types

from medbrief.agent import root_agent

DEMO_PATIENT = "b084297c-c410-108c-9499-aa99d25e761c"


async def main(patient_id: str) -> None:
    runner = InMemoryRunner(agent=root_agent, app_name="medbrief")
    session = await runner.session_service.create_session(
        app_name="medbrief", user_id="demo"
    )

    prompt = types.Content(
        role="user",
        parts=[types.Part(text=f"Brief me on patient {patient_id}")],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id="demo", session_id=session.id, new_message=prompt
    ):
        author = event.author or "?"
        # Surface tool activity so the multi-agent handoffs are visible.
        for call in event.get_function_calls():
            print(f"  [{author}] → tool: {call.name}")
        for resp in event.get_function_responses():
            print(f"  [{author}] ← tool result: {resp.name}")
        if event.content and event.content.parts:
            text = "".join(p.text or "" for p in event.content.parts)
            if text.strip():
                print(f"\n[{author}]\n{text}\n")
                final_text = text

    print("=" * 60)
    print("FINAL BRIEFING")
    print("=" * 60)
    print(final_text)


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else DEMO_PATIENT
    asyncio.run(main(pid))
