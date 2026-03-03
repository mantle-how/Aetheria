from __future__ import annotations

from dataclasses import dataclass

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
        health: int = 100,
        years: int = 0,
        bag: list[str] | None = None,
        occupation: str = "居民",
        home_place_id: str | None = None,
        work_place_id: str | None = None,
        social_place_id: str = "plaza",
        needs: NeedState | None = None,
    ):
        base_config = build_default_config()
        inventory = [] if bag is None else list(bag)
        initial_needs = NeedState.from_config(base_config.needs) if needs is None else needs

        resolved_home_place_id = home_place_id or f"home_{entity_id}"
        resolved_work_place_id = work_place_id or "workhub"

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
        )
        self.gender = gender
        self.health = health
        self.years = years
        self.bag = inventory


def build_demo_simulation(config: SimulationConfig | None = None) -> ABMSimulation:
    """建立一個可重現的多代理人示範世界。"""

    resolved_config = build_default_config() if config is None else config
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
    places: dict[str, Place] = {
        "workhub": Place(
            place_id="workhub",
            name="工作站",
            kind="work",
            x=config.world.width * 0.55,
            y=config.world.height * 0.72,
        ),
        "market": Place(
            place_id="market",
            name="市集",
            kind="food",
            x=config.world.width * 0.28,
            y=config.world.height * 0.58,
            food_stock=config.population.agent_count * 4,
            tags={"food"},
        ),
        "plaza": Place(
            place_id="plaza",
            name="廣場",
            kind="social",
            x=config.world.width * 0.68,
            y=config.world.height * 0.32,
            tags={"social"},
        ),
    }

    columns = max(1, min(3, config.population.agent_count))
    for index in range(config.population.agent_count):
        row = index // columns
        column = index % columns
        home_id = f"home_{index + 1}"
        places[home_id] = Place(
            place_id=home_id,
            name=f"住家 {index + 1}",
            kind="home",
            x=12.0 + (column * 18.0),
            y=12.0 + (row * 18.0),
            food_stock=1,
            tags={"home", "food"},
        )

    return places


def _build_demo_agents(config: SimulationConfig, places: dict[str, Place]) -> list[Agent]:
    names = ["小安", "小博", "小佳", "小德", "小依", "小峰", "小雅", "小航"]
    agents: list[Agent] = []

    for index in range(config.population.agent_count):
        agent_id = index + 1
        name = names[index % len(names)]
        home = places[f"home_{agent_id}"]
        needs = NeedState.from_config(config.needs)

        if index % 3 == 0:
            needs.mood -= 20
        elif index % 3 == 1:
            needs.energy -= 35
        else:
            needs.hunger += 25
        needs.normalize(config.needs)

        bag = [f"ration_{n}" for n in range(config.population.initial_food_per_agent)]
        agent = Agent(
            entity_id=agent_id,
            name=name,
            x=home.x,
            y=home.y,
            gender="U",
            health=100,
            years=24 + index,
            bag=bag,
            occupation="工作者",
            home_place_id=home.place_id,
            work_place_id="workhub",
            social_place_id="plaza",
            needs=needs,
        )
        agents.append(agent)

    return agents
