"""Pipeline runner: spawn the ML CLI and mirror the ml-service websocket contract.

This module runs ``python -m ML.main <prompt>`` from the repository root and turns
its stdout into the exact same websocket message types the Bun ml-service emits
(progress, terminal, office_status, token_usage, cost_update, file, complete,
error). While streaming it also persists projects, offices, and messages to the
database, masking any token or secret values before they are stored.

The runner is deliberately thread based rather than asyncio based so it behaves
the same on Windows and Linux under the FastAPI test client. The caller runs
``PipelineRunner.run`` in a worker thread and drains the messages it emits.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from .models import Message, Office, Project

# ── Contract constants (kept identical to backend/ml-service/index.ts) ──────────
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
EVENT_PREFIX = "@@GRIFFIN_EVENT "
TOKEN_RE = re.compile(
    r"\[([^\]]+)\] Token usage: in=(\d+), out=(\d+), cost=\$([0-9.]+), latency=([0-9.]+)s"
)
GITHUB_RE = re.compile(r"GitHub URL: (https://github\.com/[^\s]+)")
PROJECT_NAME_RE = re.compile(r"Project Name:\s*([^\n]+)")
FILES_CREATED_RE = re.compile(r"Files created:\s*(\d+)")
DEVOPS_WROTE_RE = re.compile(r"\[DEVOPS\] Wrote (.+)")

LANG_MAP = {
    "js": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "jsx": "javascript",
    "py": "python",
    "html": "html",
    "css": "css",
    "json": "json",
    "md": "markdown",
}

DEFAULT_CHANNEL = "#general"
DEFAULT_TIMEOUT_S = float(os.getenv("GRIFFIN_PIPELINE_TIMEOUT", "300"))


# ── Secret masking ──────────────────────────────────────────────────────────────
_MASK = "***REDACTED***"

# Well known token shapes that should never be written to the database verbatim.
_SECRET_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{10,}"),
]

# key=value or key: value pairs whose key names a secret.
_SECRET_KV_RE = re.compile(
    r"(?i)\b([A-Za-z0-9_]*(?:token|secret|api[_-]?key|access[_-]?key|password|passwd|pwd)[A-Za-z0-9_]*)"
    r"(\s*[=:]\s*)"
    r"([^\s'\"]+)"
)


def mask_secrets(text: Optional[str]) -> str:
    """Redact token and secret values in a string before it is persisted."""
    if not text:
        return text or ""
    masked = text
    for pattern in _SECRET_PATTERNS:
        masked = pattern.sub(_MASK, masked)
    masked = _SECRET_KV_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{_MASK}", masked)
    return masked


def mask_json(value: Any) -> Any:
    """Recursively mask secret values inside a JSON serializable structure."""
    if isinstance(value, str):
        return mask_secrets(value)
    if isinstance(value, dict):
        return {key: mask_json(val) for key, val in value.items()}
    if isinstance(value, list):
        return [mask_json(item) for item in value]
    return value


def resolve_repo_root() -> Path:
    """Return the repository root that contains the ML package.

    Honors GRIFFIN_REPO_ROOT, otherwise walks up from this file
    (backend/api/app/pipeline.py -> repo root).
    """
    override = os.getenv("GRIFFIN_REPO_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[3]


class PipelineRunner:
    """Run the ML pipeline for one prompt and stream mirrored websocket messages."""

    def __init__(
        self,
        prompt: str,
        emit: Callable[[dict[str, Any]], None],
        session_factory: Callable[[], Session],
        repo_root: Optional[Path] = None,
        python_exe: Optional[str] = None,
        env: Optional[dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT_S,
        channel: str = DEFAULT_CHANNEL,
    ) -> None:
        self.prompt = prompt
        self.emit = emit
        self.session_factory = session_factory
        self.repo_root = Path(repo_root) if repo_root else resolve_repo_root()
        self.python_exe = python_exe or sys.executable
        self.env = env if env is not None else os.environ.copy()
        self.timeout = timeout
        self.channel = channel

        self.db: Optional[Session] = None
        self.project_id: Optional[str] = None
        self.proc: Optional[subprocess.Popen[str]] = None

        self._office_ids: dict[str, str] = {}
        self._stdout_buffer: list[str] = []
        self._stderr_lines: list[str] = []
        self._stderr_thread: Optional[threading.Thread] = None
        self._watchdog: Optional[threading.Timer] = None
        self._stopped = False
        self._timed_out = False

    # ── public API ──────────────────────────────────────────────────────────────
    def run(self) -> None:
        """Execute the pipeline end to end, emitting mirrored messages."""
        self.db = self.session_factory()
        try:
            self._create_project()
            self._send_progress(
                f'Starting ML pipeline for: "{self.prompt}"\n\n'
                "This will take 30-60 seconds..."
            )
            self._spawn_process()
            self._consume_stdout()
            self._finalize()
        except Exception as exc:  # pragma: no cover - defensive guard
            self.emit(
                {"type": "error", "data": f"Backend pipeline error: {exc}"[:400]}
            )
        finally:
            if self._watchdog is not None:
                self._watchdog.cancel()
            if self.db is not None:
                self.db.close()

    def stop(self) -> None:
        """Signal the runner to stop and terminate the child process if running."""
        self._stopped = True
        proc = self.proc
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

    # ── process lifecycle ───────────────────────────────────────────────────────
    def _spawn_process(self) -> None:
        env = dict(self.env)
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")

        self.proc = subprocess.Popen(
            [self.python_exe, "-m", "ML.main", self.prompt],
            cwd=str(self.repo_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        self._watchdog = threading.Timer(self.timeout, self._on_timeout)
        self._watchdog.daemon = True
        self._watchdog.start()

        self._stderr_thread = threading.Thread(target=self._consume_stderr, daemon=True)
        self._stderr_thread.start()

    def _on_timeout(self) -> None:
        self._timed_out = True
        self.stop()

    def _consume_stdout(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for raw in self.proc.stdout:
            self._stdout_buffer.append(raw)
            if self._stopped:
                break
            line = raw.rstrip("\r\n")
            if not line.strip():
                continue
            self._handle_stdout_line(line)

    def _consume_stderr(self) -> None:
        assert self.proc is not None and self.proc.stderr is not None
        for raw in self.proc.stderr:
            line = raw.rstrip("\r\n")
            if not line.strip():
                continue
            clean = ANSI_RE.sub("", line)
            self._stderr_lines.append(clean)
            self.emit({"type": "terminal", "data": f"[ERROR] {clean}"})

    # ── stdout parsing (mirrors the Bun ml-service line handling) ───────────────
    def _handle_stdout_line(self, line: str) -> None:
        clean = ANSI_RE.sub("", line)

        # Structured live events (office status). Not echoed to the terminal.
        if clean.startswith(EVENT_PREFIX):
            try:
                evt = json.loads(clean[len(EVENT_PREFIX):])
            except Exception:
                evt = None
            if isinstance(evt, dict) and evt.get("kind") == "office_status":
                self.emit({"type": "office_status", "data": evt})
                self._persist_office_status(evt)
            return

        self.emit({"type": "terminal", "data": clean})

        if ("OFFICE" in line) or ("✅" in line) or ("⏳" in line):
            self.emit({"type": "progress", "data": clean})
            self._persist_message(clean, artifacts={"kind": "progress"})

        if (
            ("COST OPTIMIZER" in line)
            or ("Token usage:" in line)
            or ("\U0001f4b0" in line)
            or ("\U0001f4b5" in line)
        ):
            self.emit({"type": "cost_update", "data": clean})

        if ("Token usage:" in line) and ("cost=$" in line):
            match = TOKEN_RE.search(clean)
            if match:
                self.emit(
                    {
                        "type": "token_usage",
                        "data": {
                            "office": match.group(1),
                            "input_tokens": int(match.group(2)),
                            "output_tokens": int(match.group(3)),
                            "cost_usd": float(match.group(4)),
                            "latency_s": float(match.group(5)),
                        },
                    }
                )

    # ── completion handling ─────────────────────────────────────────────────────
    def _finalize(self) -> None:
        assert self.proc is not None
        self.proc.wait()
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=5)
        if self._watchdog is not None:
            self._watchdog.cancel()

        code = self.proc.returncode
        buffer = "".join(self._stdout_buffer)

        if code == 0 and not self._timed_out:
            self._emit_success(buffer)
        else:
            self._emit_failure()

    def _emit_success(self, buffer: str) -> None:
        github_match = GITHUB_RE.search(buffer)
        github_url = github_match.group(1) if github_match else None

        name_match = PROJECT_NAME_RE.search(buffer)
        project_name = name_match.group(1).strip() if name_match else "Generated Project"

        files_match = FILES_CREATED_RE.search(buffer)
        file_count = int(files_match.group(1)) if files_match else 0

        files = [m.group(1).strip() for m in DEVOPS_WROTE_RE.finditer(buffer)]

        for filepath in files:
            ext = filepath.rsplit(".", 1)[-1] if "." in filepath else "txt"
            self.emit(
                {
                    "type": "file",
                    "data": {
                        "filename": filepath,
                        "language": LANG_MAP.get(ext, "plaintext"),
                        "path": filepath,
                    },
                }
            )

        self._update_project_name(project_name)

        if github_url:
            success_msg = (
                f"Project complete! **{project_name}** deployed with "
                f"{file_count} files.\n\n[View on GitHub]({github_url})"
            )
        else:
            success_msg = (
                f"Project complete! **{project_name}** generated with "
                f"{file_count} files. Check ML/sandbox/"
            )

        self._persist_message(
            success_msg,
            artifacts={
                "kind": "complete",
                "files": files,
                "githubUrl": github_url,
                "projectName": project_name,
            },
        )

        complete: dict[str, Any] = {
            "type": "complete",
            "data": success_msg,
            "projectName": project_name,
            "files": files,
        }
        if github_url:
            complete["githubUrl"] = github_url
        self.emit(complete)

    def _emit_failure(self) -> None:
        if self._timed_out:
            reason = f"pipeline timed out after {self.timeout:.0f}s"
        else:
            reason = "\n".join(self._stderr_lines) or "ML pipeline failed with unknown error"
        self.emit({"type": "error", "data": f"ML pipeline failed: {reason[:200]}"})

    # ── persistence helpers ─────────────────────────────────────────────────────
    def _create_project(self) -> None:
        assert self.db is not None
        project = Project(
            name=mask_secrets(self.prompt.strip())[:200],
            root_path=str(self.repo_root),
        )
        self.db.add(project)
        self.db.commit()
        self.project_id = project.id

    def _update_project_name(self, name: str) -> None:
        assert self.db is not None and self.project_id is not None
        project = self.db.get(Project, self.project_id)
        if project is not None:
            project.name = name
            project.root_path = str(self.repo_root)
            self.db.commit()

    def _persist_message(
        self,
        content: str,
        artifacts: Optional[dict[str, Any]] = None,
        office_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> None:
        assert self.db is not None and self.project_id is not None
        message = Message(
            project_id=self.project_id,
            office_id=office_id,
            channel=channel or self.channel,
            content=mask_secrets(content),
            artifacts=mask_json(artifacts or {}),
        )
        self.db.add(message)
        self.db.commit()

    def _persist_office_status(self, evt: dict[str, Any]) -> None:
        role = str(evt.get("office", "unknown"))
        status = str(evt.get("status", "")).lower()
        context = {
            "name": evt.get("name"),
            "status": evt.get("status"),
            "kind": evt.get("kind"),
        }
        office_id = self._upsert_office(role, status, context)
        content = f"{evt.get('name', role)} -> {evt.get('status', '')}"
        self._persist_message(content, artifacts=mask_json(evt), office_id=office_id)

    def _upsert_office(
        self, role: str, status: str, context: dict[str, Any]
    ) -> str:
        assert self.db is not None and self.project_id is not None
        existing_id = self._office_ids.get(role)
        if existing_id is None:
            office = Office(
                project_id=self.project_id,
                role=role,
                status=status,
                current_context=context,
            )
            self.db.add(office)
            self.db.commit()
            self._office_ids[role] = office.id
            return office.id

        office = self.db.get(Office, existing_id)
        if office is not None:
            office.status = status
            office.current_context = context
            self.db.commit()
        return existing_id

    # ── small helpers ───────────────────────────────────────────────────────────
    def _send_progress(self, text: str) -> None:
        self.emit({"type": "progress", "data": text})
        self._persist_message(text, artifacts={"kind": "progress"})
