"""
AI & Machine Learning Office - AI Integration Notes

Generates docs/AI_INTEGRATION.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import AI_ML_SYSTEM, AI_ML_HUMAN
from ._doc_office import run_doc_office


def ai_ml_office(state: OfficeState) -> dict:
    """AI & Machine Learning node: write docs/AI_INTEGRATION.md."""
    return run_doc_office(
        state,
        AI_ML_SYSTEM,
        AI_ML_HUMAN,
        office_name="AI_ML",
        label="AI & Machine Learning",
        emoji="🤖",
        temperature=0.3,
    )
