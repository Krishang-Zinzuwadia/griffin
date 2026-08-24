"""
Performance Engineering Office - Performance Budget & Optimizations

Generates docs/PERFORMANCE.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import PERFORMANCE_SYSTEM, PERFORMANCE_HUMAN
from ._doc_office import run_doc_office


def performance_office(state: OfficeState) -> dict:
    """Performance node: write docs/PERFORMANCE.md."""
    return run_doc_office(
        state,
        PERFORMANCE_SYSTEM,
        PERFORMANCE_HUMAN,
        office_name="PERFORMANCE",
        label="Performance Engineering",
        emoji="⚡",
        temperature=0.3,
    )
