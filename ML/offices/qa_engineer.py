"""
QA Engineer Office - Test Writer & Checker

Reads the completed codebase and generates test files to verify key
functionality, then runs a real, offline, best-effort check over the
generated code plus the new test files and records honest results.

The checks are deliberately lightweight and offline:
  - JavaScript (.js/.mjs/.jsx/.cjs) is syntax-parsed with `node --check`
    when the `node` binary is available.
  - Python (.py) source is compiled with the built-in compile().
  - Every other file type has no offline runtime check and is skipped.

Nothing is ever installed and no network call is made. A failed check is
recorded in tests/QA_RESULTS.md, never raised, so the pipeline keeps moving.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import QA_SYSTEM, QA_HUMAN
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("qa_engineer")

# File extensions we can syntax-check with a real, offline tool.
_JS_EXTENSIONS = (".js", ".mjs", ".jsx", ".cjs")
_PY_EXTENSIONS = (".py",)

# Guard so a single check can never hang the whole pipeline.
_CHECK_TIMEOUT_S = 20

# Path of the report merged into the codebase for DevOps to write and push.
_REPORT_PATH = "tests/QA_RESULTS.md"

_STATUS_LABELS = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}


def _build_codebase_summary(codebase: dict, max_chars: int = 8000) -> str:
    """Build a truncated summary of the codebase for context."""
    summary_parts = []
    total = 0
    for path, content in codebase.items():
        header = f"\n--- {path} ---\n"
        if total + len(header) + len(content) > max_chars:
            remaining = max_chars - total - len(header) - 50
            if remaining > 100:
                summary_parts.append(header + content[:remaining] + "\n... (truncated)")
            break
        summary_parts.append(header + content)
        total += len(header) + len(content)
    return "".join(summary_parts) if summary_parts else "(empty codebase)"


# ═══════════════════════════════════════════════════════════════════
# REAL, OFFLINE, BEST-EFFORT EXECUTION CHECKS
# ═══════════════════════════════════════════════════════════════════

def _check_js_file(path: str, content: str) -> tuple[str, str]:
    """Syntax-check a JavaScript file with `node --check`.

    Returns (status, detail) where status is "passed", "failed" or
    "skipped". If the node binary is unavailable the file is skipped;
    nothing is ever installed.
    """
    if shutil.which("node") is None:
        return "skipped", "skipped (tool unavailable): node not found"

    ext = os.path.splitext(path)[1] or ".js"
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, f"qa_check{ext}")
            with open(tmp_path, "w", encoding="utf-8") as handle:
                handle.write(content)
            proc = subprocess.run(
                ["node", "--check", tmp_path],
                capture_output=True,
                text=True,
                timeout=_CHECK_TIMEOUT_S,
            )
        if proc.returncode == 0:
            return "passed", "node --check passed"
        stderr = (proc.stderr or proc.stdout or "").strip()
        # Map the throwaway temp path back to the logical file path so the
        # committed report is readable and deterministic across runs.
        stderr = stderr.replace(tmp_path, path).replace(
            tmp_path.replace("\\", "/"), path
        )
        return "failed", stderr or f"node --check exited with code {proc.returncode}"
    except subprocess.TimeoutExpired:
        return "failed", f"node --check timed out after {_CHECK_TIMEOUT_S}s"
    except OSError as exc:
        # e.g. node vanished between the which() probe and the run.
        return "skipped", f"skipped (tool unavailable): {exc}"


def _check_py_file(path: str, content: str) -> tuple[str, str]:
    """Syntax-check a Python file by compiling its source in memory."""
    try:
        compile(content, path, "exec")
        return "passed", "compile() passed"
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno else "unknown line"
        return "failed", f"SyntaxError: {exc.msg} ({location})"
    except (ValueError, TypeError) as exc:
        # e.g. source containing a null byte.
        return "failed", f"{type(exc).__name__}: {exc}"


def _run_offline_checks(files: dict) -> list[dict]:
    """Run a best-effort, offline check over each file.

    Never raises: any unexpected failure for a single file is recorded as
    a skipped result so the pipeline keeps moving. Files are processed in
    sorted order so the report is deterministic.
    """
    results: list[dict] = []
    for path in sorted(files):
        content = files.get(path) or ""
        lower = path.lower()
        try:
            if lower.endswith(_JS_EXTENSIONS):
                status, detail = _check_js_file(path, content)
            elif lower.endswith(_PY_EXTENSIONS):
                status, detail = _check_py_file(path, content)
            else:
                status, detail = "skipped", "skipped (no runtime check)"
        except Exception as exc:  # defensive: a check must never crash QA
            status, detail = "skipped", f"skipped (check error): {exc}"
        results.append({"path": path, "status": status, "detail": detail})
    return results


def _tally(results: list[dict]) -> dict:
    """Count results by status. 'checked' is the number of real checks run."""
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    return {
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "checked": passed + failed,
    }


def _sanitize_cell(text: str, max_len: int = 300) -> str:
    """Flatten a detail string so it is safe inside a Markdown table cell."""
    cell = " ".join((text or "").split())
    cell = cell.replace("|", "\\|")
    if len(cell) > max_len:
        cell = cell[: max_len - 3] + "..."
    return cell or "-"


def _build_qa_report(results: list[dict], counts: dict, project_name: str) -> str:
    """Render tests/QA_RESULTS.md from the check results."""
    lines = [
        "# QA Execution Results",
        "",
        f"Automated, offline best-effort checks for **{project_name or 'the project'}**.",
        "",
        "These are real checks run over the generated code and the new test files: "
        "`node --check` for JavaScript and Python `compile()` for Python. Other file "
        "types have no offline runtime check and are reported as skipped. No tools are "
        "installed and no network call is made.",
        "",
        "## Summary",
        "",
        f"- Checked: {counts['checked']}",
        f"- Passed: {counts['passed']}",
        f"- Failed: {counts['failed']}",
        f"- Skipped: {counts['skipped']}",
        "",
        "## Results",
        "",
        "| File | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for result in results:
        label = _STATUS_LABELS.get(result["status"], result["status"].upper())
        lines.append(
            f"| `{result['path']}` | {label} | {_sanitize_cell(result['detail'])} |"
        )
    if not results:
        lines.append("| _(no files to check)_ | - | - |")
    lines.append("")
    if counts["failed"]:
        lines.append(
            f"> {counts['failed']} check(s) failed. See the Detail column above."
        )
        lines.append("")
    return "\n".join(lines)


def _run_execution_step(
    codebase: dict,
    test_files: dict,
    project_name: str,
) -> tuple[str, list[str]]:
    """Run the offline checks and build the report.

    Returns (report_markdown, log_lines). Wrapped by the caller in a
    try/except, but also defends internally so a single bad file cannot
    take down the pipeline.
    """
    files_to_check = {**codebase, **test_files}
    results = _run_offline_checks(files_to_check)
    counts = _tally(results)
    report = _build_qa_report(results, counts, project_name)

    logs = [
        f"[QA_ENGINEER] Ran {counts['checked']} checks: "
        f"{counts['passed']} passed, {counts['failed']} failed, "
        f"{counts['skipped']} skipped"
    ]
    for result in results:
        if result["status"] == "failed":
            logs.append(
                f"[QA_ENGINEER] FAIL {result['path']}: "
                f"{_sanitize_cell(result['detail'], 200)}"
            )

    if counts["failed"]:
        print(
            f"  {Fore.RED}❌ {counts['failed']} check(s) failed "
            f"({counts['passed']} passed, {counts['skipped']} skipped).{Style.RESET_ALL}"
        )
    else:
        print(
            f"  {Fore.GREEN}✅ {counts['checked']} checks passed "
            f"({counts['skipped']} skipped).{Style.RESET_ALL}"
        )
    print(f"     {Fore.CYAN}📝 {_REPORT_PATH} ({len(report)} chars){Style.RESET_ALL}")
    return report, logs


def qa_engineer_office(state: OfficeState) -> dict:
    """QA Engineer node: write test files, then run real offline checks."""

    logger.info("=== QA ENGINEER - Entering ===")
    office_start = time.time()

    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"  🧪  QA ENGINEER - Test Writer & Checker")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.GREEN}⏳ Writing tests...{Style.RESET_ALL}")

    llm = get_llm(temperature=0.3)
    codebase = state.get("codebase", {})
    codebase_summary = _build_codebase_summary(codebase)

    messages = [
        ("system", QA_SYSTEM),
        ("human", QA_HUMAN.format(
            project_name=state["project_name"],
            project_goal=state["project_goal"],
            tech_stack=json.dumps(state.get("tech_stack", {}), indent=2),
            codebase_summary=codebase_summary,
        )),
    ]

    try:
        result = invoke_and_parse_json(
            llm,
            messages,
            office_name="QA_ENGINEER",
        )
    except RuntimeError as e:
        # Graceful degradation: if all retries fail, skip test generation
        # but still run the offline checks over the existing codebase so a
        # report is always produced.
        logger.warning(f"QA_ENGINEER could not produce valid output: {e}")
        print(f"  {Fore.YELLOW}⚠️  Test generation skipped - LLM output could not be parsed.{Style.RESET_ALL}")
        logs = [
            "[QA_ENGINEER] Test generation skipped: could not parse LLM response after retries."
        ]
        new_code: dict[str, str] = {}
        try:
            report, exec_logs = _run_execution_step(
                codebase, {}, state.get("project_name", "")
            )
            new_code[_REPORT_PATH] = report
            logs.extend(exec_logs)
        except Exception as exec_err:  # never crash the pipeline
            logger.warning(f"QA execution step failed: {exec_err}")
            logs.append(
                f"[QA_ENGINEER] Execution step error (recorded, not raised): {exec_err}"
            )
            new_code[_REPORT_PATH] = (
                "# QA Execution Results\n\n"
                f"The QA execution step could not complete: {exec_err}\n"
            )
        elapsed = time.time() - office_start
        logs.append(f"[QA_ENGINEER] Completed. ({elapsed:.1f}s)")
        return {
            "codebase": new_code,
            "execution_logs": logs,
        }

    test_files = result.get("test_files", {})
    logs: list[str] = []

    new_code: dict[str, str] = {}
    for path, content in test_files.items():
        if content and len(content) > 10:
            new_code[path] = content
            logs.append(f"[QA_ENGINEER] Wrote {path} ({len(content)} chars)")
            print(f"     {Fore.GREEN}✅ {path} ({len(content)} chars){Style.RESET_ALL}")

    if not new_code:
        msg = "[QA_ENGINEER] No test files generated."
        logs.append(msg)
        print(f"  {Fore.YELLOW}⏭️  {msg}{Style.RESET_ALL}")

    # ── Real, offline, best-effort execution over codebase + tests ──
    print(f"\n  {Fore.GREEN}⏳ Running offline checks...{Style.RESET_ALL}")
    try:
        report, exec_logs = _run_execution_step(
            codebase, new_code, state.get("project_name", "")
        )
        new_code[_REPORT_PATH] = report
        logs.extend(exec_logs)
    except Exception as exec_err:  # never crash the pipeline on a check
        logger.warning(f"QA execution step failed: {exec_err}")
        logs.append(
            f"[QA_ENGINEER] Execution step error (recorded, not raised): {exec_err}"
        )
        new_code.setdefault(
            _REPORT_PATH,
            "# QA Execution Results\n\n"
            f"The QA execution step could not complete: {exec_err}\n",
        )

    elapsed = time.time() - office_start
    logs.append(f"[QA_ENGINEER] Completed. ({elapsed:.1f}s)")
    logger.info(f"=== QA ENGINEER - Exiting ({elapsed:.2f}s) ===")

    return {
        "codebase": new_code,
        "execution_logs": logs,
    }
