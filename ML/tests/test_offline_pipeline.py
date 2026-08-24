"""Full offline pipeline smoke test.

Runs the entire office chain with the mock provider and asserts it produces a real
local project, with no network access and no API keys.
"""

from ML.graph import build_graph
from ML.config import SANDBOX_DIR, OFFLINE, LLM_PROVIDER
from ML.utils import reset_token_usage_log, get_token_usage_summary


def _initial_state(goal: str) -> dict:
    return {
        "project_goal": goal,
        "project_name": "",
        "active_offices": [],
        "file_manifest": [],
        "file_descriptions": {},
        "requirements": [],
        "tech_stack": {},
        "folder_structure": "",
        "file_categories": {},
        "design_system": {},
        "api_schema": {},
        "codebase": {},
        "execution_logs": [],
        "github_url": "",
        "token_usage": {},
    }


def test_environment_is_offline():
    assert LLM_PROVIDER == "mock"
    assert OFFLINE is True


def test_offline_pipeline_generates_project():
    reset_token_usage_log()
    final = build_graph().invoke(_initial_state("make a simple counter page"))

    # Real project name, not the service fallback.
    assert final["project_name"]
    assert final["project_name"] != "Generated Project"

    # Code was actually produced.
    codebase = final["codebase"]
    assert codebase, "codebase should not be empty"
    assert "index.html" in codebase
    assert final["github_url"] == ""  # offline, no push

    # Files landed on disk with a report.
    project_dir = SANDBOX_DIR / final["project_name"]
    assert (project_dir / "index.html").exists()
    assert (project_dir / "REPORT.md").exists()

    # Token accounting ran for every office call.
    summary = get_token_usage_summary()
    assert summary["total_calls"] >= 5
    assert summary["total_output_tokens"] > 0
