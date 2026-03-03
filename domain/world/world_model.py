from __future__ import annotations

from dataclasses import dataclass, field
from math import dist

from domain.agent.agent_model import ABMAgent
from domain.event.base import SimulationEvent
from domain.world.place import Place
from domain.world.rule import WorldRules
from model.action import ActionIntent, ActionOutcome, ActionType


@dataclass
class SimulationWorld:
    """持有可變世界狀態，並負責結算代理人行動。"""

    places: dict[str, Place]
    agents: list[ABMAgent]
    rules: WorldRules
    tick_count: int = 0
    minute_of_day: int = 0
    _agent_index: dict[int, ABMAgent] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._agent_index = {}
        for agent in self.agents:
            if agent.agent_id in self._agent_index:
                raise ValueError(f"代理人編號重複: {agent.agent_id}")
            self._agent_index[agent.agent_id] = agent

        missing_places = [
            place_id
            for agent in self.agents
            for place_id in (agent.home_place_id, agent.work_place_id, agent.social_place_id)
            if place_id not in self.places
        ]
        if missing_places:
            raise ValueError(f"缺少地點定義: {sorted(set(missing_places))}")

    def current_place_for(self, agent: ABMAgent) -> Place | None:
        closest_place: Place | None = None
        closest_distance: float | None = None

        for place in self.places.values():
            distance_to_place = place.distance_to(agent.x, agent.y)
            if closest_distance is None or distance_to_place < closest_distance:
                closest_place = place
                closest_distance = distance_to_place

        if closest_place is None or closest_distance is None:
            return None
        if closest_distance > self.rules.arrival_radius:
            return None
        return closest_place

    def is_agent_at_place(self, agent: ABMAgent, place_id: str) -> bool:
        place = self.places.get(place_id)
        if place is None:
            return False
        return place.distance_to(agent.x, agent.y) <= self.rules.arrival_radius

    def get_agents_near(self, agent: ABMAgent, radius: float | None = None) -> list[ABMAgent]:
        search_radius = self.rules.world.interaction_radius if radius is None else radius
        nearby_agents: list[ABMAgent] = []
        for other in self.agents:
            if other.agent_id == agent.agent_id:
                continue
            if dist((agent.x, agent.y), (other.x, other.y)) <= search_radius:
                nearby_agents.append(other)
        return nearby_agents

    def nearest_food_place_id(self, agent: ABMAgent) -> str | None:
        food_places = [place for place in self.places.values() if place.has_food()]
        if not food_places:
            return None
        nearest = min(food_places, key=lambda place: place.distance_to(agent.x, agent.y))
        return nearest.place_id

    def move_agent_towards(self, agent: ABMAgent, target_x: float, target_y: float) -> tuple[float, float]:
        step = self.rules.world.move_step
        delta_x = target_x - agent.x
        delta_y = target_y - agent.y
        distance_to_target = dist((agent.x, agent.y), (target_x, target_y))

        if distance_to_target == 0:
            return agent.x, agent.y

        if distance_to_target <= step:
            next_x = target_x
            next_y = target_y
        else:
            ratio = step / distance_to_target
            next_x = agent.x + (delta_x * ratio)
            next_y = agent.y + (delta_y * ratio)

        clamped_x, clamped_y = self.rules.clamp_position(next_x, next_y)
        agent.x = clamped_x
        agent.y = clamped_y
        agent.needs.apply_move_cost(self.rules.needs)
        return agent.x, agent.y

    def execute_action(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, SimulationEvent]:
        if intent.action_type == ActionType.MOVE:
            return self._execute_move(agent, intent)
        if intent.action_type == ActionType.EAT:
            return self._execute_eat(agent, intent)
        if intent.action_type == ActionType.REST:
            return self._execute_rest(agent, intent)
        if intent.action_type == ActionType.WORK:
            return self._execute_work(agent, intent)
        if intent.action_type == ActionType.SOCIALIZE:
            return self._execute_socialize(agent, intent)
        return self._execute_idle(agent, intent)

    def advance_time(self) -> None:
        self.tick_count += 1
        self.minute_of_day = (self.minute_of_day + self.rules.world.tick_minutes) % 1440

    def _execute_move(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, SimulationEvent]:
        target_x = agent.x if intent.target_x is None else intent.target_x
        target_y = agent.y if intent.target_y is None else intent.target_y
        previous_position = (agent.x, agent.y)
        new_position = self.move_agent_towards(agent, target_x, target_y)
        message = (
            f"{agent.name} 從 ({previous_position[0]:.1f}, {previous_position[1]:.1f}) "
            f"移動到 ({new_position[0]:.1f}, {new_position[1]:.1f})。"
        )
        return self._build_result(agent, intent, True, message)

    def _execute_eat(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, SimulationEvent]:
        source = "隨身存糧"
        success = False

        if agent.food_inventory > 0:
            agent.food_inventory -= 1
            success = True
        else:
            current_place = self.current_place_for(agent)
            if current_place is not None and current_place.consume_food():
                source = current_place.name
                success = True

        if success:
            agent.needs.recover_from_eating(self.rules.needs)
            message = f"{agent.name} 使用 {source} 進食。"
        else:
            message = f"{agent.name} 想進食，但目前沒有食物可用。"

        return self._build_result(agent, intent, success, message)

    def _execute_rest(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, SimulationEvent]:
        if self.is_agent_at_place(agent, agent.home_place_id):
            agent.needs.recover_from_rest(self.rules.needs)
            message = f"{agent.name} 在家中休息。"
            return self._build_result(agent, intent, True, message)

        agent.needs.recover_from_rest(self.rules.needs, multiplier=0.5)
        message = f"{agent.name} 在外短暫休息。"
        return self._build_result(agent, intent, True, message)

    def _execute_work(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, SimulationEvent]:
        if not self.is_agent_at_place(agent, agent.work_place_id):
            message = f"{agent.name} 不在工作地點，無法開始工作。"
            return self._build_result(agent, intent, False, message)

        agent.needs.apply_work_cost(self.rules.needs)
        agent.food_inventory += self.rules.population.workplace_food_reward
        message = f"{agent.name} 完成工作，獲得 {self.rules.population.workplace_food_reward} 份食物。"
        return self._build_result(agent, intent, True, message)

    def _execute_socialize(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, SimulationEvent]:
        nearby_agents = self.get_agents_near(agent)
        if intent.target_id is not None:
            desired_target = self._parse_agent_id(intent.target_id)
            nearby_agents = [
                nearby_agent
                for nearby_agent in nearby_agents
                if nearby_agent.agent_id == desired_target
            ]

        if not nearby_agents:
            message = f"{agent.name} 想互動，但附近沒有合適對象。"
            return self._build_result(agent, intent, False, message)

        partner = min(nearby_agents, key=lambda nearby_agent: nearby_agent.agent_id)
        gain = self.rules.population.social_affinity_gain
        decay = self.rules.population.social_affinity_loss

        agent.needs.recover_from_social(self.rules.needs)
        partner.needs.recover_from_social(self.rules.needs, multiplier=0.5)
        agent.relationships.record_positive_interaction(partner.agent_id, gain)
        partner.relationships.record_positive_interaction(agent.agent_id, gain)

        for other_agent in self.get_agents_near(agent):
            if other_agent.agent_id != partner.agent_id:
                agent.relationships.record_negative_interaction(other_agent.agent_id, decay)

        message = f"{agent.name} 與 {partner.name} 進行社交互動。"
        return self._build_result(agent, intent, True, message)

    def _execute_idle(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, SimulationEvent]:
        message = f"{agent.name} 暫時待命。"
        return self._build_result(agent, intent, True, message)

    def _build_result(
        self,
        agent: ABMAgent,
        intent: ActionIntent,
        success: bool,
        message: str,
    ) -> tuple[ActionOutcome, SimulationEvent]:
        agent.last_action = intent.action_type
        state_changes = {
            "position": {"x": round(agent.x, 2), "y": round(agent.y, 2)},
            "needs": agent.needs.as_dict(),
            "food_inventory": agent.food_inventory,
        }
        outcome = ActionOutcome(
            agent_id=agent.agent_id,
            action_type=intent.action_type,
            success=success,
            summary=message,
            state_changes=state_changes,
        )
        event = SimulationEvent(
            tick=self.tick_count,
            minute_of_day=self.minute_of_day,
            actor_id=agent.agent_id,
            event_type=intent.action_type.value,
            message=message,
            payload={
                "success": success,
                "note": intent.note,
                **state_changes,
            },
        )
        return outcome, event

    @staticmethod
    def _parse_agent_id(raw_value: str) -> int | None:
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None
