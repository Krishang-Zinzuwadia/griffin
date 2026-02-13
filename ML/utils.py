"""
Utilities — Shared helpers for the AI Office Chain.

Provides:
- Robust JSON parsing from LLM output (handles markdown fences, noisy text)
- LLM invocation with retry + exponential backoff (rate limit protection)
- Response validators for each office
"""

import re
import json
import time
import logging
from colorama import Fore, Style

logger = logging.getLogger("office_chain")


# ═══════════════════════════════════════════════════════════════════
# JSON PARSING RESILIENCE
# ═══════════════════════════════════════════════════════════════════

def parse_json_response(raw: str) -> dict:
    """Extract and parse JSON from an LLM response.

    Handles:
    - Clean JSON
    - JSON wrapped in ```json ... ``` fences
    - JSON buried in surrounding text/explanation
    """
    text = raw.strip()

    # ── Attempt 1: Strip markdown fences and parse directly ──────
    cleaned = _strip_markdown_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # ── Attempt 2: Regex extract the outermost JSON object ───────
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # ── Attempt 3: Try to find JSON between code fences ──────────
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # ── All parsing attempts failed ──────────────────────────────
    logger.error(f"Failed to parse JSON from LLM response:\n{text[:500]}")
    raise ValueError(
        f"Could not extract valid JSON from LLM response. "
        f"Raw output (first 300 chars): {text[:300]}"
    )


