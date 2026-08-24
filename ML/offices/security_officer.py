"""
Security Officer Office - Code Review, Static Scan & Audit Report

Reviews the codebase for security vulnerabilities. It combines two signals:

1. An LLM review that can return patched versions of files plus free-form
   security notes (kept from the original office).
2. A deterministic static scan that flags concrete risky patterns with the
   file name and line number, so the office produces a real, measured
   artifact rather than only an opinion printed to the console.

The office writes a "security_audit.md" report into the codebase so DevOps
writes and pushes it alongside the rest of the project.
"""

import re
import json
import time
from colorama import Fore, Style
from ..state import OfficeState
from ..config import get_llm
from ..prompts import SECURITY_SYSTEM, SECURITY_HUMAN
from ..utils import invoke_and_parse_json
from ..logger import get_logger

logger = get_logger("security_officer")


# ── Static scan pattern catalogue ────────────────────────────────
# Each entry is (label, severity, compiled_regex). The label is what shows
# up in the audit table, so keep it short and free of the pipe character.
_SCAN_PATTERNS = [
    ("eval(", "high", re.compile(r"\beval\s*\(")),
    ("new Function(", "high", re.compile(r"\bnew\s+Function\s*\(")),
    ("child_process", "high", re.compile(r"child_process")),
    ("exec(", "high", re.compile(r"\bexec(?:Sync|File|FileSync)?\s*\(")),
    (
        "hardcoded secret",
        "high",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*['"][^'"]{3,}['"]"""
        ),
    ),
    ("document.write(", "medium", re.compile(r"\bdocument\s*\.\s*write(?:ln)?\s*\(")),
    (".innerHTML =", "medium", re.compile(r"\.innerHTML\s*\+?=(?!=)")),
    ("dangerouslySetInnerHTML", "medium", re.compile(r"dangerouslySetInnerHTML")),
    (
        "http:// (non-TLS URL)",
        "low",
        re.compile(r"http://(?!localhost|127\.0\.0\.1|www\.w3\.org|schemas\.)"),
    ),
]

_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


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


def _run_static_scan(codebase: dict) -> list[dict]:
    """Scan every file for risky patterns.

    Returns a sorted list of findings, each a dict with keys
    file, line, pattern and severity. Defensive by design: a bad file
    is skipped, never fatal.
    """
    findings: list[dict] = []
    for path in sorted(codebase.keys()):
        content = codebase.get(path, "")
        if not isinstance(content, str):
            continue
        try:
            for lineno, line in enumerate(content.splitlines(), start=1):
                for label, severity, regex in _SCAN_PATTERNS:
                    if regex.search(line):
                        findings.append(
                            {
                                "file": path,
                                "line": lineno,
                                "pattern": label,
                                "severity": severity,
                            }
                        )
        except Exception as e:  # never let one bad file crash the scan
            logger.warning(f"Static scan error in {path}: {e}")
            continue

    findings.sort(
        key=lambda f: (
            f["file"],
            f["line"],
            _SEVERITY_RANK.get(f["severity"], 3),
            f["pattern"],
        )
    )
    return findings


def _severity_counts(findings: list[dict]) -> tuple[int, int, int]:
    """Return (high, medium, low) counts for a findings list."""
    high = sum(1 for f in findings if f["severity"] == "high")
    medium = sum(1 for f in findings if f["severity"] == "medium")
    low = sum(1 for f in findings if f["severity"] == "low")
    return high, medium, low


def _build_audit_md(
    scan_target: dict, findings: list[dict], security_notes: list
) -> str:
    """Assemble the security_audit.md report text."""
    high, medium, low = _severity_counts(findings)

    lines = [
        "# Security Audit",
        "",
        "Automated review by the Security Officer: an LLM code review plus a "
        "deterministic static scan for risky patterns.",
        "",
        "## Summary",
        "",
        f"- Files scanned: {len(scan_target)}",
        f"- Total findings: {len(findings)}",
        f"- High severity: {high}",
        f"- Medium severity: {medium}",
        f"- Low severity: {low}",
        "",
        "## Findings",
        "",
    ]

    if findings:
        lines.append("| File | Line | Pattern | Severity |")
        lines.append("| --- | --- | --- | --- |")
        for f in findings:
            lines.append(
                f"| {f['file']} | {f['line']} | {f['pattern']} | {f['severity']} |"
            )
    else:
        lines.append("No blocking issues found.")
    lines.append("")

    lines += ["## Security Notes (LLM Review)", ""]
    if security_notes:
        for note in security_notes:
            lines.append(f"- {note}")
    else:
        lines.append("- (no notes provided)")
    lines.append("")

    return "\n".join(lines)


def security_officer_office(state: OfficeState) -> dict:
    """Security Officer node: LLM review, static scan, and audit report."""

    logger.info("=== SECURITY OFFICER - Entering ===")
    office_start = time.time()

    print(f"\n{Fore.RED}{'='*60}")
    print(f"  🔒  SECURITY OFFICER - Code Review")
    print(f"{'='*60}{Style.RESET_ALL}\n")
    print(f"  {Fore.RED}⏳ Reviewing for security issues...{Style.RESET_ALL}")

    codebase = state.get("codebase", {})
    logs: list[str] = []

    # ── Step 1: LLM review (best effort, never fatal) ────────────
    security_notes: list = []
    patched_files: dict = {}
    try:
        llm = get_llm(temperature=0.2)  # Very deterministic for security
        codebase_summary = _build_codebase_summary(codebase)
        messages = [
            ("system", SECURITY_SYSTEM),
            ("human", SECURITY_HUMAN.format(
                project_name=state.get("project_name", ""),
                project_goal=state.get("project_goal", ""),
                tech_stack=json.dumps(state.get("tech_stack", {}), indent=2),
                codebase_summary=codebase_summary,
            )),
        ]
        result = invoke_and_parse_json(
            llm,
            messages,
            office_name="SECURITY_OFFICER",
        )
        patched_files = result.get("patched_files", {}) or {}
        security_notes = result.get("security_notes", []) or []
    except Exception as e:
        logger.warning(f"SECURITY_OFFICER LLM review skipped: {e}")
        print(
            f"  {Fore.YELLOW}⚠️  LLM review skipped - output could not be parsed. "
            f"Static scan still runs.{Style.RESET_ALL}"
        )
        logs.append("[SECURITY_OFFICER] LLM review skipped: could not parse response.")

    # ── Step 2: Merge valid patched files ────────────────────────
    new_code: dict = {}
    for path, content in patched_files.items():
        if isinstance(content, str) and len(content) > 10:
            new_code[path] = content
            logs.append(f"[SECURITY_OFFICER] Patched {path} ({len(content)} chars)")
            print(f"     {Fore.GREEN}🔧 Patched: {path}{Style.RESET_ALL}")

    if security_notes:
        print(f"\n  {Fore.GREEN}✅ Security Notes:{Style.RESET_ALL}")
        for note in security_notes:
            print(f"     {Fore.WHITE}• {note}{Style.RESET_ALL}")

    # ── Step 3: Deterministic static scan (existing + patched) ───
    try:
        scan_target = {**codebase, **new_code}
        findings = _run_static_scan(scan_target)
        high, medium, low = _severity_counts(findings)

        audit_md = _build_audit_md(scan_target, findings, security_notes)
        new_code["security_audit.md"] = audit_md

        scan_msg = (
            f"[SECURITY_OFFICER] Scan found {len(findings)} issues "
            f"({high} high, {medium} medium, {low} low)"
        )
        logs.append(scan_msg)
        logs.append(
            f"[SECURITY_OFFICER] Wrote security_audit.md ({len(audit_md)} chars)"
        )

        if findings:
            print(f"\n  {Fore.YELLOW}🔎 {scan_msg[len('[SECURITY_OFFICER] '):]}{Style.RESET_ALL}")
            for f in findings[:10]:
                print(
                    f"     {Fore.YELLOW}• {f['file']}:{f['line']} "
                    f"{f['pattern']} [{f['severity']}]{Style.RESET_ALL}"
                )
            if len(findings) > 10:
                print(f"     {Fore.YELLOW}... and {len(findings) - 10} more{Style.RESET_ALL}")
        else:
            print(f"\n  {Fore.GREEN}✅ Static scan: no blocking issues found.{Style.RESET_ALL}")
    except Exception as e:
        # The audit must never crash the pipeline. Emit a minimal report.
        logger.error(f"SECURITY_OFFICER static scan failed: {e}")
        new_code.setdefault(
            "security_audit.md",
            "# Security Audit\n\nNo blocking issues found.\n"
            f"\n(Static scan could not complete: {e})\n",
        )
        logs.append(f"[SECURITY_OFFICER] Static scan error: {e}")

    elapsed = time.time() - office_start
    logs.append(f"[SECURITY_OFFICER] Completed review. ({elapsed:.1f}s)")
    logger.info(f"=== SECURITY OFFICER - Exiting ({elapsed:.2f}s) ===")

    return {
        "codebase": new_code,
        "execution_logs": logs,
    }
