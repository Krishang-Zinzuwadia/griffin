"""Event parity and interim /ws security gate tests.

These cover the shippability blockers the FastAPI backend closes:

* code_artifact and deploy_step events are forwarded to the client (Monaco live
  code view and the Deploy Monitor), matching the Bun ml-service contract.
* Inbound God Mode user_command messages are handled without crashing.
* The interim gate: an over-length prompt is rejected before spawning, and an
  optional shared secret (GRIFFIN_WS_TOKEN) gates the connection.

Everything runs offline in mock mode and stays deterministic.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app

# Terminal message types that end a pipeline run.
_TERMINAL = {"complete", "error"}


def test_ws_forwards_code_artifact_and_deploy_step_and_completes() -> None:
    """A mock run must forward code_artifact and deploy_step, then complete."""
    assert os.environ.get("LLM_PROVIDER") == "mock"

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "prompt", "data": "Create a simple counter page"})

            types_seen: set[str] = set()
            final: dict | None = None
            for _ in range(20000):
                message = ws.receive_json()
                types_seen.add(message.get("type"))
                if message.get("type") in _TERMINAL:
                    final = message
                    break

        assert final is not None, "pipeline never produced a terminal message"
        assert final["type"] == "complete", f"pipeline errored: {final}"

        # The two events that were previously dropped on the FastAPI path.
        assert "code_artifact" in types_seen, "expected code_artifact events"
        assert "deploy_step" in types_seen, "expected deploy_step events"


def test_ws_rejects_over_length_prompt() -> None:
    """A prompt longer than the bound is rejected before any pipeline spawns."""
    limit = int(os.getenv("GRIFFIN_MAX_PROMPT_CHARS", "4000"))
    over_length = "a" * (limit + 1)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "prompt", "data": over_length})
            reply = ws.receive_json()

    assert reply["type"] == "error"
    assert str(limit) in reply["data"]
    # No pipeline artifacts should follow a rejected prompt.
    assert "office_status" not in reply.get("type", "")


def test_ws_token_gate_rejects_without_and_accepts_with_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With GRIFFIN_WS_TOKEN set, only clients presenting it may connect."""
    monkeypatch.setenv("GRIFFIN_WS_TOKEN", "s3cret-token")

    with TestClient(app) as client:
        # Missing token: the handshake is rejected.
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws") as ws:
                ws.receive_json()

        # Wrong token: also rejected.
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws?token=nope") as ws:
                ws.receive_json()

        # Correct token: accepted, and commands are handled normally.
        with client.websocket_connect("/ws?token=s3cret-token") as ws:
            ws.send_json({"type": "user_command", "command": "/deploy --force"})
            reply = ws.receive_json()
            assert reply == {"type": "terminal", "data": "[system] force deploy armed"}


def test_ws_user_command_is_handled_without_error() -> None:
    """God Mode commands get terminal replies and never crash the connection."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "user_command", "command": "/deploy --force"})
            assert ws.receive_json() == {
                "type": "terminal",
                "data": "[system] force deploy armed",
            }

            ws.send_json({"type": "user_command", "command": "/evacuate"})
            assert ws.receive_json() == {
                "type": "terminal",
                "data": "[system] session evacuated",
            }

            ws.send_json({"type": "user_command", "command": "/bogus"})
            assert ws.receive_json() == {
                "type": "terminal",
                "data": "[system] unknown command",
            }

            # The connection is still alive and usable after the commands.
            ws.send_json({"type": "user_command", "command": "/evacuate"})
            assert ws.receive_json()["type"] == "terminal"
