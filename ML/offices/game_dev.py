"""
Game Development Office - Game Design & Loop Notes

Generates docs/GAME_DESIGN.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import GAME_DEV_SYSTEM, GAME_DEV_HUMAN
from ._doc_office import run_doc_office


def game_dev_office(state: OfficeState) -> dict:
    """Game Development node: write docs/GAME_DESIGN.md."""
    return run_doc_office(
        state,
        GAME_DEV_SYSTEM,
        GAME_DEV_HUMAN,
        office_name="GAME_DEV",
        label="Game Development",
        emoji="🎮",
        temperature=0.3,
    )
