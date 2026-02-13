"""
CEO Office — Orchestrator / Planner

Takes the raw project goal and decomposes it into:
- A project name (slug)
- A file manifest (list of paths)
- Descriptions for each file
"""

import json
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import CEO_SYSTEM, CEO_HUMAN


def ceo_office(state: OfficeState) -> dict:
    """CEO node: decompose the project goal into a task manifest."""

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
    response = llm.invoke(messages)
    raw = response.content.strip()

    # Clean potential markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    result = json.loads(raw)

    project_name = result["project_name"]
    file_manifest = result["file_manifest"]
    file_descriptions = result.get("file_descriptions", {})

    print(f"  {Fore.GREEN}✅ Project Name:{Style.RESET_ALL} {project_name}")
    print(f"  {Fore.GREEN}✅ Files planned:{Style.RESET_ALL} {len(file_manifest)}")
    for f in file_manifest:
        desc = file_descriptions.get(f, "")
        print(f"     📄 {f}  —  {desc}")
    print()

    return {
        "project_name": project_name,
        "file_manifest": file_manifest,
        "file_descriptions": file_descriptions,
        "execution_logs": [
            f"[CEO] Planned project '{project_name}' with {len(file_manifest)} files."
        ],
    }
