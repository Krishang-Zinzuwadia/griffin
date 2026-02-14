"""
QA Engineer Office — Test Writer

Reads the completed codebase and generates test files
to verify key functionality.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import QA_SYSTEM, QA_HUMAN
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("qa_engineer")


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


def qa_engineer_office(state: OfficeState) -> dict:
    """QA Engineer node: write test files for the codebase."""

    logger.info("=== QA ENGINEER — Entering ===")
    office_start = time.time()

    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"  🧪  QA ENGINEER — Test Writer")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.GREEN}⏳ Writing tests...{Style.RESET_ALL}")

    llm = get_llm(temperature=0.3)
    codebase = state.get("codebase", {})
    codebase_summary = _build_codebase_summary(codebase)

    messages = [
        ("system", QA_SYSTEM),
        ("human", QA_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            tech_stack=json.dumps(state.get("tech_stack", {}), indent=2),
            codebase_summary=codebase_summary,
        )),
    ]

    try:
        result = invoke_and_parse_json(
            llm,
            messages,
            office_name="QA_ENGINEER",
        )
    except RuntimeError as e:
        # Graceful degradation: if all retries fail, skip tests
        logger.warning(f"QA_ENGINEER could not produce valid output: {e}")
        print(f"  {Fore.YELLOW}⚠️  QA skipped — LLM output could not be parsed.{Style.RESET_ALL}")
        elapsed = time.time() - office_start
        return {
            "execution_logs": [
                f"[QA_ENGINEER] Skipped: could not parse LLM response after retries. ({elapsed:.1f}s)"
            ],
        }

    test_files = result.get("test_files", {})
    elapsed = time.time() - office_start
    logs = []

    new_code = {}
    for path, content in test_files.items():
        if content and len(content) > 10:
            new_code[path] = content
            logs.append(f"[QA_ENGINEER] Wrote {path} ({len(content)} chars)")
            print(f"     {Fore.GREEN}✅ {path} ({len(content)} chars){Style.RESET_ALL}")

    if not new_code:
        msg = "[QA_ENGINEER] No test files generated."
        logs.append(msg)
        print(f"  {Fore.YELLOW}⏭️  {msg}{Style.RESET_ALL}")

    logs.append(f"[QA_ENGINEER] Completed. ({elapsed:.1f}s)")
    logger.info(f"=== QA ENGINEER — Exiting ({elapsed:.2f}s) ===")

    return {
        "codebase": new_code,
        "execution_logs": logs,
    }
