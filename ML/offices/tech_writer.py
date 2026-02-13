"""
Technical Writer Office — Documentation

Reads the codebase and generates comprehensive documentation
files (README, API docs, setup guides).
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import WRITER_SYSTEM, WRITER_HUMAN
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("tech_writer")


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


def tech_writer_office(state: OfficeState) -> dict:
    """Technical Writer node: generate documentation files."""

    logger.info("=== TECH WRITER — Entering ===")
    office_start = time.time()

    print(f"\n{Fore.WHITE}{'='*60}")
    print(f"  📝  TECHNICAL WRITER — Documentation")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.WHITE}⏳ Writing documentation...{Style.RESET_ALL}")

    llm = get_llm(temperature=0.4)
    codebase = state.get("codebase", {})
    codebase_summary = _build_codebase_summary(codebase)
    file_list = "\n".join(f"- {f}" for f in state.get("file_manifest", []))

    messages = [
        ("system", WRITER_SYSTEM),
        ("human", WRITER_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            tech_stack=json.dumps(state.get("tech_stack", {}), indent=2),
            file_manifest=file_list,
            codebase_summary=codebase_summary,
        )),
    ]

    result = invoke_and_parse_json(
        llm,
        messages,
        office_name="TECH_WRITER",
    )

    doc_files = result.get("doc_files", {})
    elapsed = time.time() - office_start
    logs = []

    new_code = {}
    for path, content in doc_files.items():
        if content and len(content) > 10:
            new_code[path] = content
            logs.append(f"[TECH_WRITER] Wrote {path} ({len(content)} chars)")
            print(f"     {Fore.GREEN}✅ {path} ({len(content)} chars){Style.RESET_ALL}")

    if not new_code:
        msg = "[TECH_WRITER] No documentation files generated."
        logs.append(msg)
        print(f"  {Fore.YELLOW}⏭️  {msg}{Style.RESET_ALL}")

    logs.append(f"[TECH_WRITER] Completed. ({elapsed:.1f}s)")
    logger.info(f"=== TECH WRITER — Exiting ({elapsed:.2f}s) ===")

    return {
        "codebase": new_code,
        "execution_logs": logs,
    }
