"""
Product Manager Office — Requirements / User Stories

Takes the project goal and creates actionable requirements
that guide the rest of the offices.
"""

import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import PM_SYSTEM, PM_HUMAN
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("product_manager")


def product_manager_office(state: OfficeState) -> dict:
    """Product Manager node: create requirements from the project goal."""

    logger.info("=== PRODUCT MANAGER — Entering ===")
    office_start = time.time()

    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"  📋  PRODUCT MANAGER — Requirements")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.MAGENTA}⏳ Defining requirements...{Style.RESET_ALL}")

    llm = get_llm(temperature=0.4)

    file_list = "\n".join(f"- {f}" for f in state.get("file_manifest", []))

    messages = [
        ("system", PM_SYSTEM),
        ("human", PM_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            file_manifest=file_list,
        )),
    ]

    result = invoke_and_parse_json(
        llm,
        messages,
        office_name="PRODUCT_MANAGER",
    )

    requirements = result.get("requirements", [])
    if not requirements:
        requirements = [f"The app must fulfill the goal: {state['project_goal']}"]

    elapsed = time.time() - office_start

    print(f"  {Fore.GREEN}✅ Requirements ({len(requirements)}):{Style.RESET_ALL}")
    for req in requirements:
        print(f"     {Fore.WHITE}• {req}{Style.RESET_ALL}")

    log_msg = f"[PRODUCT_MANAGER] Defined {len(requirements)} requirements. ({elapsed:.1f}s)"
    logger.info(f"=== PRODUCT MANAGER — Exiting ({elapsed:.2f}s) ===")

    return {
        "requirements": requirements,
        "execution_logs": [log_msg],
    }
