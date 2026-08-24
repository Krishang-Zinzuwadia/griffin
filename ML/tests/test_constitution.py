"""Offline, deterministic tests for Agent Constitution enforcement.

Covers the static constitution scan (check_codebase / build_report) and the
secret masking helper (mask_secrets). No network, no LLM, no filesystem.
"""

from ML.constitution import check_codebase, build_report, mask_secrets


def test_check_codebase_flags_long_file():
    long_file = "\n".join(f"const line{i} = {i};" for i in range(650))
    violations = check_codebase({"src/big.js": long_file})

    big = [v for v in violations if v["rule"] == "max-file-lines"]
    assert big, "a file longer than 600 lines must be flagged"
    assert big[0]["file"] == "src/big.js"
    assert big[0]["severity"] == "medium"


def test_check_codebase_flags_any_type_in_ts():
    ts_code = "export function parse(input: any) {\n  return input;\n}\n"
    violations = check_codebase({"src/parse.ts": ts_code})

    any_hits = [v for v in violations if v["rule"] == "no-any-type"]
    assert any_hits, "a .ts file containing ': any' must be flagged"
    assert any_hits[0]["file"] == "src/parse.ts"
    assert any_hits[0]["line"] == 1
    assert any_hits[0]["severity"] == "medium"


def test_check_codebase_is_conservative_on_clean_code():
    clean_ts = "export function add(a: number, b: number): number {\n  return a + b;\n}\n"
    assert check_codebase({"src/add.ts": clean_ts}) == []


def test_build_report_contains_findings():
    violations = check_codebase({"src/state.ts": "let value: any = 1;\n"})
    report = build_report(violations)

    assert "# Constitution Compliance" in report
    assert "src/state.ts" in report
    assert "no-any-type" in report
    assert "Total violations: 1" in report


def test_build_report_when_clean():
    report = build_report([])
    assert "No constitution violations found." in report


def test_mask_secrets_redacts_github_token():
    secret = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    masked = mask_secrets(f"the token is {secret} and that is all")

    assert secret not in masked
    assert "***REDACTED***" in masked


def test_mask_secrets_redacts_password_assignment():
    masked = mask_secrets('password = "hunter2"')

    assert "hunter2" not in masked
    assert "***REDACTED***" in masked


def test_mask_secrets_leaves_ordinary_text_intact():
    text = "The counter starts at zero and increments on every click."
    assert mask_secrets(text) == text


def test_mask_secrets_never_crashes_on_odd_input():
    assert mask_secrets("") == ""
    assert isinstance(mask_secrets(None), str)
