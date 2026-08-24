"""
CEO Office — Orchestrator / Planner

Takes the user's project goal and:
1. Names the project
2. Selects which offices should be activated
3. Creates the initial file manifest
"""

import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import CEO_SYSTEM, CEO_HUMAN, OFFICE_CATALOG
from ..utils import invoke_and_parse_json, validate_ceo_response
from ..logger import get_logger

logger = get_logger("ceo")

# Valid office IDs for validation
VALID_OFFICES = {
    "product_manager", "architect", "ui_designer", "api_designer",
    "frontend_engineer", "backend_engineer", "database_engineer",
    "qa_engineer", "security_officer", "tech_writer",
    # Expanded catalog offices (each ships at least one artifact file)
    "legal_compliance", "ux_research", "design_systems", "localization",
    "performance", "accessibility", "marketing", "data_science",
    "ai_ml", "three_d", "game_dev", "mobile", "iot_embedded",
}


def ceo_office(state: OfficeState) -> dict:
    """CEO node: plan the project and select active offices."""

    logger.info("=== CEO OFFICE — Entering ===")
    logger.info(f"Input state: project_goal='{state['project_goal']}'")
    office_start = time.time()

    print(f"\n{Fore.YELLOW}{'='*60}")
    print(f"  🏢  CEO OFFICE — Orchestrator / Planner")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.WHITE}Project Goal:{Style.RESET_ALL} {state['project_goal']}\n")

    llm = get_llm(temperature=0.4)

    messages = [
        ("system", CEO_SYSTEM.format(office_catalog=OFFICE_CATALOG)),
        ("human", CEO_HUMAN.format(project_goal=state["project_goal"])),
    ]

    result = invoke_and_parse_json(
        llm,
        messages,
        office_name="CEO",
    )

    # ── Validate & sanitize ──────────────────────────────────────
    result = validate_ceo_response(result)

    # Validate and sanitize active_offices
    raw_offices = result.get("active_offices", ["architect", "frontend_engineer"])
    active_offices = [o for o in raw_offices if o in VALID_OFFICES]

    # Enforce: architect is always included
    if "architect" not in active_offices:
        active_offices.insert(0, "architect")

    # Enforce: at least one coding engineer
    coding_engineers = {"frontend_engineer", "backend_engineer", "database_engineer"}
    if not coding_engineers.intersection(active_offices):
        active_offices.append("frontend_engineer")

    result["active_offices"] = active_offices

    # ── Output ──────────────────────────────────────────────────
    elapsed = time.time() - office_start

    print(f"  {Fore.GREEN}✅ Project Name:{Style.RESET_ALL} {result['project_name']}")
    print(f"  {Fore.GREEN}✅ Files planned:{Style.RESET_ALL} {len(result['file_manifest'])}")
    for f in result["file_manifest"]:
        desc = result.get("file_descriptions", {}).get(f, "")
        print(f"     {Fore.WHITE}📄 {f}{Style.RESET_ALL}  —  {desc}")

    print(f"\n  {Fore.GREEN}✅ Active Offices ({len(active_offices)}):{Style.RESET_ALL}")
    for office in active_offices:
        print(f"     {Fore.CYAN}🏢 {office}{Style.RESET_ALL}")

    log_msg = (
        f"[CEO] Planned project '{result['project_name']}' with {len(result['file_manifest'])} files, "
        f"activated {len(active_offices)} offices: {active_offices}. ({elapsed:.1f}s)"
    )
    logger.info(f"=== CEO OFFICE — Exiting ({elapsed:.2f}s) ===")
    logger.info(f"Active offices: {active_offices}")

    return {
        "project_name": result["project_name"],
        "active_offices": active_offices,
        "file_manifest": result["file_manifest"],
        "file_descriptions": result.get("file_descriptions", {}),
        "execution_logs": [log_msg],
    }
