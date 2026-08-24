"""
IoT & Embedded Office - Firmware & Connectivity Notes

Generates docs/IOT_NOTES.md for the project by following the Technical
Writer pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import IOT_SYSTEM, IOT_HUMAN
from ._doc_office import run_doc_office


def iot_embedded_office(state: OfficeState) -> dict:
    """IoT & Embedded node: write docs/IOT_NOTES.md."""
    return run_doc_office(
        state,
        IOT_SYSTEM,
        IOT_HUMAN,
        office_name="IOT_EMBEDDED",
        label="IoT & Embedded",
        emoji="🔌",
        temperature=0.3,
    )