def _strip_markdown_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences."""
    lines = text.split("\n")

    # Remove opening fence (```json or ```)
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]

    # Remove closing fence
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from raw code output (for Engineering)."""
    content = text.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```lang)
        lines = lines[1:]
        # Remove last line if it's a closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)
    return content


# ═══════════════════════════════════════════════════════════════════
# LLM INVOCATION WITH RETRY + EXPONENTIAL BACKOFF
# ═══════════════════════════════════════════════════════════════════

def invoke_llm_with_retry(
    llm,
    messages: list,
    max_retries: int = 3,
    base_delay: float = 2.0,
    office_name: str = "Office",
) -> str:
    """Invoke an LLM with retry logic and exponential backoff.

    Catches rate-limit (429) and transient errors, retries with
    increasing delays: 2s → 4s → 8s.

    Returns the raw response content string.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            call_start = time.time()
            response = llm.invoke(messages)
            call_latency = time.time() - call_start
            content = response.content.strip()

            # Log timing and response size
            logger.info(
                f"[{office_name}] LLM call succeeded in {call_latency:.2f}s "
                f"| response: {len(content)} chars"
            )
            return content

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            # Check if it's a rate limit or quota error
            is_rate_limit = any(keyword in error_str for keyword in [
                "429", "resource_exhausted", "rate limit",
                "quota", "too many requests", "resourceexhausted",
            ])

            if is_rate_limit and attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))  # 2s, 4s, 8s
                print(
                    f"  {Fore.YELLOW}⚠️  [{office_name}] Rate limited "
                    f"(attempt {attempt}/{max_retries}). "
                    f"Retrying in {delay:.0f}s...{Style.RESET_ALL}"
                )
                logger.warning(
                    f"[{office_name}] Rate limit hit on attempt {attempt}. "
                    f"Retrying in {delay}s. Error: {e}"
                )
                time.sleep(delay)

            elif not is_rate_limit and attempt < max_retries:
                # Transient error — retry with shorter delay
                delay = base_delay
                print(
                    f"  {Fore.YELLOW}⚠️  [{office_name}] Error "
                    f"(attempt {attempt}/{max_retries}): {str(e)[:100]}. "
                    f"Retrying in {delay:.0f}s...{Style.RESET_ALL}"
                )
                logger.warning(
                    f"[{office_name}] Transient error on attempt {attempt}. "
                    f"Retrying in {delay}s. Error: {e}"
                )
                time.sleep(delay)

            else:
                # Final attempt failed
                logger.error(
                    f"[{office_name}] All {max_retries} attempts failed. "
                    f"Last error: {e}"
                )

    raise RuntimeError(
        f"[{office_name}] LLM invocation failed after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


# ═══════════════════════════════════════════════════════════════════
# LLM CALL + JSON PARSE (combined retry for both)
# ═══════════════════════════════════════════════════════════════════

def invoke_and_parse_json(
    llm,
    messages: list,
    max_retries: int = 3,
    base_delay: float = 2.0,
    office_name: str = "Office",
) -> dict:
    """Invoke LLM and parse JSON response, with retry on both
    rate-limit errors AND JSON parse failures.

    On JSON parse failure, the LLM is re-invoked (different attempt
    may produce valid JSON).
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            parse_start = time.time()
            raw = invoke_llm_with_retry(
                llm, messages,
                max_retries=2,  # inner retry for rate limits
                base_delay=base_delay,
                office_name=office_name,
            )
            result = parse_json_response(raw)
            parse_latency = time.time() - parse_start
            logger.info(
                f"[{office_name}] LLM + JSON parse completed in {parse_latency:.2f}s"
            )
            return result

        except ValueError as e:
            # JSON parse failed — retry the entire LLM call
            last_error = e
            if attempt < max_retries:
                print(
                    f"  {Fore.YELLOW}⚠️  [{office_name}] JSON parse failed "
                    f"(attempt {attempt}/{max_retries}). Re-invoking LLM...{Style.RESET_ALL}"
                )
                logger.warning(
                    f"[{office_name}] JSON parse failed on attempt {attempt}: {e}"
                )
                time.sleep(1)
            else:
                logger.error(
                    f"[{office_name}] JSON parse failed after {max_retries} attempts."
                )

        except RuntimeError as e:
            # LLM invocation itself failed after retries
            raise

    raise RuntimeError(
        f"[{office_name}] Failed to get valid JSON after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


# ═══════════════════════════════════════════════════════════════════
# RESPONSE VALIDATORS
# ═══════════════════════════════════════════════════════════════════

def validate_ceo_response(result: dict) -> dict:
    """Validate and sanitize CEO office output."""
    # project_name: must exist and be kebab-case
    name = result.get("project_name", "")
    if not name or not isinstance(name, str):
        raise ValueError("CEO response missing 'project_name'")
    # Sanitize to kebab-case
    name = re.sub(r'[^a-z0-9\-]', '-', name.lower())
    name = re.sub(r'-+', '-', name).strip('-')
    if not name:
        name = "untitled-project"
    result["project_name"] = name

    # file_manifest: must be non-empty list of strings
    manifest = result.get("file_manifest", [])
    if not isinstance(manifest, list) or len(manifest) == 0:
        raise ValueError("CEO response has empty or missing 'file_manifest'")
    result["file_manifest"] = [str(f) for f in manifest]

    # file_descriptions: optional but should be a dict
    descs = result.get("file_descriptions", {})
    if not isinstance(descs, dict):
        result["file_descriptions"] = {}

    return result


def validate_product_response(result: dict, fallback_manifest: list) -> dict:
    """Validate and sanitize Product office output."""
    # tech_stack: must have at least 'languages' key
    stack = result.get("tech_stack", {})
    if not isinstance(stack, dict) or "languages" not in stack:
        logger.warning("Product response missing tech_stack.languages, using default")
        if not isinstance(stack, dict):
            stack = {}
        stack.setdefault("languages", ["Unknown"])
    result["tech_stack"] = stack

    # folder_structure: should be non-empty string
    folder = result.get("folder_structure", "")
    if not isinstance(folder, str) or not folder.strip():
        result["folder_structure"] = "(not provided)"

    # file_manifest: use updated or fall back to previous
    manifest = result.get("file_manifest", fallback_manifest)
    if not isinstance(manifest, list) or len(manifest) == 0:
        manifest = fallback_manifest
    result["file_manifest"] = [str(f) for f in manifest]

    # file_descriptions
    descs = result.get("file_descriptions", {})
    if not isinstance(descs, dict):
        result["file_descriptions"] = {}

    return result


def validate_engineering_output(content: str, filepath: str) -> str:
    """Validate Engineering office code output."""
    if not content or not content.strip():
        raise ValueError(f"Engineering produced empty output for {filepath}")

    # Check if the output is ONLY markdown fences with no content
    stripped = strip_code_fences(content)
    if not stripped.strip():
        raise ValueError(
            f"Engineering produced only markdown fences for {filepath}"
        )

    return stripped


# ═══════════════════════════════════════════════════════════════════
# CONTEXT WINDOW MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

MAX_CONTEXT_CHARS = 10_000  # ~2.5K tokens


def build_previous_code_context(
    codebase: dict[str, str],
    max_chars: int = MAX_CONTEXT_CHARS,
) -> str:
    """Build a context string of previously written code.

    If the total exceeds max_chars, only include the most recent files,
    truncating older ones to their first 30 lines.
    """
    if not codebase:
        return "(none yet)"

    parts = []
    total_chars = 0
    items = list(codebase.items())

    # Process in reverse (most recent first)
    for path, content in reversed(items):
        lines = content.split("\n")

        # Recent files: include up to 80 lines
        if total_chars < max_chars * 0.6:
            if len(lines) > 80:
                snippet = "\n".join(lines[:80]) + f"\n... ({len(lines) - 80} more lines)"
            else:
                snippet = content
        else:
            # Older files: heavily truncate to 30 lines
            if len(lines) > 30:
                snippet = "\n".join(lines[:30]) + f"\n... ({len(lines) - 30} more lines)"
            else:
                snippet = content

        entry = f"--- {path} ---\n{snippet}"
        total_chars += len(entry)

        # Hard cap: stop adding if we've exceeded the limit
        if total_chars > max_chars and parts:
            remaining = len(items) - len(parts)
            parts.append(f"... ({remaining} earlier files omitted for brevity)")
            break

        parts.append(entry)

    # Reverse back to chronological order
    parts.reverse()
    return "\n\n".join(parts)
