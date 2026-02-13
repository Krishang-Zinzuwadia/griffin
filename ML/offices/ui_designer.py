"""
UI/UX Designer Office — Design System

Creates a cohesive design system (colors, typography, spacing)
that frontend engineers follow when writing CSS/HTML.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import UI_SYSTEM, UI_HUMAN
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("ui_designer")


def ui_designer_office(state: OfficeState) -> dict:
    """UI/UX Designer node: create a design system."""

    logger.info("=== UI/UX DESIGNER — Entering ===")
    office_start = time.time()

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"  🎨  UI/UX DESIGNER — Design System")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.CYAN}⏳ Creating design system...{Style.RESET_ALL}")

    llm = get_llm(temperature=0.6)  # Slightly more creative

    requirements = state.get("requirements", [])
    req_text = "\n".join(f"- {r}" for r in requirements) if requirements else "None specified"

    messages = [
        ("system", UI_SYSTEM),
        ("human", UI_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            requirements=req_text,
            tech_stack=json.dumps(state.get("tech_stack", {}), indent=2),
        )),
    ]

    result = invoke_and_parse_json(
        llm,
        messages,
        office_name="UI_DESIGNER",
    )

    design_system = result.get("design_system", {})
    elapsed = time.time() - office_start

    colors = design_system.get("colors", {})
    typography = design_system.get("typography", {})

    print(f"  {Fore.GREEN}✅ Design System:{Style.RESET_ALL}")
    if colors:
        print(f"     {Fore.WHITE}🎨 Colors:{Style.RESET_ALL}")
        for name, val in colors.items():
            print(f"        {name}: {val}")
    if typography:
        print(f"     {Fore.WHITE}🔤 Typography:{Style.RESET_ALL}")
        for name, val in typography.items():
            print(f"        {name}: {val}")
    style_notes = design_system.get("style_notes", "")
    if style_notes:
        print(f"     {Fore.WHITE}📝 Style: {style_notes}{Style.RESET_ALL}")

    log_msg = f"[UI_DESIGNER] Created design system. ({elapsed:.1f}s)"
    logger.info(f"=== UI/UX DESIGNER — Exiting ({elapsed:.2f}s) ===")

    return {
        "design_system": design_system,
        "execution_logs": [log_msg],
    }
