"""
Database Engineer Office — Schema & Data

Writes all database files (schemas, migrations, models, seed data)
using the project context.
"""

from ..state import OfficeState
from ..prompts import DATABASE_SYSTEM, CODING_HUMAN
from ..code_writer import write_files, get_files_for_engineer
from ..logger import get_logger

logger = get_logger("database_engineer")


def database_engineer_office(state: OfficeState) -> dict:
    """Database Engineer node: write all database code files."""

    logger.info("=== DATABASE ENGINEER — Entering ===")

    files_to_write = get_files_for_engineer(state, "database_engineer")

    return write_files(
        state=state,
        files_to_write=files_to_write,
        office_name="DATABASE ENGINEER",
        office_emoji="🗄️",
        system_prompt=DATABASE_SYSTEM,
        human_prompt_template=CODING_HUMAN,
        extra_context="",
    )
