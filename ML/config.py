"""
Configuration — Environment & LLM Setup

Loads .env from the project root and provides a configured LLM instance.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load .env from the repo root (two levels up from ML/)
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

# ── LLM Config ───────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")

# ── GitHub Config ────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")

# ── Paths ────────────────────────────────────────────────────────
SANDBOX_DIR = Path(__file__).resolve().parent / "sandbox"


def get_llm(temperature: float = 0.4) -> ChatGoogleGenerativeAI:
    """Return a configured Gemini LLM instance."""
    if not GOOGLE_API_KEY:
        raise ValueError(
            "GOOGLE_API_KEY is not set. "
            "Add it to your .env file at the project root."
        )
    return ChatGoogleGenerativeAI(
        model=LLM_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,
    )
