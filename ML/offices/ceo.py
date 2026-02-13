"""
CEO Office — Orchestrator / Planner

Takes the raw project goal and decomposes it into:
- A project name (slug)
- A file manifest (list of paths)
- Descriptions for each file
"""

import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import CEO_SYSTEM, CEO_HUMAN
from ..utils import invoke_and_parse_json, validate_ceo_response
from ..logger import get_logger

logger = get_logger("ceo")


def ceo_office(state: OfficeState) -> dict:
    """CEO node: decompose the project goal into a task manifest."""

    logger.info("=== CEO OFFICE — Entering ===")
    logger.info(f"Input state: project_goal='{state['project_goal'][:100]}'")
    office_start = time.time()

    print(f"\n{Fore.YELLOW}{'='*60}")
    print(f"  🏢  CEO OFFICE — Orchestrator / Planner")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"{Fore.CYAN}  Project Goal:{Style.RESET_ALL} {state['project_goal']}\n")

    llm = get_llm(temperature=0.3)

    messages = [
        ("system", CEO_SYSTEM),
        ("human", CEO_HUMAN.format(project_goal=state["project_goal"])),
    ]

    print(f"  {Fore.YELLOW}⏳ Thinking...{Style.RESET_ALL}")

    # ── LLM call with retry + JSON parse with retry ──────────────
    result = invoke_and_parse_json(
        llm, messages,
        max_retries=3,
        office_name="CEO",
    )

    # ── Validate & sanitize ──────────────────────────────────────
    result = validate_ceo_response(result)

    project_name = result["project_name"]
    file_manifest = result["file_manifest"]
    file_descriptions = result.get("file_descriptions", {})

    print(f"  {Fore.GREEN}✅ Project Name:{Style.RESET_ALL} {project_name}")
    print(f"  {Fore.GREEN}✅ Files planned:{Style.RESET_ALL} {len(file_manifest)}")
    for f in file_manifest:
        desc = file_descriptions.get(f, "")
        print(f"     📄 {f}  —  {desc}")
    print()

    office_elapsed = time.time() - office_start
    logger.info(
        f"=== CEO OFFICE — Exiting ({office_elapsed:.2f}s) | "
        f"project_name='{project_name}', files={len(file_manifest)} ==="
    )

    return {
        "project_name": project_name,
        "file_manifest": file_manifest,
        "file_descriptions": file_descriptions,
        "execution_logs": [
            f"[CEO] Planned project '{project_name}' with {len(file_manifest)} files. ({office_elapsed:.1f}s)"
        ],
    }
