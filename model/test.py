from __future__ import annotations

from dataclasses import dataclass
from math import ceil, sqrt

from domain.agent.agent_model import ABMAgent
from domain.agent.need import NeedState
from domain.agent.relationship import RelationshipLedger
from domain.simulation.perception import ABMSimulation, SimulationLogger
from domain.world.place import Place
from domain.world.rule import WorldRules
from domain.world.world_model import SimulationWorld
from model.action import ActionType
from model.config import SimulationConfig, build_default_config


@dataclass
class Entity:
    """給既有視覺化層使用的簡單可渲染物件。"""

    entity_id: int
    name: str
    x: float
    y: float


@dataclass
class InteractiveEntity(Entity):
    """地點或互動物件在畫面上的標記。"""

    durability: float = 100.0


class Agent(ABMAgent):
    """保留舊版視覺化介面的相容代理人包裝。"""

    def __init__(
        self,
        entity_id: int,
        name: str,
        x: float,
        y: float,
        gender: str = "U",
        health: float = 100.0,
        years: int = 0,
        bag: list[str] | None = None,
        occupation: str = "居民",
        home_place_id: str | None = None,
        work_place_id: str | None = None,
        social_place_id: str = "plaza_1",
        needs: NeedState | None = None,
    ):
        base_config = build_default_config()
        inventory = [] if bag is None else list(bag)
        initial_needs = NeedState.from_config(base_config.needs) if needs is None else needs

        resolved_home_place_id = home_place_id or f"home_{entity_id}"
        resolved_work_place_id = work_place_id or "workhub_1"

        super().__init__(
            agent_id=entity_id,
            name=name,
            x=x,
            y=y,
            occupation=occupation,
            home_place_id=resolved_home_place_id,
            work_place_id=resolved_work_place_id,
            social_place_id=social_place_id,
            needs=initial_needs,
            food_inventory=len(inventory),
            relationships=RelationshipLedger(),
            last_action=ActionType.IDLE,
            health=float(health),
            is_alive=True,
        )
        self.gender = gender
        self.years = years
        self.bag = inventory


def build_demo_simulation(config: SimulationConfig | None = None) -> ABMSimulation:
    """建立一個可重現的多代理人示範世界。"""

    if config is None:
        resolved_config = build_default_config()
        resolved_config.population.agent_count = 50
    else:
        resolved_config = config

    rules = WorldRules(resolved_config)
    places = _build_demo_places(resolved_config)
    agents = _build_demo_agents(resolved_config, places)
    world = SimulationWorld(
        places=places,
        agents=agents,
        rules=rules,
        tick_count=0,
        minute_of_day=resolved_config.world.starting_minute,
    )
    logger = SimulationLogger(resolved_config.logging)
    return ABMSimulation(world=world, logger=logger)


def simulation_to_entities(
    simulation: ABMSimulation,
) -> list[Entity | InteractiveEntity | Agent]:
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
) -> list[Entity | InteractiveEntity | Agent]:
    """先跑幾個 tick，再回傳給視覺化層使用的物件。"""

    simulation = build_demo_simulation(config)
    simulation.run(steps)
    return simulation_to_entities(simulation)


