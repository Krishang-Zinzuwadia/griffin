"""
Engineering Office — Coder

Iterates through the file manifest one file at a time.
Each file gets its own LLM call to avoid rate limits and
to allow the LLM to reference previously written files.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import ENGINEERING_SYSTEM, ENGINEERING_HUMAN
from ..utils import (
    invoke_llm_with_retry,
    validate_engineering_output,
    build_previous_code_context,
)
from ..logger import get_logger

logger = get_logger("engineering")


def engineering_office(state: OfficeState) -> dict:
    """Engineering node: write code for every file in the manifest."""

    logger.info("=== ENGINEERING OFFICE — Entering ===")
    logger.info(
        f"Input state: project_name='{state['project_name']}', "
        f"files_to_write={len(state['file_manifest'])}, "
        f"tech_stack={list(state.get('tech_stack', {}).keys())}"
    )
    office_start = time.time()

    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"  💻  ENGINEERING OFFICE — Coder")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    llm = get_llm(temperature=0.4)
    file_manifest = state["file_manifest"]
    file_descriptions = state.get("file_descriptions", {})
    tech_stack = state.get("tech_stack", {})
    folder_structure = state.get("folder_structure", "")
    codebase: dict[str, str] = {}
    logs: list[str] = []

    total = len(file_manifest)

    for idx, filepath in enumerate(file_manifest, 1):
        file_start = time.time()
        print(f"  {Fore.BLUE}[{idx}/{total}] Writing:{Style.RESET_ALL} {filepath}")
        logger.info(f"[{idx}/{total}] Starting file: {filepath}")

        # Build context of other files (always include descriptions)
        other_files = "\n".join(
            f"- {f}: {file_descriptions.get(f, 'N/A')}"
            for f in file_manifest
            if f != filepath
        )

        # Build context of previously written code (managed for token limits)
        previous_code = build_previous_code_context(codebase)

        messages = [
            ("system", ENGINEERING_SYSTEM),
            ("human", ENGINEERING_HUMAN.format(
                project_name=state["project_name"],
                project_goal=state["project_goal"],
                tech_stack=json.dumps(tech_stack, indent=2),
                folder_structure=folder_structure,
                current_file=filepath,
                file_description=file_descriptions.get(filepath, "No description provided"),
                other_files_context=other_files,
                previous_code=previous_code,
            )),
        ]

        print(f"         {Fore.BLUE}⏳ Generating code...{Style.RESET_ALL}")

        # ── LLM call with retry (rate limit protection) ──────────
        raw_content = invoke_llm_with_retry(
            llm, messages,
            max_retries=3,
            office_name=f"ENGINEERING ({filepath})",
        )

        # ── Validate output ──────────────────────────────────────
        try:
            content = validate_engineering_output(raw_content, filepath)
        except ValueError as e:
            # If validation fails, retry once with a nudge
            logger.warning(f"Validation failed for {filepath}: {e}. Retrying...")
            print(f"         {Fore.YELLOW}⚠️  Validation failed, retrying...{Style.RESET_ALL}")
            raw_content = invoke_llm_with_retry(
                llm, messages,
                max_retries=2,
                office_name=f"ENGINEERING-retry ({filepath})",
            )
            content = validate_engineering_output(raw_content, filepath)

        file_elapsed = time.time() - file_start
        codebase[filepath] = content
        logs.append(f"[ENGINEERING] Wrote {filepath} ({len(content)} chars, {file_elapsed:.1f}s)")
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
        f"=== ENGINEERING OFFICE — Exiting ({office_elapsed:.2f}s) | "
        f"files_written={total}, total_chars={sum(len(c) for c in codebase.values())} ==="
    )

    return {
        "codebase": codebase,
        "execution_logs": logs,
    }
