"""
Mock LLM provider for offline, deterministic pipeline runs.

Enabled with LLM_PROVIDER=mock. Requires no API key and makes no network calls.
The mock inspects each prompt and returns a canned, schema-correct response for the
calling office, so the full office chain runs start to finish for tests and demos.

The returned object mimics the small slice of the LangChain message interface the
pipeline relies on: a ``content`` string and a ``usage_metadata`` dict.
"""

import re


class MockResponse:
    """Minimal stand in for a LangChain chat message."""

    def __init__(self, content: str, input_tokens: int, output_tokens: int):
        self.content = content
        self.usage_metadata = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        self.response_metadata: dict = {}


def _messages_to_text(messages) -> str:
    """Flatten the LangChain style message list into a single string."""
    parts = []
    for message in messages:
        if isinstance(message, (tuple, list)) and len(message) >= 2:
            parts.append(str(message[1]))
        elif hasattr(message, "content"):
            parts.append(str(message.content))
        else:
            parts.append(str(message))
    return "\n".join(parts)


def _slugify(text: str, fallback: str = "demo-app") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = "-".join(slug.split("-")[:5])
    return slug or fallback


def _project_slug(text: str) -> str:
    match = re.search(r"Project Idea:\s*(.+)", text)
    goal = match.group(1).strip() if match else "demo app"
    return _slugify(goal)


# ── Canned JSON responses (schema matches ML/prompts.py) ──────────────

def _ceo_json(text: str) -> str:
    slug = _project_slug(text)
    return (
        '{'
        f'"project_name": "{slug}", '
        '"active_offices": ["product_manager", "architect", "ui_designer", '
        '"frontend_engineer", "qa_engineer", "security_officer", "tech_writer"], '
        '"file_manifest": ["index.html", "styles.css", "script.js"], '
        '"file_descriptions": {'
        '"index.html": "Main page markup", '
        '"styles.css": "Page styling", '
        '"script.js": "Client side behaviour"}'
        '}'
    )


_PM_JSON = (
    '{"requirements": ['
    '"The app must render a single page with a clear heading and controls", '
    '"Users must be able to interact with the primary control and see the result update", '
    '"The app must be responsive on mobile and desktop", '
    '"The app must work without any backend service"]}'
)

_ARCH_JSON = (
    '{'
    '"tech_stack": {"languages": ["HTML", "CSS", "JavaScript"], '
    '"frameworks": [], "libraries": [], "tools": []}, '
    '"folder_structure": "project/\\n  index.html\\n  styles.css\\n  script.js", '
    '"file_manifest": ["index.html", "styles.css", "script.js"], '
    '"file_descriptions": {"index.html": "Main page markup", '
    '"styles.css": "Page styling", "script.js": "Client side behaviour"}, '
    '"file_categories": {"index.html": "frontend", "styles.css": "frontend", '
    '"script.js": "frontend"}'
    '}'
)

_UI_JSON = (
    '{"design_system": {'
    '"colors": {"primary": "#3B82F6", "background": "#0F172A", "text": "#F8FAFC"}, '
    '"typography": {"font_family": "Inter, system-ui, sans-serif", "base_size": "16px"}, '
    '"spacing": {"unit": "8px", "border_radius": "8px"}, '
    '"style_notes": "Clean modern dark theme"}}'
)

_API_JSON = (
    '{"api_schema": {"base_url": "/api/v1", "endpoints": ['
    '{"method": "GET", "path": "/health", "description": "Health check", '
    '"request": {}, "response": {"status": "ok"}}]}}'
)

_QA_JSON = (
    '{"test_files": {"tests/smoke.test.js": '
    '"test(\'app boots\', () => { expect(1 + 1).toBe(2); });\\n"}}'
)

_SECURITY_JSON = (
    '{"patched_files": {}, "security_notes": ["No blocking issues found in offline review"]}'
)

_WRITER_JSON = (
    '{"doc_files": {"README.md": '
    '"# Demo App\\n\\nGenerated offline by the mock provider for testing.\\n\\n'
    '## Run\\n\\nOpen index.html in a browser.\\n"}}'
)


def _code_for(text: str) -> str:
    """Return minimal valid file content for a coding office request."""
    match = re.search(r"FILE TO WRITE:\s*(.+)", text)
    path = match.group(1).strip() if match else "file.txt"
    lower = path.lower()
    if lower.endswith((".html", ".htm")):
        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            "  <meta charset=\"UTF-8\">\n"
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            "  <title>Demo App</title>\n"
            "  <link rel=\"stylesheet\" href=\"styles.css\">\n"
            "</head>\n<body>\n"
            "  <main>\n    <h1>Demo App</h1>\n    <button id=\"action\">Click</button>\n"
            "    <p id=\"output\">Ready</p>\n  </main>\n"
            "  <script src=\"script.js\"></script>\n</body>\n</html>\n"
        )
    if lower.endswith(".css"):
        return (
            ":root { --bg: #0f172a; --fg: #f8fafc; }\n"
            "* { box-sizing: border-box; }\n"
            "body { margin: 0; font-family: system-ui, sans-serif; "
            "background: var(--bg); color: var(--fg); }\n"
            "main { max-width: 640px; margin: 4rem auto; padding: 1rem; text-align: center; }\n"
            "button { padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; }\n"
        )
    if lower.endswith((".js", ".mjs")):
        return (
            "const button = document.getElementById('action');\n"
            "const output = document.getElementById('output');\n"
            "let count = 0;\n"
            "if (button) {\n"
            "  button.addEventListener('click', () => {\n"
            "    count += 1;\n"
            "    if (output) output.textContent = `Clicked ${count} times`;\n"
            "  });\n"
            "}\n"
        )
    if lower.endswith(".json"):
        return "{\n  \"name\": \"demo-app\"\n}\n"
    return f"// {path} generated offline by the mock provider\n"


def _route(text: str) -> str:
    # Coding offices ask for raw file content, not JSON.
    if "raw file content" in text or "FILE TO WRITE:" in text:
        return _code_for(text)
    if "You are the CEO" in text:
        return _ceo_json(text)
    if "You are the Product Manager" in text:
        return _PM_JSON
    if "You are the Software Architect" in text:
        return _ARCH_JSON
    if "You are the UI/UX Designer" in text:
        return _UI_JSON
    if "You are the API Designer" in text:
        return _API_JSON
    if "You are a Senior QA Engineer" in text:
        return _QA_JSON
    if "You are the Security Officer" in text:
        return _SECURITY_JSON
    if "You are a Technical Writer" in text:
        return _WRITER_JSON
    # Unknown prompt: return an empty object so JSON parsers do not crash.
    return "{}"


class MockLLM:
    """Drop in replacement for the chat model used by the office chain."""

    def __init__(self, temperature: float = 0.4):
        self.temperature = temperature

    def invoke(self, messages):
        text = _messages_to_text(messages)
        content = _route(text)
        input_tokens = max(1, len(text) // 4)
        output_tokens = max(1, len(content) // 4)
        return MockResponse(content, input_tokens, output_tokens)
