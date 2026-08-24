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
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal, get_session, init_db
from .models import Message, Office, Project
from .pipeline import PipelineRunner


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    init_db()
    yield


app = FastAPI(title="Griffin Backend API", lifespan=lifespan)


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
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept prompts and stream the mirrored ml-service message types.

    The client sends {"type": "prompt", "data": "..."}. For each prompt the ML
    pipeline runs in a worker thread and the messages it produces are forwarded
    over the socket while projects, offices, and messages are persisted.
    """
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except (ValueError, TypeError):
                continue
            if isinstance(message, dict) and message.get("type") == "prompt":
                prompt = str(message.get("data", ""))
                await _run_pipeline(websocket, prompt)
    except WebSocketDisconnect:
        return


async def _run_pipeline(websocket: WebSocket, prompt: str) -> None:
    """Run one pipeline invocation, draining its messages to the socket."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[Any] = asyncio.Queue()

    def emit(item: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, item)

    runner = PipelineRunner(
        prompt=prompt,
        emit=emit,
        session_factory=SessionLocal,
    )

    def worker() -> None:
        try:
            runner.run()
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    task = asyncio.create_task(asyncio.to_thread(worker))
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            await websocket.send_json(item)
    finally:
        runner.stop()
        await task
