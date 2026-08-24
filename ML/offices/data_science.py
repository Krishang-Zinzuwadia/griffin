"""
Data Science Office - Analytics & Pipeline Notes

Generates docs/DATA_SCIENCE.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import DATA_SCIENCE_SYSTEM, DATA_SCIENCE_HUMAN
from ._doc_office import run_doc_office


def data_science_office(state: OfficeState) -> dict:
    """Data Science node: write docs/DATA_SCIENCE.md."""
    return run_doc_office(
        state,
        DATA_SCIENCE_SYSTEM,
        DATA_SCIENCE_HUMAN,
        office_name="DATA_SCIENCE",
        label="Data Science",
        emoji="📊",
        temperature=0.3,
    )
