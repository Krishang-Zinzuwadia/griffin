"""
Mobile Engineering Office - Mobile Delivery Plan

Generates docs/MOBILE_PLAN.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import MOBILE_SYSTEM, MOBILE_HUMAN
from ._doc_office import run_doc_office


def mobile_office(state: OfficeState) -> dict:
    """Mobile Engineering node: write docs/MOBILE_PLAN.md."""
    return run_doc_office(
        state,
        MOBILE_SYSTEM,
        MOBILE_HUMAN,
        office_name="MOBILE",
        label="Mobile Engineering",
        emoji="📱",
        temperature=0.3,
    )
