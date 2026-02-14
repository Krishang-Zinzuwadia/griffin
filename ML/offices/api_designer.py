"""
API Designer Office — Endpoint Schemas

Designs REST/GraphQL endpoints that backend engineers implement
and frontend engineers consume.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import API_SYSTEM, API_HUMAN
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("api_designer")


def api_designer_office(state: OfficeState) -> dict:
    """API Designer node: design endpoint schemas."""

    logger.info("=== API DESIGNER — Entering ===")
    office_start = time.time()

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"  🔌  API DESIGNER — Endpoint Schemas")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.CYAN}⏳ Designing API endpoints...{Style.RESET_ALL}")

    llm = get_llm(temperature=0.3)

    requirements = state.get("requirements", [])
    req_text = "\n".join(f"- {r}" for r in requirements) if requirements else "None specified"
    file_list = "\n".join(f"- {f}" for f in state.get("file_manifest", []))

    messages = [
        ("system", API_SYSTEM),
        ("human", API_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            requirements=req_text,
            tech_stack=json.dumps(state.get("tech_stack", {}), indent=2),
            file_manifest=file_list,
        )),
    ]

    result = invoke_and_parse_json(
        llm,
        messages,
        office_name="API_DESIGNER",
    )

    api_schema = result.get("api_schema", {})
    endpoints = api_schema.get("endpoints", [])
    elapsed = time.time() - office_start

    print(f"  {Fore.GREEN}✅ API Schema:{Style.RESET_ALL}")
    base = api_schema.get("base_url", "/api")
    print(f"     {Fore.WHITE}Base URL: {base}{Style.RESET_ALL}")
    for ep in endpoints:
        method = ep.get("method", "GET")
        path = ep.get("path", "/")
        desc = ep.get("description", "")
        print(f"     {Fore.WHITE}{method:6s} {path}  —  {desc}{Style.RESET_ALL}")

    log_msg = f"[API_DESIGNER] Designed {len(endpoints)} endpoints. ({elapsed:.1f}s)"
    logger.info(f"=== API DESIGNER — Exiting ({elapsed:.2f}s) ===")

    return {
        "api_schema": api_schema,
        "execution_logs": [log_msg],
    }
