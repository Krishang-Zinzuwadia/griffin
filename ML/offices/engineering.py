"""
Engineering Office — Coder

Iterates through the file manifest one file at a time.
Each file gets its own LLM call to avoid rate limits and
to allow the LLM to reference previously written files.
"""

import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import ENGINEERING_SYSTEM, ENGINEERING_HUMAN


def engineering_office(state: OfficeState) -> dict:
    """Engineering node: write code for every file in the manifest."""

    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"  💻  ENGINEERING OFFICE — Coder")
    print(f"{'='*60}{Style.RESET_ALL}\n")

    llm = get_llm(temperature=0.4)
    file_manifest = state["file_manifest"]
    file_descriptions = state.get("file_descriptions", {})
    tech_stack = state.get("tech_stack", {})
    folder_structure = state.get("folder_structure", "")
    codebase: dict[str, str] = {}
    logs: list[str] = []

    total = len(file_manifest)

    for idx, filepath in enumerate(file_manifest, 1):
        print(f"  {Fore.BLUE}[{idx}/{total}] Writing:{Style.RESET_ALL} {filepath}")

        # Build context of other files
        other_files = "\n".join(
            f"- {f}: {file_descriptions.get(f, 'N/A')}"
            for f in file_manifest
            if f != filepath
        )

        # Build context of previously written code (truncated for token limits)
        previous_code_parts = []
        for prev_path, prev_content in codebase.items():
            # Truncate very long files to first 80 lines for context
            lines = prev_content.split("\n")
            if len(lines) > 80:
                snippet = "\n".join(lines[:80]) + f"\n... ({len(lines) - 80} more lines)"
            else:
                snippet = prev_content
            previous_code_parts.append(f"--- {prev_path} ---\n{snippet}")

        previous_code = "\n\n".join(previous_code_parts) if previous_code_parts else "(none yet)"

        messages = [
            ("system", ENGINEERING_SYSTEM),
            ("human", ENGINEERING_HUMAN.format(
                project_name=state["project_name"],
                project_goal=state["project_goal"],
                tech_stack=json.dumps(tech_stack, indent=2),
                folder_structure=folder_structure,
                current_file=filepath,
                file_description=file_descriptions.get(filepath, "No description provided"),
                other_files_context=other_files,
                previous_code=previous_code,
            )),
        ]

        print(f"         {Fore.BLUE}⏳ Generating code...{Style.RESET_ALL}")
        response = llm.invoke(messages)
        content = response.content.strip()

        # Strip markdown code fences if the LLM wrapped the output
        if content.startswith("```"):
            # Remove first line (```lang) and last line (```)
            lines = content.split("\n")
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            content = "\n".join(lines)

        codebase[filepath] = content
        logs.append(f"[ENGINEERING] Wrote {filepath} ({len(content)} chars)")
        print(f"         {Fore.GREEN}✅ Done ({len(content)} chars){Style.RESET_ALL}")

        # Small delay between files to be kind to the API
        if idx < total:
            time.sleep(1)

    print(f"\n  {Fore.GREEN}✅ All {total} files written!{Style.RESET_ALL}\n")

    return {
        "codebase": codebase,
        "execution_logs": logs,
    }
