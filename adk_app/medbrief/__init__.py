"""
MedBrief ADK agent package.

ADK's discovery convention: `adk web adk_app` (or `adk run adk_app/medbrief`)
imports this package and looks for `agent.root_agent`.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# ADK's Gemini client reads GOOGLE_API_KEY; this project uses GEMINI_API_KEY.
# GEMINI_API_KEY from .env ALWAYS wins — otherwise a stale GOOGLE_API_KEY in
# the Windows/system environment silently overrides the key you just updated.
if os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]
# Use the public Gemini API (AI Studio key), not Vertex AI.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

from . import agent  # noqa: E402,F401
