"""
Architect Office — System Design

Selects tech stack, designs folder structure, refines file manifest,
and categorizes each file for the appropriate coding engineer.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import ARCHITECT_SYSTEM, ARCHITECT_HUMAN
from ..utils import invoke_and_parse_json, validate_product_response
from ..logger import get_logger

logger = get_logger("architect")


def architect_office(state: OfficeState) -> dict:
    """Architect node: design tech stack, structure, and file categorization."""

    logger.info("=== ARCHITECT OFFICE — Entering ===")
    office_start = time.time()

    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"  🏗️  ARCHITECT OFFICE — System Design")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.MAGENTA}⏳ Designing architecture...{Style.RESET_ALL}")

    llm = get_llm(temperature=0.4)

    file_list = "\n".join(f"- {f}" for f in state.get("file_manifest", []))
    desc_list = "\n".join(
        f"- {k}: {v}" for k, v in state.get("file_descriptions", {}).items()
    )
    requirements = state.get("requirements", [])
    req_text = "\n".join(f"- {r}" for r in requirements) if requirements else "None specified"
    active_offices = state.get("active_offices", [])

    messages = [
        ("system", ARCHITECT_SYSTEM),
        ("human", ARCHITECT_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            active_offices=json.dumps(active_offices),
            requirements=req_text,
            file_manifest=file_list,
            file_descriptions=desc_list,
        )),
    ]

    result = invoke_and_parse_json(
        llm,
        messages,
        office_name="ARCHITECT",
    )

    # ── Validate ────────────────────────────────────────────────
    # Ensure fallback_manifest is passed correctly
    result = validate_product_response(result, fallback_manifest=state.get("file_manifest", []))

    tech_stack = result.get("tech_stack", {})
    folder_structure = result.get("folder_structure", "")
    file_manifest = result.get("file_manifest", state.get("file_manifest", []))
    file_descriptions = result.get("file_descriptions", state.get("file_descriptions", {}))
    file_categories = result.get("file_categories", {})

    # Ensure every file has a category — default to "frontend"
    for f in file_manifest:
        if f not in file_categories:
            file_categories[f] = "frontend"

    elapsed = time.time() - office_start

    print(f"  {Fore.GREEN}✅ Tech Stack:{Style.RESET_ALL}")
    for key, val in tech_stack.items():
        print(f"     {Fore.WHITE}🔧 {key}: {val}{Style.RESET_ALL}")

    print(f"\n  {Fore.GREEN}✅ Folder Structure:{Style.RESET_ALL}")
    for line in folder_structure.split("\n"):
        print(f"     {Fore.WHITE}{line}{Style.RESET_ALL}")

    print(f"\n  {Fore.GREEN}✅ File Categorization:{Style.RESET_ALL}")
    for f, cat in file_categories.items():
        print(f"     {Fore.WHITE}{f} → {cat}{Style.RESET_ALL}")

    print(f"\n  {Fore.GREEN}✅ Final file count:{Style.RESET_ALL} {len(file_manifest)}")

    log_msg = (
        f"[ARCHITECT] Architected with stack: {json.dumps(tech_stack)}. "
        f"Final manifest: {len(file_manifest)} files. ({elapsed:.1f}s)"
    )
    logger.info(f"=== ARCHITECT OFFICE — Exiting ({elapsed:.2f}s) ===")

    return {
        "tech_stack": tech_stack,
        "folder_structure": folder_structure,
        "file_manifest": file_manifest,
        "file_descriptions": file_descriptions,
        "file_categories": file_categories,
        "execution_logs": [log_msg],
    }
