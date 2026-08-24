"""
Legal & Compliance Office - Terms of Service & Privacy Policy

Generates TERMS.md and PRIVACY.md for the project by following the
Technical Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import LEGAL_SYSTEM, LEGAL_HUMAN
from ._doc_office import run_doc_office


def legal_compliance_office(state: OfficeState) -> dict:
    """Legal & Compliance node: write TERMS.md and PRIVACY.md."""
    return run_doc_office(
        state,
        LEGAL_SYSTEM,
        LEGAL_HUMAN,
        office_name="LEGAL_COMPLIANCE",
        label="Legal & Compliance",
        emoji="⚖️",
        temperature=0.3,
    )
