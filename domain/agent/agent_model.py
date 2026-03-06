from __future__ import annotations

from dataclasses import dataclass, field
from math import dist
from typing import TYPE_CHECKING

from domain.agent.need import NeedState
from domain.agent.relationship import RelationshipLedger
from model.action import ActionIntent, ActionType

if TYPE_CHECKING:
    from domain.simulation.perception import AgentPerception
    from domain.world.rule import WorldRules


@dataclass
class ABMAgent:
    """ABM 模擬中的核心代理人。"""

    SOCIAL_COOLDOWN_TICKS: int = field(init=False, default=8, repr=False)

    agent_id: int
    name: str
    x: float
    y: float
    occupation: str
    home_place_id: str
    work_place_id: str
    social_place_id: str
    needs: NeedState
    food_inventory: int = 0
    relationships: RelationshipLedger = field(default_factory=RelationshipLedger)
    last_action: ActionType = ActionType.IDLE
    health: float = 100.0
    is_alive: bool = True
    death_tick: int | None = None
    is_socializing_until_recovered: bool = False
    is_resting_until_recovered: bool = False
    social_cooldown_until_tick: int = 0
    parent_home_place_ids: tuple[str, ...] = ()
    is_restocking_food: bool = False
    rest_hunger_baseline: float | None = None
    rest_mood_baseline: float | None = None

    @property
    def entity_id(self) -> int:
        """提供給視覺層使用的相容欄位。"""

        return self.agent_id

    def decide_action(self, perception: "AgentPerception", rules: "WorldRules") -> ActionIntent:
        """依照固定優先序決定下一步：進食 > 休息 > 補糧 > 社交 > 待命。"""

        if not self.is_alive:
            return ActionIntent(
                action_type=ActionType.IDLE,
                note="代理人已死亡，無法行動。",
            )

        self._refresh_social_flag(rules)
        self._refresh_restock_flag(rules)
        self._refresh_rest_flag(rules)

        if self.needs.hunger < rules.population.eat_threshold:
            return self._eat_routine(perception)

        if self.is_resting_until_recovered:
            return self._rest_routine(perception)

        if self.is_restocking_food:
            return self._restock_food_routine(perception)

        if self.is_socializing_until_recovered:
            return self._socialize_routine(perception, rules)

        return ActionIntent(
            action_type=ActionType.IDLE,
            note="需求穩定，維持待命。",
        )

    def apply_health_decay(self, rules: "WorldRules", tick: int) -> bool:
        """每 tick 扣生命值；回傳是否在本次 tick 死亡。"""

        if not self.is_alive:
            return False

        self.health -= rules.population.passive_health_loss_per_tick
        critical_threshold = rules.population.critical_need_threshold
        if (
            self.needs.hunger < critical_threshold
            or self.needs.energy < critical_threshold
            or self.needs.mood < critical_threshold
        ):
            self.health -= rules.population.critical_health_loss_per_tick

        if self.health > 0:
            return False

        self.health = 0.0
        self.is_alive = False
        self.death_tick = tick
        self.last_action = ActionType.IDLE
        self.is_socializing_until_recovered = False
        self.is_resting_until_recovered = False
        self.social_cooldown_until_tick = 0
        self.is_restocking_food = False
        return True

    def resolve_rest_home_place_id(self, place_positions: dict[str, tuple[float, float]]) -> str | None:
        """休息地點：自己住家優先，否則依序 fallback 父母住家。"""

        if self.home_place_id in place_positions:
            return self.home_place_id

        for place_id in self.parent_home_place_ids:
            if place_id and place_id in place_positions:
                return place_id

        return None

    def _refresh_social_flag(self, rules: "WorldRules") -> None:
        if self.needs.mood < rules.population.social_start_threshold:
            self.is_socializing_until_recovered = True
            return

        if (
            self.is_socializing_until_recovered
            and self.needs.mood > rules.population.social_stop_threshold
        ):
            self.is_socializing_until_recovered = False

    def _refresh_rest_flag(self, rules: "WorldRules") -> None:
        if self.needs.energy < rules.population.rest_threshold:
            self.is_resting_until_recovered = True
            return

        if (
            self.is_resting_until_recovered
            and self.needs.energy > rules.population.rest_stop_threshold
        ):
            self.is_resting_until_recovered = False

    def _refresh_restock_flag(self, rules: "WorldRules") -> None:
        threshold = rules.population.food_restock_threshold
        if self.food_inventory < threshold:
            self.is_restocking_food = True
        elif self.food_inventory >= threshold:
            self.is_restocking_food = False

    def _eat_routine(self, perception: "AgentPerception") -> ActionIntent:
        if self.food_inventory > 0 or perception.current_place_has_food:
            return ActionIntent(
                action_type=ActionType.EAT,
                note="飢餓低於門檻，優先進食。",
            )

        if perception.nearest_food_place_id is None:
            return ActionIntent(
                action_type=ActionType.IDLE,
                note="飢餓偏低，但目前找不到食物來源。",
            )

        return self._move_to_place(
            perception,
            perception.nearest_food_place_id,
            "飢餓低於門檻，前往最近可取得食物的地點。",
        )

    def _rest_routine(self, perception: "AgentPerception") -> ActionIntent:
        rest_home_place_id = self.resolve_rest_home_place_id(perception.place_positions)
        if rest_home_place_id is None:
            return ActionIntent(
                action_type=ActionType.REST,
                note="精力恢復中，但住家不存在，先原地休息。",
            )

        if perception.current_place_id == rest_home_place_id:
            return ActionIntent(
                action_type=ActionType.REST,
                note="精力恢復中，於住家持續休息。",
            )

        return self._move_to_place(
            perception,
            rest_home_place_id,
            "精力恢復中，返回住家持續休息。",
        )

    def _restock_food_routine(self, perception: "AgentPerception") -> ActionIntent:
        if perception.current_place_id == self.work_place_id:
            return ActionIntent(
                action_type=ActionType.WORK,
                note="食物庫存低於補糧門檻，執行工作補糧。",
            )

        return self._move_to_place(
            perception,
            self.work_place_id,
            "食物庫存低於補糧門檻，前往工作站補糧。",
        )

    def _socialize_routine(self, perception: "AgentPerception", rules: "WorldRules") -> ActionIntent:
        if perception.tick < self.social_cooldown_until_tick:
            return ActionIntent(
                action_type=ActionType.IDLE,
                note="社交冷卻中，暫時等待。",
            )

        target = self._pick_social_target(perception)
        if target is None:
            if perception.current_place_id == self.social_place_id:
                return ActionIntent(
                    action_type=ActionType.IDLE,
                    note="心情低落中，在社交空間等待互動。",
                )
            return self._move_to_place(
                perception,
                self.social_place_id,
                "心情低落中，前往社交空間。",
            )

        target_distance = dist((self.x, self.y), (target.x, target.y))
        if target_distance <= rules.world.interaction_radius:
            return ActionIntent(
                action_type=ActionType.SOCIALIZE,
                target_id=str(target.agent_id),
                note="心情低落中，進行社交恢復。",
            )

        return ActionIntent(
            action_type=ActionType.MOVE,
            target_id=str(target.agent_id),
            target_x=target.x,
            target_y=target.y,
            note="心情低落中，接近最低心情且閒置的對象。",
        )

    def _move_to_place(
        self,
        perception: "AgentPerception",
        place_id: str,
        note: str,
    ) -> ActionIntent:
        """建立移動意圖；若地點不存在則改為待命。"""

        coordinates = perception.place_positions.get(place_id)
        if coordinates is None:
            return ActionIntent(
                action_type=ActionType.IDLE,
                note=f"找不到目標地點：{place_id}",
            )

        return ActionIntent(
            action_type=ActionType.MOVE,
            target_id=place_id,
            target_x=coordinates[0],
            target_y=coordinates[1],
            note=note,
        )

    def _pick_social_target(self, perception: "AgentPerception") -> ABMAgent | None:
        """從其餘存活且閒置的代理人中挑選心情最低者。"""

        candidates = [
            candidate
            for candidate in perception.alive_agents
            if (
                candidate.agent_id != self.agent_id
                and candidate.is_alive
                and candidate.last_action == ActionType.IDLE
            )
        ]
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda candidate: (
                candidate.needs.mood,
                dist((self.x, self.y), (candidate.x, candidate.y)),
                candidate.agent_id,
            ),
        )
