"""
Marketing & Growth Office - SEO & Landing Copy

Generates docs/MARKETING.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import MARKETING_SYSTEM, MARKETING_HUMAN
from ._doc_office import run_doc_office


def marketing_office(state: OfficeState) -> dict:
    """Marketing node: write docs/MARKETING.md."""
    return run_doc_office(
        state,
        MARKETING_SYSTEM,
        MARKETING_HUMAN,
        office_name="MARKETING",
        label="Marketing & Growth",
        emoji="📣",
    )
