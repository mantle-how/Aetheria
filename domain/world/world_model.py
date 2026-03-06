from __future__ import annotations

from dataclasses import dataclass, field
from math import dist

from domain.agent.agent_model import ABMAgent
from domain.agent.need import NeedState
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
    _born_pairs: set[tuple[int, int]] = field(init=False, repr=False, default_factory=set)

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
        if not agent.is_alive:
            return []

        search_radius = self.rules.world.interaction_radius if radius is None else radius
        nearby_agents: list[ABMAgent] = []
        for other in self.agents:
            if not other.is_alive:
                continue
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
        if not agent.is_alive:
            return agent.x, agent.y

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

    def execute_action(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, list[SimulationEvent]]:
        if not agent.is_alive:
            return self._single_event_result(
                agent,
                intent,
                False,
                f"{agent.name} 已死亡，無法執行動作。",
            )

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

    def _execute_move(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, list[SimulationEvent]]:
        target_x = agent.x if intent.target_x is None else intent.target_x
        target_y = agent.y if intent.target_y is None else intent.target_y
        previous_position = (agent.x, agent.y)
        new_position = self.move_agent_towards(agent, target_x, target_y)
        message = (
            f"{agent.name} 從 ({previous_position[0]:.1f}, {previous_position[1]:.1f}) "
            f"移動到 ({new_position[0]:.1f}, {new_position[1]:.1f})。"
        )
        return self._single_event_result(agent, intent, True, message)

    def _execute_eat(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, list[SimulationEvent]]:
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

        return self._single_event_result(agent, intent, success, message)

    def _execute_rest(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, list[SimulationEvent]]:
        agent.needs.recover_from_rest(self.rules.needs)
        if agent.rest_hunger_baseline is not None:
            agent.needs.hunger = agent.rest_hunger_baseline
        if agent.rest_mood_baseline is not None:
            agent.needs.mood = agent.rest_mood_baseline
        agent.needs.normalize(self.rules.needs)

        rest_home_ids = [agent.home_place_id, *agent.parent_home_place_ids]
        is_resting_at_home = any(
            place_id and self.is_agent_at_place(agent, place_id)
            for place_id in rest_home_ids
        )
        if is_resting_at_home:
            message = f"{agent.name} 在住家休息。"
        else:
            message = f"{agent.name} 在外休息。"
        return self._single_event_result(agent, intent, True, message)

    def _execute_work(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, list[SimulationEvent]]:
        if not self.is_agent_at_place(agent, agent.work_place_id):
            message = f"{agent.name} 不在工作地點，無法開始工作。"
            return self._single_event_result(agent, intent, False, message)

        agent.needs.apply_work_cost(self.rules.needs)
        agent.food_inventory += self.rules.population.workplace_food_reward
        message = f"{agent.name} 完成工作，獲得 {self.rules.population.workplace_food_reward} 份食物。"
        return self._single_event_result(agent, intent, True, message)

    def _execute_socialize(
        self,
        agent: ABMAgent,
        intent: ActionIntent,
    ) -> tuple[ActionOutcome, list[SimulationEvent]]:
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
            return self._single_event_result(agent, intent, False, message)

        partner = min(nearby_agents, key=lambda nearby_agent: (nearby_agent.needs.mood, nearby_agent.agent_id))
        agent.needs.recover_from_social(self.rules.needs)
        partner.needs.recover_from_social(self.rules.needs)
        agent.relationships.record_positive_interaction(
            partner.agent_id,
            self.rules.population.social_affinity_gain_active,
        )
        partner.relationships.record_positive_interaction(
            agent.agent_id,
            self.rules.population.social_affinity_gain_passive,
        )
        cooldown_until = self.tick_count + agent.SOCIAL_COOLDOWN_TICKS
        agent.social_cooldown_until_tick = max(agent.social_cooldown_until_tick, cooldown_until)
        partner.social_cooldown_until_tick = max(partner.social_cooldown_until_tick, cooldown_until)

        message = f"{agent.name} 與 {partner.name} 進行社交互動。"
        outcome, action_event = self._build_result(agent, intent, True, message)
        events = [action_event]

        birth_event = self._maybe_birth_event(agent, partner)
        if birth_event is not None:
            events.append(birth_event)

        return outcome, events

    def _execute_idle(self, agent: ABMAgent, intent: ActionIntent) -> tuple[ActionOutcome, list[SimulationEvent]]:
        message = f"{agent.name} 暫時待命。"
        return self._single_event_result(agent, intent, True, message)

    def _single_event_result(
        self,
        agent: ABMAgent,
        intent: ActionIntent,
        success: bool,
        message: str,
    ) -> tuple[ActionOutcome, list[SimulationEvent]]:
        outcome, event = self._build_result(agent, intent, success, message)
        return outcome, [event]

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
            "health": round(agent.health, 6),
            "is_alive": agent.is_alive,
            "death_tick": agent.death_tick,
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

    def _maybe_birth_event(self, agent: ABMAgent, partner: ABMAgent) -> SimulationEvent | None:
        pair_key = self._pair_key(agent.agent_id, partner.agent_id)
        if pair_key in self._born_pairs:
            return None

        affinity_threshold = float(self.rules.population.affinity_birth_threshold)
        if agent.relationships.affinity_for(partner.agent_id) < affinity_threshold:
            return None
        if partner.relationships.affinity_for(agent.agent_id) < affinity_threshold:
            return None

        self._born_pairs.add(pair_key)
        child = self._create_child(agent, partner)
        return SimulationEvent(
            tick=self.tick_count,
            minute_of_day=self.minute_of_day,
            actor_id=agent.agent_id,
            event_type="birth",
            message=f"{agent.name} 與 {partner.name} 生下了 {child.name}。",
            payload={
                "parent_a": agent.agent_id,
                "parent_b": partner.agent_id,
                "child_id": child.agent_id,
                "child_position": {"x": round(child.x, 2), "y": round(child.y, 2)},
            },
        )

    def _create_child(self, parent_a: ABMAgent, parent_b: ABMAgent) -> ABMAgent:
        child_id = self._next_agent_id()
        child_x, child_y = self.rules.clamp_position(
            (parent_a.x + parent_b.x) / 2.0,
            (parent_a.y + parent_b.y) / 2.0,
        )
        parent_home_place_ids = tuple(
            place_id
            for place_id in (parent_a.home_place_id, parent_b.home_place_id)
            if place_id in self.places
        )
        child_home_place_id = self._select_place_id(
            *parent_home_place_ids,
            kind="home",
        )
        child_work_place_id = self._select_place_id(
            parent_a.work_place_id,
            parent_b.work_place_id,
            kind="work",
        )
        child_social_place_id = self._select_place_id(
            parent_a.social_place_id,
            parent_b.social_place_id,
            kind="social",
        )
        child = ABMAgent(
            agent_id=child_id,
            name=f"Agent_{child_id}",
            x=child_x,
            y=child_y,
            occupation="newborn",
            home_place_id=child_home_place_id,
            work_place_id=child_work_place_id,
            social_place_id=child_social_place_id,
            needs=NeedState.from_config(self.rules.needs),
            food_inventory=0,
            health=self.rules.population.initial_health,
            is_alive=True,
            parent_home_place_ids=parent_home_place_ids,
        )
        self.agents.append(child)
        self._agent_index[child.agent_id] = child
        return child

    def _next_agent_id(self) -> int:
        if not self._agent_index:
            return 1
        return max(self._agent_index) + 1

    @staticmethod
    def _pair_key(agent_a_id: int, agent_b_id: int) -> tuple[int, int]:
        return (agent_a_id, agent_b_id) if agent_a_id < agent_b_id else (agent_b_id, agent_a_id)

    @staticmethod
    def _parse_agent_id(raw_value: str) -> int | None:
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _select_place_id(self, *preferred_ids: str, kind: str | None = None) -> str:
        for place_id in preferred_ids:
            if place_id and place_id in self.places:
                place = self.places[place_id]
                if kind is None or place.kind == kind:
                    return place_id

        if kind is not None:
            for place in self.places.values():
                if place.kind == kind:
                    return place.place_id

        if self.places:
            return next(iter(self.places))

        raise ValueError("世界中沒有可用地點。")
