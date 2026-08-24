"""
Accessibility Office - WCAG Guidance

Generates docs/ACCESSIBILITY.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import ACCESSIBILITY_SYSTEM, ACCESSIBILITY_HUMAN
from ._doc_office import run_doc_office


def accessibility_office(state: OfficeState) -> dict:
    """Accessibility node: write docs/ACCESSIBILITY.md."""
    return run_doc_office(
        state,
        ACCESSIBILITY_SYSTEM,
        ACCESSIBILITY_HUMAN,
        office_name="ACCESSIBILITY",
        label="Accessibility",
        emoji="♿",
        temperature=0.3,
    )
