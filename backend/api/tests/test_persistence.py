"""Persistence and REST tests: create rows, then read them back over HTTP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import Message, Office, Project
from app.pipeline import mask_secrets


def _seed_project() -> str:
    """Insert a project with one office and one message, return the project id."""
    db = SessionLocal()
    try:
        project = Project(name="Seed Project", root_path="/tmp/seed")
        db.add(project)
        db.commit()

        office = Office(
            project_id=project.id,
            role="backend_engineer",
            status="working",
            current_context={"name": "Backend Engineer"},
        )
        db.add(office)
        db.commit()

        message = Message(
            project_id=project.id,
            office_id=office.id,
            channel="#engineering-core",
            content="Backend Engineer -> WORKING",
            artifacts={"kind": "office_status"},
        )
        db.add(message)
        db.commit()
        return project.id
    finally:
        db.close()


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_create_and_query_project() -> None:
    project_id = _seed_project()

    with TestClient(app) as client:
        listing = client.get("/projects")
        assert listing.status_code == 200
        ids = [item["id"] for item in listing.json()]
        assert project_id in ids

        detail = client.get(f"/projects/{project_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["name"] == "Seed Project"
        assert body["root_path"] == "/tmp/seed"
        assert len(body["offices"]) == 1
        assert body["offices"][0]["role"] == "backend_engineer"
        assert body["offices"][0]["status"] == "working"

        messages = client.get(f"/projects/{project_id}/messages")
        assert messages.status_code == 200
        rows = messages.json()
        assert len(rows) == 1
        assert rows[0]["channel"] == "#engineering-core"
        assert rows[0]["content"] == "Backend Engineer -> WORKING"


def test_missing_project_returns_404() -> None:
    with TestClient(app) as client:
        assert client.get("/projects/does-not-exist").status_code == 404
        assert client.get("/projects/does-not-exist/messages").status_code == 404


def test_secret_values_are_masked() -> None:
    secret_line = "Using GITHUB_TOKEN=ghp_abcdef0123456789abcdef0123 for push"
    masked = mask_secrets(secret_line)
    assert "ghp_abcdef0123456789abcdef0123" not in masked
    assert "REDACTED" in masked
