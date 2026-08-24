"""The Cost Optimizer reports REAL accumulated token usage.

Its "actual usage" panel used to read state["token_usage"], which nothing
populates mid run, so it always reported zero. These tests run real mock LLM
calls (both directly and through the first few offices) and assert the Cost
Optimizer node now reports the non zero usage that the global tracker in
ML.utils actually accumulated, sourced from get_token_usage_summary().

Offline and deterministic: conftest.py forces LLM_PROVIDER=mock and
GRIFFIN_OFFLINE=1 before any ML module is imported, so nothing touches the
network and every run is repeatable.
"""

from ML.config import get_llm
from ML.offices.ceo import ceo_office
from ML.offices.product_manager import product_manager_office
from ML.offices.architect import architect_office
from ML.offices.cost_optimizer import cost_optimizer_office
from ML.utils import (
    reset_token_usage_log,
    get_token_usage_summary,
    invoke_and_parse_json,
)


def _blank_state(goal: str) -> dict:
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


def _run_first_offices(goal: str) -> dict:
    """Run ceo -> product_manager -> architect, merging their partial state.

    Mirrors the real pipeline order so the global tracker holds real, non zero
    usage for those offices before the Cost Optimizer runs.
    """
    state = _blank_state(goal)
    for office in (ceo_office, product_manager_office, architect_office):
        state.update(office(state))
    return state


def test_tracker_records_real_usage_for_first_offices():
    """Sanity: running the first offices leaves non zero usage in the tracker."""
    reset_token_usage_log()
    _run_first_offices("make a simple counter page")

    summary = get_token_usage_summary()
    assert summary["total_calls"] > 0
    assert summary["total_input_tokens"] > 0
    assert summary["total_output_tokens"] > 0


def test_cost_optimizer_reports_tracker_usage_after_offices():
    """The optimizer reports the REAL accumulated usage, not the empty ledger."""
    reset_token_usage_log()

    # Real mock LLM calls happen here (one per office), recorded by the tracker.
    state = _run_first_offices("make a simple counter page")

    # The tracker accumulated real usage before the optimizer runs.
    before = get_token_usage_summary()
    assert before["total_calls"] > 0

    # The office ledger is still empty mid run; the old code read this and so
    # always reported zero.
    assert not state["token_usage"]

    result = cost_optimizer_office(state)

    # The optimizer output reflects the live tracker usage, not the ledger.
    actual = result["token_usage"]["cost_report"]["actual_usage"]
    assert actual["total_calls"] == before["total_calls"]
    assert actual["total_input_tokens"] == before["total_input_tokens"]
    assert actual["total_output_tokens"] == before["total_output_tokens"]
    assert actual["total_cost_usd"] == before["total_cost_usd"]

    # The panel is now genuinely non zero.
    assert actual["total_calls"] > 0
    assert actual["total_input_tokens"] > 0
    assert actual["total_output_tokens"] > 0

    # An honest execution_logs line carries the real accumulated usage.
    usage_lines = [
        line for line in result["execution_logs"] if "Real usage so far" in line
    ]
    assert usage_lines, f"expected a real-usage log line, got {result['execution_logs']}"
    assert f"{before['total_calls']} calls" in usage_lines[0]
    assert "cost=$" in usage_lines[0]


def test_cost_optimizer_reads_tracker_not_state_ledger():
    """Reading is from get_token_usage_summary(), independent of state ledger."""
    reset_token_usage_log()
    llm = get_llm()

    # A couple of real mock LLM calls, recorded by the global tracker.
    for _ in range(2):
        invoke_and_parse_json(
            llm,
            [("system", "ping"), ("human", "return an empty json object")],
            office_name="TEST",
        )

    summary = get_token_usage_summary()
    assert summary["total_calls"] == 2
    assert summary["total_input_tokens"] > 0

    # A minimal state whose ledger is empty, exactly as during a real run.
    state = {
        "project_name": "demo",
        "project_goal": "make a simple counter page",
        "active_offices": ["architect", "frontend_engineer"],
        "file_manifest": ["index.html"],
        "file_categories": {"index.html": "frontend"},
        "token_usage": {},
    }

    result = cost_optimizer_office(state)
    actual = result["token_usage"]["cost_report"]["actual_usage"]

    # Reported usage matches the live tracker, proving it is not read from the
    # empty state["token_usage"] ledger.
    assert actual["total_calls"] == summary["total_calls"] == 2
    assert actual["total_input_tokens"] == summary["total_input_tokens"]
    assert actual["total_output_tokens"] == summary["total_output_tokens"]
    assert actual["total_calls"] > 0
    assert actual["total_input_tokens"] > 0
