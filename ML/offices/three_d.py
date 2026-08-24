"""
3D & Spatial Office - 3D and WebGL Scene Notes

Generates docs/3D_NOTES.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import THREE_D_SYSTEM, THREE_D_HUMAN
from ._doc_office import run_doc_office


def three_d_office(state: OfficeState) -> dict:
    """3D & Spatial node: write docs/3D_NOTES.md."""
    return run_doc_office(
        state,
        THREE_D_SYSTEM,
        THREE_D_HUMAN,
        office_name="THREE_D",
        label="3D & Spatial",
        emoji="🧊",
        temperature=0.3,
    )
