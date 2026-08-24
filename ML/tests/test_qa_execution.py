"""QA office runs real, offline checks over the generated code.

Drives the QA node directly with a codebase that holds one valid JavaScript
file and one file with a deliberate syntax error, then asserts the node emits
a tests/QA_RESULTS.md report that distinguishes a pass from a fail. When the
node binary is unavailable the same files must be reported as skipped instead.

Runs fully offline and deterministically via the mock provider (conftest).
"""

import shutil

from ML.offices.qa_engineer import qa_engineer_office

VALID_JS = "const answer = 40 + 2;\nfunction greet(name) {\n  return `hi ${name}`;\n}\n"
BROKEN_JS = "function broken( {\n  return 1\n"  # missing ) and unterminated block


def _state_with_two_js_files() -> dict:
    return {
        "project_goal": "counter page",
        "project_name": "qa-check-demo",
        "tech_stack": {"languages": ["JavaScript"]},
        "codebase": {
            "valid.js": VALID_JS,
            "broken.js": BROKEN_JS,
        },
    }


def _row_for(report: str, filename: str) -> str:
    """Return the Markdown table row that reports on ``filename``."""
    for line in report.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and f"`{filename}`" in stripped:
            return stripped
    return ""


def test_qa_execution_writes_report_and_distinguishes_pass_from_fail():
    result = qa_engineer_office(_state_with_two_js_files())

    codebase = result["codebase"]
    assert "tests/QA_RESULTS.md" in codebase, "QA must emit an execution report"

    report = codebase["tests/QA_RESULTS.md"]
    assert "# QA Execution Results" in report

    valid_row = _row_for(report, "valid.js")
    broken_row = _row_for(report, "broken.js")
    assert valid_row, "report must include a row for valid.js"
    assert broken_row, "report must include a row for broken.js"

    if shutil.which("node") is not None:
        # A real syntax parse ran: the good file passes, the broken one fails.
        assert "PASS" in valid_row
        assert "FAIL" in broken_row
        assert "Failed: 1" in report
        # The honest log line must not claim success while a check failed.
        joined_logs = " ".join(result["execution_logs"])
        assert "1 failed" in joined_logs
    else:
        # No node runtime available: both JS files are honestly skipped.
        assert "SKIP" in valid_row
        assert "SKIP" in broken_row
        assert "tool unavailable" in report


def test_qa_execution_report_counts_are_consistent():
    result = qa_engineer_office(_state_with_two_js_files())
    report = result["codebase"]["tests/QA_RESULTS.md"]

    def _count(label: str) -> int:
        for line in report.splitlines():
            if line.startswith(f"- {label}:"):
                return int(line.split(":", 1)[1].strip())
        raise AssertionError(f"missing count line for {label}")

    checked = _count("Checked")
    passed = _count("Passed")
    failed = _count("Failed")
    _skipped = _count("Skipped")

    # 'checked' is exactly the number of real checks that ran.
    assert checked == passed + failed
    # The two JS files under test are always accounted for.
    assert passed + failed + _skipped >= 2
