"""FastAPI entrypoint for Griffin backend."""
from json import JSONDecodeError, loads
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Griffin Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a simple health status for readiness/liveness checks."""
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Accept a WebSocket and echo messages back to the client."""
    await websocket.accept()
    await websocket.send_json({"event": "WELCOME", "message": "WebSocket ready"})

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            text_frame = _extract_text_frame(message)
            if text_frame is None:
                await websocket.send_json({
                    "event": "ERROR",
                    "message": "Unsupported frame type; send text or JSON.",
                })
                continue

            try:
                payload = loads(text_frame)
            except JSONDecodeError as exc:
                await websocket.send_json({
                    "event": "ERROR",
                    "message": "Invalid JSON payload; echoing raw text.",
                    "detail": exc.msg,
                    "position": {"line": exc.lineno, "column": exc.colno},
                    "raw": text_frame,
                })
                await websocket.send_json({"event": "ECHO", "payload": {"raw": text_frame}})
                continue

            await websocket.send_json({"event": "ECHO", "payload": payload})
    except WebSocketDisconnect:
        # Client disconnected; nothing else to do.
        return


def _extract_text_frame(message: dict[str, Any]) -> str | None:
    """Return the UTF-8 text payload from a Starlette WebSocket frame."""
    if text := message.get("text"):
        return text

    raw_bytes = message.get("bytes")
    if raw_bytes is None:
        return None

    return raw_bytes.decode("utf-8", errors="replace")
