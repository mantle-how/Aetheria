from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from apps.engine.config import DEFAULT_HOST, DEFAULT_PORT, STREAM_FPS
from apps.engine.engine import SimulationRuntime


runtime = SimulationRuntime()
app = FastAPI(title="Aetheria Demo Web", version="1.0.0")
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.on_event("startup")
def _on_startup() -> None:
    runtime.start()


@app.on_event("shutdown")
def _on_shutdown() -> None:
    runtime.stop()


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (static_dir / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.websocket("/ws/sim")
async def websocket_sim(websocket: WebSocket) -> None:
    await websocket.accept()
    sender = asyncio.create_task(_sender_loop(websocket))
    receiver = asyncio.create_task(_receiver_loop(websocket))
    done, pending = await asyncio.wait(
        {sender, receiver},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    for task in done:
        exception = task.exception()
        if exception is not None and not isinstance(exception, WebSocketDisconnect):
            raise exception


async def _sender_loop(websocket: WebSocket) -> None:
    interval_seconds = 1.0 / float(max(1, STREAM_FPS))
    while True:
        await websocket.send_json(runtime.snapshot())
        await asyncio.sleep(interval_seconds)


async def _receiver_loop(websocket: WebSocket) -> None:
    while True:
        payload = await websocket.receive_json()
        if not isinstance(payload, dict):
            continue

        command = str(payload.get("cmd", "")).strip().lower()
        _handle_command(command)


def _handle_command(command: str) -> None:
    if command == "play":
        runtime.set_running(True)
    elif command == "pause":
        runtime.set_running(False)
    elif command == "toggle":
        runtime.toggle_running()
    elif command == "step":
        runtime.step_once()
    elif command == "reset":
        runtime.reset()


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    uvicorn.run(
        "apps.api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run()
