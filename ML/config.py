"""
Configuration — Environment & LLM Setup

Loads .env from the project root and provides a configured LLM instance.
Supports two providers:
  - "openrouter" (default) — uses OpenRouter's OpenAI-compatible API
  - "gemini" — direct Google Gemini API via langchain-google-genai
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the repo root (two levels up from ML/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── Provider Config ──────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")

# ── Gemini Config ────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ── OpenRouter Config ────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ── GitHub Config ────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")

# ── Paths ────────────────────────────────────────────────────────
SANDBOX_DIR = Path(__file__).resolve().parent / "sandbox"


def get_llm(temperature: float = 0.4):
    """Return a configured LLM instance based on the LLM_PROVIDER env var.

    Provider options:
      - "openrouter" → ChatOpenAI pointed at OpenRouter's API
      - "gemini"     → ChatGoogleGenerativeAI (direct Gemini)
    """
    if LLM_PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Add it to your .env file at the project root."
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=LLM_MODEL,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
            temperature=temperature,
            default_headers={
                "HTTP-Referer": "https://github.com/Nakul-Sinha/griffin_personal",
                "X-Title": "AI Office Chain",
            },
        )

    elif LLM_PROVIDER == "gemini":
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY is not set. "
                "Add it to your .env file at the project root."
            )
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GOOGLE_API_KEY,
            temperature=temperature,
            convert_system_message_to_human=True,
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{LLM_PROVIDER}'. "
            f"Must be 'openrouter' or 'gemini'."
        )
