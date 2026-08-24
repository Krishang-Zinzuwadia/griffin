"""
Localization Office - Internationalization Catalog

Generates i18n/en.json for the project by following the Technical Writer
pattern through the shared documentation-office helper.
"""

from ..state import OfficeState
from ..prompts import LOCALIZATION_SYSTEM, LOCALIZATION_HUMAN
from ._doc_office import run_doc_office


def localization_office(state: OfficeState) -> dict:
    """Localization node: write i18n/en.json."""
    return run_doc_office(
        state,
        LOCALIZATION_SYSTEM,
        LOCALIZATION_HUMAN,
        office_name="LOCALIZATION",
        label="Localization",
        emoji="🌐",
        temperature=0.3,
    )
