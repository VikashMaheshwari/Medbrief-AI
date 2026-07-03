"""
Model provider layer — one place that knows how to talk to every LLM API.

A provider becomes selectable the moment its API key appears in .env:
    GROQ_API_KEY=...      → Groq (llama-3.3-70b-versatile)
    GEMINI_API_KEY=...    → Google Gemini (gemini-2.5-flash)
    OPENAI_API_KEY=...    → OpenAI (gpt-4o-mini)

Pick the default with MODEL_PROVIDER=groq|gemini|openai in .env, or switch
live via POST /provider. Gemini and OpenAI use the openai SDK (Gemini
exposes an OpenAI-compatible endpoint); Groq keeps its own SDK.
"""
import os
import time
from dotenv import load_dotenv

load_dotenv()

PROVIDER_CONFIG = {
    "groq": {
        "label": "Groq",
        "default_model": "llama-3.3-70b-versatile",
        "model_env": "GROQ_MODEL",
        "keys": ["GROQ_API_KEY"],
    },
    "gemini": {
        "label": "Google Gemini",
        "default_model": "gemini-2.5-flash",
        "model_env": "GEMINI_MODEL",
        "keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o-mini",
        "model_env": "OPENAI_MODEL",
        "keys": ["OPENAI_API_KEY"],
    },
}

RATE_LIMIT_DELAYS = (0, 3, 8)  # retry schedule (seconds) on 429

_clients: dict = {}


def _key_for(name: str) -> str | None:
    for env_var in PROVIDER_CONFIG[name]["keys"]:
        value = os.getenv(env_var)
        if value:
            return value
    return None


def is_configured(name: str) -> bool:
    return name in PROVIDER_CONFIG and _key_for(name) is not None


def model_for(name: str) -> str:
    cfg = PROVIDER_CONFIG[name]
    return os.getenv(cfg["model_env"], cfg["default_model"])


def _pick_default() -> str:
    preferred = os.getenv("MODEL_PROVIDER", "").lower()
    if preferred and is_configured(preferred):
        return preferred
    for name in PROVIDER_CONFIG:  # groq first — the original default
        if is_configured(name):
            return name
    return "groq"  # unconfigured — calls will fail with a clear key error


_active = _pick_default()


def get_active() -> str:
    return _active


def set_active(name: str) -> None:
    global _active
    if name not in PROVIDER_CONFIG:
        raise ValueError(f"Unknown provider '{name}'. Options: {', '.join(PROVIDER_CONFIG)}")
    if not is_configured(name):
        env_hint = PROVIDER_CONFIG[name]["keys"][0]
        raise ValueError(f"{PROVIDER_CONFIG[name]['label']} is not configured — add {env_hint} to your .env file and restart the API")
    _active = name


def status() -> dict:
    return {
        "active": _active,
        "providers": [
            {
                "id": name,
                "label": cfg["label"],
                "model": model_for(name),
                "configured": is_configured(name),
                "active": name == _active,
            }
            for name, cfg in PROVIDER_CONFIG.items()
        ],
    }


def _client(name: str):
    if name in _clients:
        return _clients[name]
    api_key = _key_for(name)
    if name == "groq":
        from groq import Groq
        client = Groq(api_key=api_key)
    else:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=PROVIDER_CONFIG[name].get("base_url"))
    _clients[name] = client
    return client


def _rate_limit_errors() -> tuple:
    errors = []
    try:
        from groq import RateLimitError as GroqRateLimit
        errors.append(GroqRateLimit)
    except ImportError:
        pass
    try:
        from openai import RateLimitError as OpenAIRateLimit
        errors.append(OpenAIRateLimit)
    except ImportError:
        pass
    return tuple(errors)


def chat_completion(messages: list, max_tokens: int = 1024, tools: list | None = None, tool_choice: str | None = None):
    # One call signature for every provider, with 429 retries built in
    name = _active
    client = _client(name)

    kwargs = {"model": model_for(name), "max_tokens": max_tokens, "messages": messages}
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice or "auto"

    rate_limits = _rate_limit_errors()
    last_error = None
    for delay in RATE_LIMIT_DELAYS:
        if delay:
            time.sleep(delay)
        try:
            return client.chat.completions.create(**kwargs)
        except rate_limits as e:
            last_error = e

    # Surface the provider's own explanation — a 429 can mean rate limits,
    # exhausted daily quota, or depleted billing credits
    detail = ""
    body = getattr(last_error, "body", None)
    if isinstance(body, dict):
        detail = str(body.get("message") or body.get("error", {}).get("message") or "")
    if not detail and last_error is not None:
        detail = str(last_error)[:200]
    label = PROVIDER_CONFIG[name]["label"]
    raise RuntimeError(
        f"{label} refused the request (quota/rate limit): {detail or 'try again shortly'} "
        f"— you can switch providers in Settings"
    ) from last_error
