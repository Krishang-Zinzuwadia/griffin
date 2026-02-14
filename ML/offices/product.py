"""
Product Office — Architect

Takes the CEO's manifest and refines it:
- Selects the tech stack
- Defines folder structure
- Adds missing config/infra files
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import PRODUCT_SYSTEM, PRODUCT_HUMAN
from ..utils import invoke_and_parse_json, validate_product_response
from ..logger import get_logger

logger = get_logger("product")


def product_office(state: OfficeState) -> dict:
    """Product node: select tech stack and refine architecture."""

    logger.info("=== PRODUCT OFFICE — Entering ===")
    logger.info(
        f"Input state: project_name='{state['project_name']}', "
        f"files={len(state['file_manifest'])}"
    )
    office_start = time.time()

    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"  🏗️  PRODUCT OFFICE — Architect")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    llm = get_llm(temperature=0.3)

    messages = [
        ("system", PRODUCT_SYSTEM),
        ("human", PRODUCT_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            file_manifest=json.dumps(state["file_manifest"], indent=2),
            file_descriptions=json.dumps(state.get("file_descriptions", {}), indent=2),
        )),
    ]

    print(f"  {Fore.MAGENTA}⏳ Designing architecture...{Style.RESET_ALL}")

    # ── LLM call with retry + JSON parse with retry ──────────────
    result = invoke_and_parse_json(
        llm, messages,
        max_retries=3,
        office_name="PRODUCT",
    )

    # ── Validate & sanitize ──────────────────────────────────────
    result = validate_product_response(result, fallback_manifest=state["file_manifest"])

    tech_stack = result["tech_stack"]
    folder_structure = result["folder_structure"]
    file_manifest = result["file_manifest"]
    file_descriptions = result.get("file_descriptions", state.get("file_descriptions", {}))

    print(f"  {Fore.GREEN}✅ Tech Stack:{Style.RESET_ALL}")
    for key, val in tech_stack.items():
        print(f"     🔧 {key}: {val}")
    print(f"\n  {Fore.GREEN}✅ Folder Structure:{Style.RESET_ALL}")
    for line in folder_structure.split("\n"):
        print(f"     {line}")
    print(f"\n  {Fore.GREEN}✅ Final file count:{Style.RESET_ALL} {len(file_manifest)}")
    print()

    office_elapsed = time.time() - office_start
    logger.info(
        f"=== PRODUCT OFFICE — Exiting ({office_elapsed:.2f}s) | "
        f"tech_stack={list(tech_stack.keys())}, files={len(file_manifest)} ==="
    )

    return {
        "tech_stack": tech_stack,
        "folder_structure": folder_structure,
        "file_manifest": file_manifest,
        "file_descriptions": file_descriptions,
        "execution_logs": [
            f"[PRODUCT] Architected with stack: {json.dumps(tech_stack)}. "
            f"Final manifest: {len(file_manifest)} files. ({office_elapsed:.1f}s)"
        ],
    }
