from __future__ import annotations

import asyncio
from pathlib import Path
import threading
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from model.config import LoggingConfig, PopulationConfig, SimulationConfig
from model.test import build_demo_simulation

TARGET_TPS = 30
STREAM_FPS = 30
DEFAULT_AGENT_COUNT = 50
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


class SimulationRuntime:
    def __init__(self, agent_count: int = DEFAULT_AGENT_COUNT) -> None:
        config = SimulationConfig(
            logging=LoggingConfig(print_to_stdout=False),
            population=PopulationConfig(agent_count=agent_count),
        )
        self._simulation = build_demo_simulation(config)
        self._simulation_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._running = True
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None

    def start(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._stop_event.clear()
        self._worker = threading.Thread(
            target=self._simulation_loop,
            name="simulation-runtime",
            daemon=True,
        )
        self._worker.start()

    def stop(self) -> None:
        self._stop_event.set()
        worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=1.0)
        self._worker = None

    def set_running(self, running: bool) -> None:
        with self._state_lock:
            self._running = bool(running)

    def toggle_running(self) -> bool:
        with self._state_lock:
            self._running = not self._running
            return self._running

    def is_running(self) -> bool:
        with self._state_lock:
            return self._running

    def step_once(self) -> None:
        with self._simulation_lock:
            self._simulation.step()

    def snapshot(self) -> dict:
        with self._simulation_lock:
            world = self._simulation.world
            agents = [self._serialize_agent(agent) for agent in world.agents]
            places = [self._serialize_place(place) for place in world.places.values()]
            average_divisor = max(1, len(world.agents))
            average_hunger = sum(agent.needs.hunger for agent in world.agents) / average_divisor
            average_energy = sum(agent.needs.energy for agent in world.agents) / average_divisor
            average_mood = sum(agent.needs.mood for agent in world.agents) / average_divisor
            average_health = sum(agent.health for agent in world.agents) / average_divisor
            alive_count = sum(1 for agent in world.agents if agent.is_alive)
            dead_count = len(world.agents) - alive_count
            tick_count = world.tick_count
            minute_of_day = world.minute_of_day

        return {
            "tick": tick_count,
            "minute_of_day": minute_of_day,
            "agents": agents,
            "places": places,
            "stats": {
                "running": self.is_running(),
                "agent_count": len(agents),
                "alive_count": alive_count,
                "dead_count": dead_count,
                "average_hunger": round(average_hunger, 4),
                "average_energy": round(average_energy, 4),
                "average_mood": round(average_mood, 4),
                "average_health": round(average_health, 4),
            },
        }

    def _simulation_loop(self) -> None:
        tick_interval_seconds = 1.0 / float(max(1, TARGET_TPS))
        next_tick_time = time.perf_counter()
        while not self._stop_event.is_set():
            if not self.is_running():
                next_tick_time = time.perf_counter()
                time.sleep(0.02)
                continue

            with self._simulation_lock:
                self._simulation.step()

            next_tick_time += tick_interval_seconds
            sleep_for = next_tick_time - time.perf_counter()
            if sleep_for > 0:
                time.sleep(min(sleep_for, 0.02))
            else:
                next_tick_time = time.perf_counter()

    @staticmethod
    def _serialize_agent(agent) -> dict:
        return {
            "agent_id": int(agent.agent_id),
            "name": str(agent.name),
            "x": float(agent.x),
            "y": float(agent.y),
            "occupation": str(agent.occupation),
            "home_place_id": str(agent.home_place_id),
            "work_place_id": str(agent.work_place_id),
            "social_place_id": str(agent.social_place_id),
            "parent_home_place_ids": list(agent.parent_home_place_ids),
            "food_inventory": int(agent.food_inventory),
            "needs": {
                "hunger": float(agent.needs.hunger),
                "energy": float(agent.needs.energy),
                "mood": float(agent.needs.mood),
            },
            "health": float(agent.health),
            "is_alive": bool(agent.is_alive),
            "death_tick": None if agent.death_tick is None else int(agent.death_tick),
            "last_action": None if agent.last_action is None else str(agent.last_action.value),
            "is_socializing_until_recovered": bool(agent.is_socializing_until_recovered),
            "is_restocking_food": bool(agent.is_restocking_food),
        }

    @staticmethod
    def _serialize_place(place) -> dict:
        return {
            "place_id": str(place.place_id),
            "name": str(place.name),
            "kind": str(place.kind),
            "x": float(place.x),
            "y": float(place.y),
            "food_stock": int(place.food_stock),
        }


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
        if command == "play":
            runtime.set_running(True)
        elif command == "pause":
            runtime.set_running(False)
        elif command == "toggle":
            runtime.toggle_running()
        elif command == "step":
            runtime.step_once()


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
