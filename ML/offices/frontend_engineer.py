"""
Frontend Engineer Office — Client-Side Code

Writes all frontend files (HTML, CSS, JavaScript, etc.)
using the design system and project context.
"""

import json
from ..state import OfficeState
from ..prompts import FRONTEND_SYSTEM, CODING_HUMAN
from ..code_writer import write_files, get_files_for_engineer
from ..logger import get_logger

logger = get_logger("frontend_engineer")


def frontend_engineer_office(state: OfficeState) -> dict:
    """Frontend Engineer node: write all frontend code files."""

    logger.info("=== FRONTEND ENGINEER — Entering ===")

    files_to_write = get_files_for_engineer(state, "frontend_engineer")

    # Build extra context from design system
    design_system = state.get("design_system", {})
    extra = ""
    if design_system:
        extra = f"Design System (follow these specs for styling):\n{json.dumps(design_system, indent=2)}"

    return write_files(
        state=state,
        files_to_write=files_to_write,
        office_name="FRONTEND ENGINEER",
        office_emoji="🎨",
        system_prompt=FRONTEND_SYSTEM,
        human_prompt_template=CODING_HUMAN,
        extra_context=extra,
    )
