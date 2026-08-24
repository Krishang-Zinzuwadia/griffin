"""Shared test setup for the backend API suite.

Runs everything offline: forces the mock LLM provider, clears any real
credentials, and points the database at a throwaway SQLite file. These are set
before the app package is imported so the engine binds to the temporary
database.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make the backend/api directory importable as the package root (app.*).
_API_DIR = Path(__file__).resolve().parent
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

# Offline, deterministic pipeline runs with no network and no API keys.
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ["GRIFFIN_OFFLINE"] = "1"
# Bound the worst case so a stuck child process cannot stall the suite.
os.environ.setdefault("GRIFFIN_PIPELINE_TIMEOUT", "180")
for _var in ("GITHUB_TOKEN", "GITHUB_OWNER", "VERCEL_TOKEN"):
    os.environ.pop(_var, None)

# Throwaway SQLite database for the whole test session.
_TMP_DIR = tempfile.mkdtemp(prefix="griffin-api-test-")
_DB_PATH = Path(_TMP_DIR, "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH.as_posix()}"
