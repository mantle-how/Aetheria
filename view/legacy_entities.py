from __future__ import annotations

from dataclasses import dataclass

from apps.engine.bootstrap import build_demo_simulation
from domain.agent.agent_model import ABMAgent
from domain.simulation.config import SimulationConfig
from domain.simulation.perception import ABMSimulation


@dataclass
class Entity:
    """給舊版視覺化層使用的簡單可渲染物件。"""

    entity_id: int
    name: str
    x: float
    y: float


@dataclass
class InteractiveEntity(Entity):
    """地點或互動物件在畫面上的標記。"""

    durability: float = 100.0


def simulation_to_entities(
    simulation: ABMSimulation,
) -> list[Entity | InteractiveEntity | ABMAgent]:
    """把目前模擬狀態轉成視覺化層可以直接繪製的物件。"""

    place_markers = [
        InteractiveEntity(
            entity_id=1000 + index,
            name=place.name,
            x=place.x,
            y=place.y,
            durability=max(1.0, float(place.food_stock + 1)),
        )
        for index, place in enumerate(simulation.world.places.values())
    ]
    return [*place_markers, *simulation.world.agents]


def generate_demo_entities(
    steps: int = 0,
    config: SimulationConfig | None = None,
) -> list[Entity | InteractiveEntity | ABMAgent]:
    """先跑幾個 tick，再回傳給視覺化層使用的物件。"""

    simulation = build_demo_simulation(config)
    simulation.run(steps)
    return simulation_to_entities(simulation)
