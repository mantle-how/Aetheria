from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from domain.agent.need import NeedState
from domain.agent.relationship import RelationshipLedger
from model.action import ActionIntent, ActionType

if TYPE_CHECKING:
    from domain.simulation.perception import AgentPerception
    from domain.world.rule import WorldRules


@dataclass
class ABMAgent:
    """ABM 模擬中使用的核心代理人。"""

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

    @property
    def entity_id(self) -> int:
        """提供給舊版視覺化層的相容欄位。"""

        return self.agent_id

    def decide_action(self, perception: "AgentPerception", rules: "WorldRules") -> ActionIntent:
        """用清楚且可預測的 ABM 規則決定下一步行動。"""

        if self.needs.hunger >= rules.population.high_hunger_threshold:
            if self.food_inventory > 0 or perception.current_place_has_food:
                return ActionIntent(
                    action_type=ActionType.EAT,
                    note="飢餓值過高，先處理進食。",
                )
            return self._move_to_place(
                perception,
                perception.nearest_food_place_id or self.home_place_id,
                "前往可取得食物的地點。",
            )

        if self.needs.energy <= rules.population.low_energy_threshold:
            if perception.current_place_id == self.home_place_id:
                return ActionIntent(
                    action_type=ActionType.REST,
                    note="精力不足，在家休息。",
                )
            return self._move_to_place(
                perception,
                self.home_place_id,
                "返回住處恢復精力。",
            )

        if self.needs.mood <= rules.population.low_mood_threshold:
            social_target = self._pick_social_target(perception)
            if social_target is not None:
                return ActionIntent(
                    action_type=ActionType.SOCIALIZE,
                    target_id=str(social_target.agent_id),
                    note="心情偏低，尋找社交互動。",
                )
            return self._move_to_place(
                perception,
                self.social_place_id,
                "前往社交空間。",
            )

        if rules.is_work_time(perception.minute_of_day):
            if perception.current_place_id == self.work_place_id:
                return ActionIntent(
                    action_type=ActionType.WORK,
                    note="目前處於工作時段。",
                )
            return self._move_to_place(
                perception,
                self.work_place_id,
                "前往工作地點。",
            )

        social_target = self._pick_social_target(perception)
        if social_target is not None and perception.current_place_id == self.social_place_id:
            return ActionIntent(
                action_type=ActionType.SOCIALIZE,
                target_id=str(social_target.agent_id),
                note="空檔時間用來維持社交連結。",
            )

        if perception.current_place_id != self.social_place_id:
            return self._move_to_place(
                perception,
                self.social_place_id,
                "沒有緊急需求，前往廣場活動。",
            )

        return ActionIntent(
            action_type=ActionType.IDLE,
            note="目前狀態穩定，暫時待命。",
        )

    def _move_to_place(
        self,
        perception: "AgentPerception",
        place_id: str,
        note: str,
    ) -> ActionIntent:
        """建立前往指定地點的移動意圖；若地點不存在則改為待命。"""

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
        """從附近代理人中優先挑選關係最佳者，否則取編號最小者。"""

        if not perception.nearby_agents:
            return None

        candidate_ids = [candidate.agent_id for candidate in perception.nearby_agents]
        preferred_id = self.relationships.strongest_bond(candidate_ids)
        if preferred_id is not None:
            for candidate in perception.nearby_agents:
                if candidate.agent_id == preferred_id:
                    return candidate

        return min(perception.nearby_agents, key=lambda candidate: candidate.agent_id)
