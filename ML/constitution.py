"""
Agent Constitution - Compliance checks and secret masking.

Enforces the global rules from the Agent Constitution (REQUIREMENTS.md
section 8) on generated code, and redacts credential-like values before they
are written into any artifact.

Two responsibilities:

1. check_codebase / build_report - a deterministic, dependency-free static
   scan that flags constitution violations (oversized files, TypeScript
   ``any`` types, absolute imports, non kebab-case file names) and renders a
   CONSTITUTION.md compliance report.
2. mask_secrets - redact tokens and credential-like values from arbitrary
   text so they never leak into generated reports.

Everything here is defensive: a single malformed file, an odd key, or an odd
input value must never crash the pipeline. The scan is intentionally
conservative to avoid false positives, using simple line scans and no
external tools.
"""

import os
import re

# ── Severity ranking (for stable ordering) ───────────────────────
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

# ── Extension groups ─────────────────────────────────────────────
_TS_EXTS = (".ts", ".tsx")
_JSTS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs")
_NAME_CHECK_EXTS = (".ts", ".tsx", ".js", ".jsx")

_MAX_LINES = 600

# ── Pattern catalogue ────────────────────────────────────────────
# TypeScript ``any`` in its three documented shapes: ": any", "as any"
# and "<any>". Word boundaries keep "anyOf" or "anything" from matching.
_ANY_PATTERNS = (
    re.compile(r":\s*any\b"),
    re.compile(r"\bas\s+any\b"),
    re.compile(r"<\s*any\s*>"),
)

# Import (or re-export / require / dynamic import) whose target path starts
# with "/". The leading-slash requirement keeps bare package names and
# relative "./" or "../" imports from matching.
_ABS_IMPORT_RE = re.compile(
    r"""(?:\bfrom\s*|\brequire\s*\(\s*|\bimport\s*\(\s*|\bimport\s+)['"](/[^'"]*)['"]"""
)

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_COMMENT_PREFIXES = ("//", "*", "/*")


def _basename(path: str) -> str:
    """Return the final path component, tolerant of both slash styles."""
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def _split_ext(name: str) -> tuple:
    """Split a basename into (stem, ext); ext is lowercase and keeps the dot."""
    stem, ext = os.path.splitext(name)
    return stem, ext.lower()


def _check_file(path: str, content: str) -> list:
    """Run every constitution rule over a single file. Never raises."""
    violations = []
    name = _basename(path)
    _stem, ext = _split_ext(name)
    lines = content.splitlines()

    # Rule: max 600 lines per file.
    if len(lines) > _MAX_LINES:
        violations.append({
            "file": path,
            "line": 0,
            "rule": "max-file-lines",
            "severity": "medium",
            "detail": f"{len(lines)} lines (max {_MAX_LINES})",
        })

    # Rule: no ``any`` types in TypeScript.
    if ext in _TS_EXTS:
        for lineno, line in enumerate(lines, start=1):
            if line.lstrip().startswith(_COMMENT_PREFIXES):
                continue
            for pattern in _ANY_PATTERNS:
                match = pattern.search(line)
                if match:
                    violations.append({
                        "file": path,
                        "line": lineno,
                        "rule": "no-any-type",
                        "severity": "medium",
                        "detail": f"uses '{match.group(0).strip()}'",
                    })
                    break

    # Rule: relative imports only (no import path starting with "/").
    if ext in _JSTS_EXTS:
        for lineno, line in enumerate(lines, start=1):
            if line.lstrip().startswith(_COMMENT_PREFIXES):
                continue
            match = _ABS_IMPORT_RE.search(line)
            if match:
                violations.append({
                    "file": path,
                    "line": lineno,
                    "rule": "no-absolute-import",
                    "severity": "low",
                    "detail": f"absolute import '{match.group(1)}'",
                })

    # Rule: kebab-case names for component/module files. Skips dotfiles and
    # config/test/type-declaration files (basenames with more than one dot).
    if ext in _NAME_CHECK_EXTS and not name.startswith(".") and name.count(".") == 1:
        stem = name[: -len(ext)]
        if not _KEBAB_RE.match(stem):
            violations.append({
                "file": path,
                "line": 0,
                "rule": "kebab-case-filename",
                "severity": "low",
                "detail": f"'{name}' is not kebab-case",
            })

    return violations


