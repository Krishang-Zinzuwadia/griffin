"""
Shared helper for the documentation and design offices.

Every office in the expanded catalog follows the Technical Writer pattern:
it calls the LLM with a system and human prompt, expects a JSON object with
a "doc_files" map, and merges those files into the shared codebase.

A RuntimeError from the LLM layer (a parse failure that survives all retries)
is caught here so a single office can never crash the pipeline. This mirrors
the graceful degradation used by qa_engineer and security_officer.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..utils import invoke_and_parse_json
from ..logger import get_logger


def _build_codebase_summary(codebase: dict, max_chars: int = 8000) -> str:
    """Build a truncated summary of the codebase for context."""
    summary_parts = []
    total = 0
    for path, content in codebase.items():
        header = f"\n--- {path} ---\n"
        if total + len(header) + len(content) > max_chars:
            remaining = max_chars - total - len(header) - 50
            if remaining > 100:
                summary_parts.append(header + content[:remaining] + "\n... (truncated)")
            break
        summary_parts.append(header + content)
        total += len(header) + len(content)
    return "".join(summary_parts) if summary_parts else "(empty codebase)"


def run_doc_office(
    state: OfficeState,
    system_prompt: str,
    human_prompt: str,
    office_name: str,
    label: str,
    emoji: str = "📄",
    temperature: float = 0.4,
) -> dict:
    """Run one documentation or design office and return a partial state update.

    Follows the Technical Writer pattern: call get_llm + invoke_and_parse_json
    with the given system and human prompts, then merge any returned doc_files
    into the codebase. On RuntimeError (LLM output could not be parsed after
    retries) the office skips gracefully and returns no files so the pipeline
    keeps moving.
    """
    logger = get_logger(office_name.lower())
    logger.info(f"=== {label} - Entering ===")
    office_start = time.time()

    print(f"\n{Fore.WHITE}{'='*60}")
    print(f"  {emoji}  {label.upper()}")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.WHITE}Working...{Style.RESET_ALL}")

    codebase = state.get("codebase", {})
    codebase_summary = _build_codebase_summary(codebase)

    messages = [
        ("system", system_prompt),
        ("human", human_prompt.format(
            project_name=state.get("project_name", ""),
            project_goal=state.get("project_goal", ""),
            tech_stack=json.dumps(state.get("tech_stack", {}), indent=2),
            codebase_summary=codebase_summary,
        )),
    ]

    logs: list[str] = []

    try:
        llm = get_llm(temperature=temperature)
        result = invoke_and_parse_json(
            llm,
            messages,
            office_name=office_name,
        )
    except RuntimeError as e:
        # Graceful degradation: a parse failure never crashes the pipeline.
        logger.warning(f"{office_name} could not produce valid output: {e}")
        print(
            f"  {Fore.YELLOW}Skipped: LLM output could not be parsed after "
            f"retries.{Style.RESET_ALL}"
        )
        logs.append(
            f"[{office_name}] Skipped: could not parse LLM response after retries."
        )
        elapsed = time.time() - office_start
        logs.append(f"[{office_name}] Completed. ({elapsed:.1f}s)")
        return {"codebase": {}, "execution_logs": logs}

    doc_files = result.get("doc_files", {}) or {}

    new_code: dict[str, str] = {}
    for path, content in doc_files.items():
        if isinstance(content, str) and len(content) > 10:
            new_code[path] = content
            logs.append(f"[{office_name}] Wrote {path} ({len(content)} chars)")
            print(f"     {Fore.GREEN}Wrote {path} ({len(content)} chars){Style.RESET_ALL}")

    if not new_code:
        msg = f"[{office_name}] No files generated."
        logs.append(msg)
        print(f"  {Fore.YELLOW}{msg}{Style.RESET_ALL}")

    elapsed = time.time() - office_start
    logs.append(f"[{office_name}] Completed. ({elapsed:.1f}s)")
    logger.info(f"=== {label} - Exiting ({elapsed:.2f}s) ===")

    return {"codebase": new_code, "execution_logs": logs}
