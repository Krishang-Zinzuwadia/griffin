"""
State Definition — The "Company Ledger"

Single source of truth passed between all office nodes.
Uses LangGraph's Annotated pattern for state management.
"""

from typing import TypedDict, Annotated
import operator


def merge_dicts(left: dict, right: dict) -> dict:
    """Merge two dicts, with right overriding left."""
    merged = left.copy()
    merged.update(right)
    return merged


class OfficeState(TypedDict):
    """State schema for the AI Office Chain.

    Each field is populated/updated by the corresponding office node.
    """

    # ── Set by user ──────────────────────────────────────────────
    project_goal: str  # Original user prompt

    # ── Set by CEO Office ────────────────────────────────────────
    project_name: str  # URL-safe slug for the project
    file_manifest: list[str]  # List of file paths to create
    file_descriptions: dict[str, str]  # { "path": "what this file does" }

    # ── Set by Product Office ────────────────────────────────────
    tech_stack: dict[str, str]  # { "language": "JavaScript", ... }
    folder_structure: str  # ASCII tree of the project layout

    # ── Set by Engineering Office ────────────────────────────────
    codebase: Annotated[dict[str, str], merge_dicts]  # { "path": "code content" }

    # ── Set by DevOps Office ─────────────────────────────────────
    github_url: str  # Final repo URL
    vercel_url: str  # Vercel deployment URL

    # ── Shared across all offices ────────────────────────────────
    execution_logs: Annotated[list[str], operator.add]  # Append-only audit trail