def check_codebase(codebase: dict) -> list:
    """Flag Agent Constitution violations across a codebase.

    Args:
        codebase: mapping of file path -> file content.

    Returns:
        A deterministically ordered list of violation dicts, each with the
        keys file, line, rule, severity and detail. Conservative by design to
        avoid false positives, and defensive so one bad file never crashes
        the scan.
    """
    violations = []
    if not isinstance(codebase, dict):
        return violations

    for path in sorted(codebase.keys()):
        content = codebase.get(path, "")
        if not isinstance(path, str) or not isinstance(content, str):
            continue
        try:
            violations.extend(_check_file(path, content))
        except Exception:
            # A single malformed file must never break the scan.
            continue

    violations.sort(key=lambda v: (
        v["file"],
        v["line"],
        _SEVERITY_RANK.get(v["severity"], 3),
        v["rule"],
    ))
    return violations


def severity_counts(violations: list) -> tuple:
    """Return (high, medium, low) counts for a violations list."""
    high = sum(1 for v in violations if v.get("severity") == "high")
    medium = sum(1 for v in violations if v.get("severity") == "medium")
    low = sum(1 for v in violations if v.get("severity") == "low")
    return high, medium, low


def _md_cell(value) -> str:
    """Make a value safe to drop into a Markdown table cell."""
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "/").strip()


def build_report(violations: list) -> str:
    """Render a CONSTITUTION.md compliance report.

    Args:
        violations: the output of check_codebase.

    Returns:
        Markdown text with a summary count and a findings table, or a clear
        "No constitution violations found." line when the list is empty.
    """
    violations = violations or []
    high, medium, low = severity_counts(violations)
    files_affected = len({v.get("file") for v in violations})

    lines = [
        "# Constitution Compliance",
        "",
        "Automated check against the Agent Constitution "
        "(REQUIREMENTS.md section 8).",
        "",
        "## Summary",
        "",
        f"- Files with violations: {files_affected}",
        f"- Total violations: {len(violations)}",
        f"- High severity: {high}",
        f"- Medium severity: {medium}",
        f"- Low severity: {low}",
        "",
        "## Violations",
        "",
    ]

    if violations:
        lines.append("| File | Line | Rule | Severity | Detail |")
        lines.append("| --- | --- | --- | --- | --- |")
        for v in violations:
            lines.append(
                f"| {_md_cell(v.get('file'))} "
                f"| {_md_cell(v.get('line'))} "
                f"| {_md_cell(v.get('rule'))} "
                f"| {_md_cell(v.get('severity'))} "
                f"| {_md_cell(v.get('detail'))} |"
            )
    else:
        lines.append("No constitution violations found.")
    lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# SECRET MASKING
# ═══════════════════════════════════════════════════════════════════

_REDACTED = "***REDACTED***"

# GitHub personal access and OAuth tokens: ghp_, gho_, ghu_, ghs_, ghr_,
# plus the fine-grained github_pat_ form.
_GITHUB_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"
)
# OpenAI / OpenRouter style keys (e.g. sk-or-v1-...).
_SK_TOKEN_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")
# Google API keys.
_GOOGLE_TOKEN_RE = re.compile(r"\bAIza[A-Za-z0-9_-]{16,}")
# Credentials embedded in a URL: https://<userinfo>@host (e.g. a token used
# as the git remote username).
_URL_CRED_RE = re.compile(r"(https?://)[^/\s:@]+(?::[^/\s@]+)?@")
# Any value assigned to a sensitive key (token/secret/password/api_key),
# with an optional surrounding quote on either side.
_KV_SECRET_RE = re.compile(
    r"""(?i)(\b(?:api[_-]?key|secret|password|token)\b['"]?\s*[:=]\s*)(['"]?)([^\s'";,)]{3,})"""
)
# Generic long token (Vercel style): a 24+ character alphanumeric run that
# mixes letters and digits. The digit requirement keeps ordinary prose safe.
_GENERIC_TOKEN_RE = re.compile(
    r"\b(?=[A-Za-z0-9]*[0-9])(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{24,}\b"
)


def mask_secrets(text) -> str:
    """Redact credential-like values from arbitrary text.

    Redacts GitHub tokens, OpenAI/OpenRouter and Google API keys, credentials
    embedded in URLs, generic long tokens (Vercel style), and any value
    assigned to a key named token/secret/password/api_key. Each is replaced
    with "***REDACTED***". Safe on arbitrary input and never raises.
    """
    if not isinstance(text, str):
        return "" if text is None else str(text)
    try:
        text = _GITHUB_TOKEN_RE.sub(_REDACTED, text)
        text = _SK_TOKEN_RE.sub(_REDACTED, text)
        text = _GOOGLE_TOKEN_RE.sub(_REDACTED, text)
        text = _URL_CRED_RE.sub(lambda m: m.group(1) + _REDACTED + "@", text)
        text = _KV_SECRET_RE.sub(lambda m: m.group(1) + m.group(2) + _REDACTED, text)
        text = _GENERIC_TOKEN_RE.sub(_REDACTED, text)
    except Exception:
        return text
    return text
