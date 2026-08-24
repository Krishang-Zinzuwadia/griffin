"""
Design Systems Office - Design Tokens

Generates design_tokens.json for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import DESIGN_SYSTEMS_SYSTEM, DESIGN_SYSTEMS_HUMAN
from ._doc_office import run_doc_office


def design_systems_office(state: OfficeState) -> dict:
    """Design Systems node: write design_tokens.json."""
    return run_doc_office(
        state,
        DESIGN_SYSTEMS_SYSTEM,
        DESIGN_SYSTEMS_HUMAN,
        office_name="DESIGN_SYSTEMS",
        label="Design Systems",
        emoji="🎨",
        temperature=0.3,
    )
