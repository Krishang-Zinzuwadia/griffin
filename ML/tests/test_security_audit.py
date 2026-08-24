"""The Security Officer produces a measured security_audit.md artifact.

Runs the office node directly with the mock provider (offline, deterministic).
The mock returns empty patched_files and a single security note, so the audit
content is driven by the deterministic static scan.
"""

from ML.offices.security_officer import security_officer_office


def _state(codebase: dict) -> dict:
    return {
        "project_name": "audit-demo",
        "project_goal": "demonstrate the security audit",
        "tech_stack": {"languages": ["JavaScript"]},
        "codebase": codebase,
    }


def test_scan_flags_eval_as_a_finding():
    result = security_officer_office(
        _state({"app.js": "const x = eval(userInput);\n"})
    )

    codebase = result["codebase"]
    assert "security_audit.md" in codebase

    report = codebase["security_audit.md"]
    # eval is surfaced as a concrete finding, tied to its file.
    assert "eval" in report
    assert "| app.js |" in report
    assert "high" in report
    # A real finding means we do NOT claim the code is clean.
    assert "Total findings: 0" not in report


def test_clean_codebase_reports_no_issues():
    clean_js = (
        "const button = document.getElementById('action');\n"
        "const output = document.getElementById('output');\n"
        "let count = 0;\n"
        "button.addEventListener('click', () => {\n"
        "  count += 1;\n"
        "  output.textContent = `Clicked ${count} times`;\n"
        "});\n"
    )
    result = security_officer_office(
        _state({"index.html": "<!DOCTYPE html>\n<title>Clean</title>\n", "script.js": clean_js})
    )

    report = result["codebase"]["security_audit.md"]
    assert "No blocking issues found" in report
    assert "Total findings: 0" in report


def test_multiple_patterns_are_counted():
    dangerous = (
        "el.innerHTML = userInput;\n"
        "const api_key = \"sk-secret-value\";\n"
        "fetch('http://insecure.example.com/data');\n"
    )
    result = security_officer_office(_state({"bad.js": dangerous}))
    report = result["codebase"]["security_audit.md"]

    assert ".innerHTML =" in report
    assert "hardcoded secret" in report
    assert "http://" in report
    assert "Total findings: 0" not in report