def _build_demo_places(config: SimulationConfig) -> dict[str, Place]:
    places: dict[str, Place] = {}
    service_place_count = 10
    width = float(config.world.width)
    height = float(config.world.height)
    market_food_stock = max(5, config.population.agent_count * 2)

    work_positions = _build_cluster_positions(
        count=service_place_count,
        center_x=width * 0.74,
        center_y=height * 0.74,
        span_x=width * 0.24,
        span_y=height * 0.22,
        world_width=width,
        world_height=height,
    )
    for index, (x, y) in enumerate(work_positions, start=1):
        place_id = f"workhub_{index}"
        places[place_id] = Place(
            place_id=place_id,
            name=f"工作站 {index}",
            kind="work",
            x=x,
            y=y,
        )

    market_positions = _build_cluster_positions(
        count=service_place_count,
        center_x=width * 0.24,
        center_y=height * 0.56,
        span_x=width * 0.24,
        span_y=height * 0.22,
        world_width=width,
        world_height=height,
    )
    for index, (x, y) in enumerate(market_positions, start=1):
        place_id = f"market_{index}"
        places[place_id] = Place(
            place_id=place_id,
            name=f"市集 {index}",
            kind="food",
            x=x,
            y=y,
            food_stock=market_food_stock,
            tags={"food"},
        )

    social_positions = _build_cluster_positions(
        count=service_place_count,
        center_x=width * 0.74,
        center_y=height * 0.26,
        span_x=width * 0.24,
        span_y=height * 0.22,
        world_width=width,
        world_height=height,
    )
    for index, (x, y) in enumerate(social_positions, start=1):
        place_id = f"plaza_{index}"
        places[place_id] = Place(
            place_id=place_id,
            name=f"廣場 {index}",
            kind="social",
            x=x,
            y=y,
            tags={"social"},
        )

    agent_count = max(1, config.population.agent_count)
    columns = max(1, int(ceil(sqrt(agent_count))))
    rows = max(1, int(ceil(agent_count / columns)))
    padding_x = 8.0
    padding_y = 8.0
    usable_width = max(1.0, config.world.width - (padding_x * 2.0))
    usable_height = max(1.0, config.world.height - (padding_y * 2.0))
    gap_x = 0.0 if columns <= 1 else usable_width / (columns - 1)
    gap_y = 0.0 if rows <= 1 else usable_height / (rows - 1)

    for index in range(agent_count):
        row = index // columns
        column = index % columns
        home_id = f"home_{index + 1}"
        x = padding_x + (column * gap_x)
        y = padding_y + (row * gap_y)
        places[home_id] = Place(
            place_id=home_id,
            name=f"住家 {index + 1}",
            kind="home",
            x=x,
            y=y,
            food_stock=1,
            tags={"home", "food"},
        )

    return places


def _build_demo_agents(config: SimulationConfig, places: dict[str, Place]) -> list[Agent]:
    base_names = ["小安", "小博", "小佳", "小德", "小依", "小峰", "小雅", "小航"]
    agents: list[Agent] = []
    work_place_ids = sorted(
        [place_id for place_id, place in places.items() if place.kind == "work"],
        key=lambda value: int(value.split("_")[-1]),
    )
    social_place_ids = sorted(
        [place_id for place_id, place in places.items() if place.kind == "social"],
        key=lambda value: int(value.split("_")[-1]),
    )

    for index in range(config.population.agent_count):
        agent_id = index + 1
        name = f"{base_names[index % len(base_names)]}{agent_id}"
        home = places[f"home_{agent_id}"]
        needs = NeedState.from_config(config.needs)

        if index % 3 == 0:
            needs.mood -= 20.0
        elif index % 3 == 1:
            needs.energy -= 35.0
        else:
            needs.hunger += 25.0
        needs.normalize(config.needs)

        bag = [f"ration_{n}" for n in range(config.population.initial_food_per_agent)]
        agent = Agent(
            entity_id=agent_id,
            name=name,
            x=home.x,
            y=home.y,
            gender="U",
            health=config.population.initial_health,
            years=24 + index,
            bag=bag,
            occupation="工作者",
            home_place_id=home.place_id,
            work_place_id=work_place_ids[index % len(work_place_ids)],
            social_place_id=social_place_ids[index % len(social_place_ids)],
            needs=needs,
        )
        agents.append(agent)

    return agents


def _build_cluster_positions(
    count: int,
    center_x: float,
    center_y: float,
    span_x: float,
    span_y: float,
    world_width: float,
    world_height: float,
) -> list[tuple[float, float]]:
    if count <= 0:
        return []

    columns = max(1, int(ceil(sqrt(count))))
    rows = max(1, int(ceil(count / columns)))
    min_x = center_x - (span_x / 2.0)
    min_y = center_y - (span_y / 2.0)
    positions: list[tuple[float, float]] = []

    for index in range(count):
        row = index // columns
        column = index % columns
        if columns == 1:
            x = center_x
        else:
            x = min_x + (span_x * (column / (columns - 1)))
        if rows == 1:
            y = center_y
        else:
            y = min_y + (span_y * (row / (rows - 1)))

        clamped_x = max(2.0, min(world_width - 2.0, x))
        clamped_y = max(2.0, min(world_height - 2.0, y))
        positions.append((clamped_x, clamped_y))

    return positions
