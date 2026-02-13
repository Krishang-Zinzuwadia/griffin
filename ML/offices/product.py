"""
Product Office — Architect

Takes the CEO's manifest and refines it:
- Selects the tech stack
- Defines folder structure
- Adds missing config/infra files
"""

import json
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import PRODUCT_SYSTEM, PRODUCT_HUMAN


def product_office(state: OfficeState) -> dict:
    """Product node: select tech stack and refine architecture."""

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
    response = llm.invoke(messages)
    raw = response.content.strip()

    # Clean potential markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    result = json.loads(raw)

    tech_stack = result.get("tech_stack", {})
    folder_structure = result.get("folder_structure", "")
    file_manifest = result.get("file_manifest", state["file_manifest"])
    file_descriptions = result.get("file_descriptions", state.get("file_descriptions", {}))

    print(f"  {Fore.GREEN}✅ Tech Stack:{Style.RESET_ALL}")
    for key, val in tech_stack.items():
        print(f"     🔧 {key}: {val}")
    print(f"\n  {Fore.GREEN}✅ Folder Structure:{Style.RESET_ALL}")
    for line in folder_structure.split("\n"):
        print(f"     {line}")
    print(f"\n  {Fore.GREEN}✅ Final file count:{Style.RESET_ALL} {len(file_manifest)}")
    print()

    return {
        "tech_stack": tech_stack,
        "folder_structure": folder_structure,
        "file_manifest": file_manifest,
        "file_descriptions": file_descriptions,
        "execution_logs": [
            f"[PRODUCT] Architected with stack: {json.dumps(tech_stack)}. "
            f"Final manifest: {len(file_manifest)} files."
        ],
    }
