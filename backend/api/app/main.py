"""FastAPI backend for Griffin.

This service mirrors the Bun ml-service websocket contract (see
backend/ml-service/index.ts) and adds database persistence for projects, offices,
and messages. It exposes a small REST surface for reading persisted data and a
``/ws`` endpoint that runs the ML pipeline and streams the same message types the
Bun service emits.

Run it with:

    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal, get_session, init_db
from .models import Message, Office, Project
from .pipeline import PipelineRunner

logger = logging.getLogger("griffin.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    init_db()
    yield


app = FastAPI(title="Griffin Backend API", lifespan=lifespan)


# ── Interim security gate configuration ─────────────────────────────────────────
# These are the stopgap controls for the unauthenticated /ws endpoint: a global
# concurrency cap, an optional shared secret, and a prompt length bound. Env var
# names are fixed by contract: GRIFFIN_MAX_CONCURRENCY, GRIFFIN_WS_TOKEN,
# GRIFFIN_MAX_PROMPT_CHARS.
_DEFAULT_MAX_CONCURRENCY = 3
_DEFAULT_MAX_PROMPT_CHARS = 4000


def _positive_int_env(name: str, default: int) -> int:
    """Read a positive integer env var, falling back to default when unusable."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


# Global concurrency limiter shared across all connections. Sized once at import
# from GRIFFIN_MAX_CONCURRENCY. A threading semaphore is used (rather than an
# asyncio one) so it is independent of any particular event loop.
_RUN_SEMAPHORE = threading.BoundedSemaphore(
    _positive_int_env("GRIFFIN_MAX_CONCURRENCY", _DEFAULT_MAX_CONCURRENCY)
)


# ── REST endpoints ──────────────────────────────────────────────────────────────
@app.get("/")
def health() -> dict[str, str]:
    """Health check."""
    return {"status": "ok"}


@app.get("/projects")
def list_projects(db: Session = Depends(get_session)) -> list[dict[str, Any]]:
    """List all projects, newest first."""
    projects = db.scalars(
        select(Project).order_by(Project.created_at.desc())
    ).all()
    return [project.to_dict() for project in projects]


@app.get("/projects/{project_id}")
def get_project(
    project_id: str, db: Session = Depends(get_session)
) -> dict[str, Any]:
    """Return a single project with its offices."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    data = project.to_dict()
    offices = db.scalars(
        select(Office).where(Office.project_id == project_id)
    ).all()
    data["offices"] = [office.to_dict() for office in offices]
    return data


@app.get("/projects/{project_id}/messages")
def get_project_messages(
    project_id: str, db: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    """Return the messages for a project, oldest first."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    messages = db.scalars(
        select(Message)
        .where(Message.project_id == project_id)
        .order_by(Message.created_at.asc())
    ).all()
    return [message.to_dict() for message in messages]


# ── WebSocket endpoint ──────────────────────────────────────────────────────────
class _ConnectionState:
    """Per-connection state so inbound commands can act on the running pipeline."""

    def __init__(self) -> None:
        self.runner: Optional[PipelineRunner] = None
        self.task: Optional[asyncio.Task[Any]] = None
        # Armed by "/deploy --force"; consumed once on the next prompt run.
        self.force_deploy: bool = False
        # Serializes sends so the receive loop and the pipeline drain task never
        # interleave writes to the same socket.
        self.send_lock = asyncio.Lock()


