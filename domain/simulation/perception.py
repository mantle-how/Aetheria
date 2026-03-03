from __future__ import annotations

from dataclasses import dataclass, field

from domain.agent.agent_model import ABMAgent
from domain.event.base import SimulationEvent
from domain.world.world_model import SimulationWorld
from model.config import LoggingConfig


@dataclass(frozen=True)
class AgentPerception:
    """代理人決策時使用的局部世界快照。"""

    tick: int
    minute_of_day: int
    current_place_id: str | None
    current_place_has_food: bool
    nearby_agents: tuple[ABMAgent, ...]
    place_positions: dict[str, tuple[float, float]]
    nearest_food_place_id: str | None


@dataclass
class SimulationLogger:
    """簡單的記憶體內事件紀錄器，可選擇同步輸出到終端。"""

    config: LoggingConfig
    lines: list[str] = field(default_factory=list)

    def record(self, event: SimulationEvent) -> None:
        if not self.config.enabled:
            return

        line = event.to_log_line()
        if len(self.lines) >= self.config.max_events:
            self.lines.pop(0)
        self.lines.append(line)

        if self.config.print_to_stdout:
            print(line)


@dataclass
class ABMSimulation:
    """用序列式 tick 更新來推進 ABM 世界。"""

    world: SimulationWorld
    logger: SimulationLogger

    def build_perception(self, agent: ABMAgent) -> AgentPerception:
        current_place = self.world.current_place_for(agent)
        place_positions = {
            place_id: (place.x, place.y)
            for place_id, place in self.world.places.items()
        }
        nearby_agents = tuple(self.world.get_agents_near(agent))

        return AgentPerception(
            tick=self.world.tick_count,
            minute_of_day=self.world.minute_of_day,
            current_place_id=None if current_place is None else current_place.place_id,
            current_place_has_food=False if current_place is None else current_place.has_food(),
            nearby_agents=nearby_agents,
            place_positions=place_positions,
            nearest_food_place_id=self.world.nearest_food_place_id(agent),
        )

    def step(self) -> list[SimulationEvent]:
        for agent in self.world.agents:
            agent.needs.apply_passive_decay(self.world.rules.needs)

        events: list[SimulationEvent] = []
        for agent in self.world.agents:
            perception = self.build_perception(agent)
            intent = agent.decide_action(perception, self.world.rules)
            _, event = self.world.execute_action(agent, intent)
            self.logger.record(event)
            events.append(event)

        self.world.advance_time()
        return events

    def run(self, steps: int) -> list[SimulationEvent]:
        all_events: list[SimulationEvent] = []
        for _ in range(max(0, steps)):
            all_events.extend(self.step())
        return all_events
