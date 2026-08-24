"""
UX Research Office - Personas & User Flows

Generates docs/USER_FLOWS.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import UX_RESEARCH_SYSTEM, UX_RESEARCH_HUMAN
from ._doc_office import run_doc_office


def ux_research_office(state: OfficeState) -> dict:
    """UX Research node: write docs/USER_FLOWS.md."""
    return run_doc_office(
        state,
        UX_RESEARCH_SYSTEM,
        UX_RESEARCH_HUMAN,
        office_name="UX_RESEARCH",
        label="UX Research",
        emoji="🧭",
    )
