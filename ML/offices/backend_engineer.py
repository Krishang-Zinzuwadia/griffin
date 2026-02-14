"""
Backend Engineer Office — Server-Side Code

Writes all backend files (APIs, routes, middleware, business logic)
using the API schema and project context.
"""

import json
from ..state import OfficeState
from ..prompts import BACKEND_SYSTEM, CODING_HUMAN
from ..code_writer import write_files, get_files_for_engineer
from ..logger import get_logger

logger = get_logger("backend_engineer")


def backend_engineer_office(state: OfficeState) -> dict:
    """Backend Engineer node: write all backend code files."""

    logger.info("=== BACKEND ENGINEER — Entering ===")

    files_to_write = get_files_for_engineer(state, "backend_engineer")

    # Build extra context from API schema
    api_schema = state.get("api_schema", {})
    extra = ""
    if api_schema:
        extra = f"API Schema (implement these endpoints):\n{json.dumps(api_schema, indent=2)}"

    return write_files(
        state=state,
        files_to_write=files_to_write,
        office_name="BACKEND ENGINEER",
        office_emoji="⚙️",
        system_prompt=BACKEND_SYSTEM,
        human_prompt_template=CODING_HUMAN,
        extra_context=extra,
    )
