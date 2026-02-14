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
    active_offices: list[str]  # Which offices the CEO selected
    file_manifest: list[str]  # List of file paths to create
    file_descriptions: Annotated[dict[str, str], merge_dicts]

    # ── Set by Product Manager ───────────────────────────────────
    requirements: list[str]  # Feature requirements / user stories

    # ── Set by Architect ─────────────────────────────────────────
    tech_stack: dict[str, str]  # { "languages": [...], ... }
    folder_structure: str  # ASCII tree of the project layout
    file_categories: dict[str, str]  # { "path": "frontend"|"backend"|"database" }

    # ── Set by UI/UX Designer ────────────────────────────────────
    design_system: dict  # Colors, fonts, spacing, component specs

    # ── Set by API Designer ──────────────────────────────────────
    api_schema: dict  # Endpoints, methods, request/response schemas

    # ── Set by coding offices (Frontend/Backend/Database/QA/Security/TechWriter) ──
    codebase: Annotated[dict[str, str], merge_dicts]  # { "path": "code content" }

    # ── Set by DevOps Office ─────────────────────────────────────
    github_url: str  # Final repo URL
    vercel_url: str  # Vercel deployment URL

    # ── Set by Cost Optimizer & updated by all offices ───────────
    token_usage: Annotated[dict, merge_dicts]  # Token counts, costs, per-office breakdown

    # ── Shared across all offices ────────────────────────────────
    execution_logs: Annotated[list[str], operator.add]  # Append-only audit trail
