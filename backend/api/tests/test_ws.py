"""WebSocket test: run the mock pipeline end to end over /ws and assert the
mirrored message types arrive and a project row is persisted."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app

# Terminal message types that end a pipeline run.
_TERMINAL = {"complete", "error"}


def test_ws_streams_contract_and_persists() -> None:
    assert os.environ.get("LLM_PROVIDER") == "mock"

    with TestClient(app) as client:
        before_ids = {item["id"] for item in client.get("/projects").json()}

        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "prompt", "data": "Create a simple counter page"})

            types_seen: set[str] = set()
            final: dict | None = None
            # Generous cap; a mock run produces a few hundred messages at most.
            for _ in range(20000):
                message = ws.receive_json()
                types_seen.add(message.get("type"))
                if message.get("type") in _TERMINAL:
                    final = message
                    break

        assert final is not None, "pipeline never produced a terminal message"
        assert final["type"] == "complete", f"pipeline errored: {final}"

        # The core contract message types must appear during the run.
        assert "office_status" in types_seen
        assert "token_usage" in types_seen
        assert "progress" in types_seen
        assert "terminal" in types_seen

        # The final complete carries a project name (and no github url offline).
        assert final.get("projectName")
        assert "githubUrl" not in final

        # A new project row was persisted, named after the completed project.
        after = client.get("/projects").json()
        new_projects = [item for item in after if item["id"] not in before_ids]
        assert new_projects, "expected a new project row to be persisted"

        names = {item["name"] for item in new_projects}
        assert final["projectName"] in names

        # That project has offices and messages persisted too.
        project_id = new_projects[0]["id"]
        detail = client.get(f"/projects/{project_id}").json()
        assert detail["offices"], "expected office rows to be persisted"

        messages = client.get(f"/projects/{project_id}/messages").json()
        assert messages, "expected message rows to be persisted"
        channels = {row["channel"] for row in messages}
        assert "#general" in channels
