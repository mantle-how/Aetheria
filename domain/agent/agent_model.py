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
    social_cooldown_until_tick: int = 0

    @property
    def entity_id(self) -> int:
        """提供給視覺層使用的相容欄位。"""

        return self.agent_id

    def decide_action(self, perception: "AgentPerception", rules: "WorldRules") -> ActionIntent:
        """依照需求門檻與社交規則決定下一步。"""

        if not self.is_alive:
            return ActionIntent(
                action_type=ActionType.IDLE,
                note="代理人已死亡，無法行動。",
            )

        self._refresh_social_flag(rules)

        if self.needs.energy < rules.population.rest_threshold:
            if perception.current_place_id == self.home_place_id:
                return ActionIntent(
                    action_type=ActionType.REST,
                    note="精力低於門檻，優先休息。",
                )
            return self._move_to_place(
                perception,
                self.home_place_id,
                "精力低於門檻，前往住處休息。",
            )

        if self.needs.hunger < rules.population.eat_threshold:
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

        if self.is_socializing_until_recovered:
            return self._recover_mood_routine(
                perception=perception,
                rules=rules,
                socialize_note="心情低落中，持續社交恢復。",
                move_note="心情低落中，前往社交空間。",
                idle_note="心情低落中，在社交空間等待互動。",
            )

        return self._stable_routine(perception, rules)

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
        self.social_cooldown_until_tick = 0
        return True

    def _refresh_social_flag(self, rules: "WorldRules") -> None:
        if self.needs.mood < rules.population.social_start_threshold:
            self.is_socializing_until_recovered = True
            return

        if (
            self.is_socializing_until_recovered
            and self.needs.mood > rules.population.social_stop_threshold
        ):
            self.is_socializing_until_recovered = False

    def _recover_mood_routine(
        self,
        perception: "AgentPerception",
        rules: "WorldRules",
        socialize_note: str,
        move_note: str,
        idle_note: str,
    ) -> ActionIntent:
        if perception.current_place_id != self.social_place_id:
            return self._move_to_place(
                perception,
                self.social_place_id,
                move_note,
            )

        if perception.tick < self.social_cooldown_until_tick:
            return ActionIntent(
                action_type=ActionType.IDLE,
                note="社交冷卻中，暫時等待。",
            )

        target = self._pick_social_target(perception)
        if target is None:
            return ActionIntent(
                action_type=ActionType.IDLE,
                note=idle_note,
            )

        if dist((self.x, self.y), (target.x, target.y)) <= rules.world.interaction_radius:
            return ActionIntent(
                action_type=ActionType.SOCIALIZE,
                target_id=str(target.agent_id),
                note=socialize_note,
            )

        return ActionIntent(
            action_type=ActionType.MOVE,
            target_id=str(target.agent_id),
            target_x=target.x,
            target_y=target.y,
            note="心情低落中，接近可社交對象。",
        )

    def _stable_routine(self, perception: "AgentPerception", rules: "WorldRules") -> ActionIntent:
        if rules.is_work_time(perception.minute_of_day):
            if perception.current_place_id == self.work_place_id:
                return ActionIntent(
                    action_type=ActionType.WORK,
                    note="需求穩定，工作時段執行工作。",
                )
            return self._move_to_place(
                perception,
                self.work_place_id,
                "需求穩定，前往工作站。",
            )

        if perception.current_place_id != self.home_place_id:
            return self._move_to_place(
                perception,
                self.home_place_id,
                "需求穩定，返回住家待命。",
            )

        return ActionIntent(
            action_type=ActionType.IDLE,
            note="需求穩定，於住家待命。",
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
        """優先從附近代理人中挑選心情值最低者，避免全員追逐同一目標。"""

        if not perception.nearby_agents:
            return None

        candidates = [
            candidate
            for candidate in perception.nearby_agents
            if candidate.agent_id != self.agent_id and candidate.is_alive
        ]
        if not candidates:
            return None

        return min(candidates, key=lambda candidate: (candidate.needs.mood, candidate.agent_id))