async def _send(websocket: WebSocket, state: _ConnectionState, item: dict[str, Any]) -> None:
    """Send one JSON message under the connection send lock."""
    async with state.send_lock:
        await websocket.send_json(item)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept prompts and stream the mirrored ml-service message types.

    The client sends {"type": "prompt", "data": "..."}. For each prompt the ML
    pipeline runs in a worker thread and the messages it produces are forwarded
    over the socket while projects, offices, and messages are persisted. Inbound
    {"type": "user_command", "command": "..."} messages drive God Mode controls.

    An optional shared secret (GRIFFIN_WS_TOKEN) gates the connection: when set,
    the client must present it as a ?token= query parameter.
    """
    expected_token = os.getenv("GRIFFIN_WS_TOKEN")
    if expected_token:
        if websocket.query_params.get("token") != expected_token:
            # Reject before accepting the handshake.
            await websocket.close(code=1008)
            return
    else:
        logger.warning(
            "GRIFFIN_WS_TOKEN is not set; /ws accepts unauthenticated clients"
        )

    await websocket.accept()

    state = _ConnectionState()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if not isinstance(message, dict):
                continue
            msg_type = message.get("type")
            try:
                if msg_type == "user_command":
                    await _handle_user_command(websocket, state, message)
                elif msg_type == "prompt":
                    await _handle_prompt(
                        websocket, state, str(message.get("data", ""))
                    )
            except WebSocketDisconnect:
                raise
            except Exception as exc:  # never let one bad message crash the server
                logger.exception("Error handling %s message: %s", msg_type, exc)
    except WebSocketDisconnect:
        return
    finally:
        runner = state.runner
        if runner is not None:
            runner.stop()
        task = state.task
        if task is not None and not task.done():
            try:
                await task
            except Exception:  # pragma: no cover - defensive cleanup
                pass


async def _handle_user_command(
    websocket: WebSocket, state: _ConnectionState, message: dict[str, Any]
) -> None:
    """Handle an inbound God Mode command, mirroring the Bun ml-service.

    This must never crash the server. Unknown commands get a terminal reply.
    """
    command = str(message.get("command", "")).strip()
    if command == "/evacuate":
        runner = state.runner
        if runner is not None:
            runner.stop()
        await _send(
            websocket, state, {"type": "terminal", "data": "[system] session evacuated"}
        )
    elif command == "/deploy --force":
        # One-shot flag: the next prompt run gets GRIFFIN_FORCE_DEPLOY=1 injected.
        state.force_deploy = True
        await _send(
            websocket, state, {"type": "terminal", "data": "[system] force deploy armed"}
        )
    else:
        await _send(
            websocket, state, {"type": "terminal", "data": "[system] unknown command"}
        )


async def _handle_prompt(
    websocket: WebSocket, state: _ConnectionState, prompt: str
) -> None:
    """Validate and start a pipeline run for one prompt, applying the gate."""
    max_prompt_chars = _positive_int_env(
        "GRIFFIN_MAX_PROMPT_CHARS", _DEFAULT_MAX_PROMPT_CHARS
    )
    if len(prompt) > max_prompt_chars:
        await _send(
            websocket,
            state,
            {
                "type": "error",
                "data": (
                    f"Prompt too long: {len(prompt)} characters exceeds the "
                    f"{max_prompt_chars} character limit."
                ),
            },
        )
        return

    if state.task is not None and not state.task.done():
        await _send(
            websocket,
            state,
            {"type": "error", "data": "A pipeline is already running on this connection."},
        )
        return

    # Global concurrency cap: reject immediately when at capacity.
    if not _RUN_SEMAPHORE.acquire(blocking=False):
        await _send(
            websocket,
            state,
            {
                "type": "error",
                "data": "Server busy: too many concurrent pipeline runs. Try again shortly.",
            },
        )
        return

    # Consume the one-shot force-deploy flag for this run.
    force_deploy = state.force_deploy
    state.force_deploy = False

    state.task = asyncio.create_task(
        _run_pipeline(websocket, state, prompt, force_deploy)
    )


async def _run_pipeline(
    websocket: WebSocket,
    state: _ConnectionState,
    prompt: str,
    force_deploy: bool,
) -> None:
    """Run one pipeline invocation, draining its messages to the socket.

    Owns the concurrency slot acquired by the caller and always releases it.
    """
    try:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Any] = asyncio.Queue()

        def emit(item: dict[str, Any]) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, item)

        env = os.environ.copy()
        if force_deploy:
            env["GRIFFIN_FORCE_DEPLOY"] = "1"

        runner = PipelineRunner(
            prompt=prompt,
            emit=emit,
            session_factory=SessionLocal,
            env=env,
        )
        state.runner = runner

        def worker() -> None:
            try:
                runner.run()
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        worker_task = asyncio.create_task(asyncio.to_thread(worker))
        disconnected = False
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if disconnected:
                    continue
                try:
                    await _send(websocket, state, item)
                except Exception:
                    # Client went away; stop the child and keep draining the
                    # queue so the worker can finish and be joined cleanly.
                    disconnected = True
                    runner.stop()
        finally:
            runner.stop()
            await worker_task
    finally:
        _RUN_SEMAPHORE.release()
        if state.runner is not None and (
            state.task is None or state.task is asyncio.current_task()
        ):
            state.runner = None
