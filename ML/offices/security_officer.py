"""
Security Officer Office — Code Review & Patches

Reviews the codebase for security vulnerabilities and returns
patched versions of files that need fixing.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import SECURITY_SYSTEM, SECURITY_HUMAN
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("security_officer")


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


def security_officer_office(state: OfficeState) -> dict:
    """Security Officer node: review and patch code for security issues."""

    logger.info("=== SECURITY OFFICER — Entering ===")
    office_start = time.time()

    print(f"\n{Fore.RED}{'='*60}")
    print(f"  🔒  SECURITY OFFICER — Code Review")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.RED}⏳ Reviewing for security issues...{Style.RESET_ALL}")

    llm = get_llm(temperature=0.2)  # Very deterministic for security
    codebase = state.get("codebase", {})
    codebase_summary = _build_codebase_summary(codebase)

    messages = [
        ("system", SECURITY_SYSTEM),
        ("human", SECURITY_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            tech_stack=json.dumps(state.get("tech_stack", {}), indent=2),
            codebase_summary=codebase_summary,
        )),
    ]

    result = invoke_and_parse_json(
        llm,
        messages,
        office_name="SECURITY_OFFICER",
    )

    patched_files = result.get("patched_files", {})
    security_notes = result.get("security_notes", [])
    elapsed = time.time() - office_start
    logs = []

    new_code = {}
    for path, content in patched_files.items():
        if content and len(content) > 10:
            new_code[path] = content
            logs.append(f"[SECURITY] Patched {path} ({len(content)} chars)")
            print(f"     {Fore.GREEN}🔧 Patched: {path}{Style.RESET_ALL}")

    if security_notes:
        print(f"\n  {Fore.GREEN}✅ Security Notes:{Style.RESET_ALL}")
        for note in security_notes:
            print(f"     {Fore.WHITE}• {note}{Style.RESET_ALL}")

    if not new_code:
        msg = "[SECURITY] No security patches needed."
        logs.append(msg)
        print(f"  {Fore.GREEN}✅ {msg}{Style.RESET_ALL}")

    logs.append(f"[SECURITY] Completed review. ({elapsed:.1f}s)")
    logger.info(f"=== SECURITY OFFICER — Exiting ({elapsed:.2f}s) ===")

    return {
        "codebase": new_code,
        "execution_logs": logs,
    }
