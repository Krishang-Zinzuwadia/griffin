"""
Code Writer — Shared utility for coding offices.

Provides a reusable file-writing loop used by frontend_engineer,
backend_engineer, and database_engineer offices.
"""

import json
import time
from colorama import Fore, Style
from .config import get_llm
from .utils import (
    invoke_llm_with_retry,
    validate_engineering_output,
    build_previous_code_context,
)
from .logger import get_logger

# ── Live events ──────────────────────────────────────────────────
# Coding offices emit a machine readable event per file so the ML service can
# stream generated code straight to the frontend as it lands.
EVENT_PREFIX = "@@GRIFFIN_EVENT "

_LANGUAGE_BY_EXT = {
    "html": "html",
    "css": "css",
    "js": "javascript",
    "mjs": "javascript",
    "jsx": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "py": "python",
    "json": "json",
    "md": "markdown",
}


def _language_for(filepath: str) -> str:
    """Map a file path to a highlight language by its extension."""
    ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    return _LANGUAGE_BY_EXT.get(ext, "plaintext")


def _emit_code_artifact(filepath: str, content: str) -> None:
    """Emit a live code_artifact event for a freshly written file."""
    try:
        payload = {
            "kind": "code_artifact",
            "filename": filepath,
            "language": _language_for(filepath),
            "code": content,
            "progress": 100,
            "status": "complete",
        }
        print(EVENT_PREFIX + json.dumps(payload), flush=True)
    except Exception:
        pass


def write_files(
    state: dict,
    files_to_write: list[str],
    office_name: str,
    office_emoji: str,
    system_prompt: str,
    human_prompt_template: str,
    extra_context: str = "",
) -> dict:
    """Shared file-writing loop for coding offices.

    Args:
        state: Current OfficeState dict
        files_to_write: List of file paths this office should write
        office_name: Display name (e.g. "FRONTEND ENGINEER")
        office_emoji: Emoji for terminal output
        system_prompt: System prompt for this office's specialty
        human_prompt_template: Human prompt template with {placeholders}
        extra_context: Extra context to inject (design_system, api_schema, etc.)

    Returns:
        dict with "codebase" and "execution_logs" keys
    """
    logger = get_logger(office_name.lower().replace(" ", "_"))
    logger.info(f"=== {office_name} — Entering ===")
    logger.info(f"Files to write: {len(files_to_write)}")
    office_start = time.time()

    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"  {office_emoji}  {office_name}")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    if not files_to_write:
        msg = f"[{office_name.upper()}] No files assigned — skipping."
        logger.info(msg)
        print(f"  {Fore.YELLOW}⏭️  {msg}{Style.RESET_ALL}")
        return {"codebase": {}, "execution_logs": [msg]}

    llm = get_llm(temperature=0.4)
    file_manifest = state.get("file_manifest", [])
    file_descriptions = state.get("file_descriptions", {})
    tech_stack = state.get("tech_stack", {})
    folder_structure = state.get("folder_structure", "")
    existing_codebase = state.get("codebase", {})

    # Start with existing codebase for context building
    codebase: dict[str, str] = {}
    logs: list[str] = []
    total = len(files_to_write)

    for idx, filepath in enumerate(files_to_write, 1):
        file_start = time.time()
        print(f"  {Fore.BLUE}[{idx}/{total}] Writing:{Style.RESET_ALL} {filepath}")
        logger.info(f"[{idx}/{total}] Starting file: {filepath}")

        # Build context of other files (always include descriptions)
        other_files = "\n".join(
            f"- {f}: {file_descriptions.get(f, 'N/A')}"
            for f in file_manifest
            if f != filepath
        )

        # Build context of previously written code (includes existing + just written)
        all_code = {**existing_codebase, **codebase}
        previous_code = build_previous_code_context(all_code)

        messages = [
            ("system", system_prompt),
            ("human", human_prompt_template.format(
                project_name=state.get("project_name", ""),
                project_goal=state.get("project_goal", ""),
                tech_stack=json.dumps(tech_stack, indent=2),
                folder_structure=folder_structure,
                current_file=filepath,
                file_description=file_descriptions.get(filepath, "No description provided"),
                other_files_context=other_files,
                previous_code=previous_code,
                extra_context=extra_context,
            )),
        ]

        print(f"         {Fore.BLUE}⏳ Generating code...{Style.RESET_ALL}")

        raw_content = invoke_llm_with_retry(
            llm, messages,
            max_retries=3,
            office_name=f"{office_name} ({filepath})",
        )

        # Validate output
        try:
            content = validate_engineering_output(raw_content, filepath)
        except ValueError as e:
            logger.warning(f"Validation failed for {filepath}: {e}. Retrying...")
            print(f"         {Fore.YELLOW}⚠️  Validation failed, retrying...{Style.RESET_ALL}")
            raw_content = invoke_llm_with_retry(
                llm, messages,
                max_retries=2,
                office_name=f"{office_name}-retry ({filepath})",
            )
            content = validate_engineering_output(raw_content, filepath)

        file_elapsed = time.time() - file_start
        codebase[filepath] = content
        _emit_code_artifact(filepath, content)
        tag = office_name.upper().replace(" ", "_")
        logs.append(f"[{tag}] Wrote {filepath} ({len(content)} chars, {file_elapsed:.1f}s)")
        logger.info(
            f"[{idx}/{total}] Completed {filepath} | "
            f"{len(content)} chars | {file_elapsed:.2f}s"
        )
        print(f"         {Fore.GREEN}✅ Done ({len(content)} chars, {file_elapsed:.1f}s){Style.RESET_ALL}")

        # Small delay between files to be kind to the API
        if idx < total:
            time.sleep(1)

    office_elapsed = time.time() - office_start
    print(f"\n  {Fore.GREEN}✅ All {total} files written in {office_elapsed:.1f}s!{Style.RESET_ALL}\n")
    logger.info(
        f"=== {office_name} — Exiting ({office_elapsed:.2f}s) | "
        f"files_written={total}, total_chars={sum(len(c) for c in codebase.values())} ==="
    )

    return {
        "codebase": codebase,
        "execution_logs": logs,
    }


def get_files_for_engineer(state: dict, engineer_id: str) -> list[str]:
    """Get the files this engineer should write, picking up orphaned files if needed.

    Args:
        state: Current OfficeState
        engineer_id: One of "frontend_engineer", "backend_engineer", "database_engineer"

    Returns:
        List of file paths to write.
    """
    CATEGORY_MAP = {
        "frontend_engineer": "frontend",
        "backend_engineer": "backend",
        "database_engineer": "database",
    }

    active_offices = state.get("active_offices", [])
    file_categories = state.get("file_categories", {})
    file_manifest = state.get("file_manifest", [])
    existing_codebase = state.get("codebase", {})

    my_category = CATEGORY_MAP.get(engineer_id, "")

    # Get files assigned to my category
    my_files = [f for f in file_manifest if file_categories.get(f) == my_category]

    # If I'm the first active coding engineer, pick up any unclaimed files
    active_engineers = [e for e in CATEGORY_MAP if e in active_offices]
    if active_engineers and engineer_id == active_engineers[0]:
        claimed_categories = {CATEGORY_MAP[e] for e in active_engineers}
        for f in file_manifest:
            cat = file_categories.get(f, "")
            if cat not in claimed_categories and f not in my_files:
                my_files.append(f)

    # Exclude files already written by previous offices
    my_files = [f for f in my_files if f not in existing_codebase]

    return my_files
