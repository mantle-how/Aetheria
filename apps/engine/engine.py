from __future__ import annotations

from copy import deepcopy
import threading
import time
from typing import Any

from apps.engine.bootstrap import build_demo_simulation
from apps.engine.config import DEFAULT_AGENT_COUNT, TARGET_TPS
from domain.simulation.config import LoggingConfig, PopulationConfig, SimulationConfig
from domain.simulation.perception import ABMSimulation


class SimulationRuntime:
    def __init__(self, agent_count: int = DEFAULT_AGENT_COUNT) -> None:
        self._config = SimulationConfig(
            logging=LoggingConfig(print_to_stdout=False),
            population=PopulationConfig(agent_count=agent_count),
        )
        self._simulation = self._build_simulation()
        self._simulation_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._running = True
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._world_revision = 1

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

    def reset(self) -> None:
        with self._simulation_lock:
            self._simulation = self._build_simulation()
            self._world_revision += 1
        with self._state_lock:
            self._running = True

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

    def snapshot(self) -> dict[str, Any]:
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
            world_revision = self._world_revision

        return {
            "world_revision": world_revision,
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

    def _build_simulation(self) -> ABMSimulation:
        return build_demo_simulation(deepcopy(self._config))

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
    def _serialize_agent(agent) -> dict[str, Any]:
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
    def _serialize_place(place) -> dict[str, Any]:
        return {
            "place_id": str(place.place_id),
            "name": str(place.name),
            "kind": str(place.kind),
            "x": float(place.x),
            "y": float(place.y),
            "food_stock": int(place.food_stock),
        }
