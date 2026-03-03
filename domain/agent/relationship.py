from __future__ import annotations

from dataclasses import dataclass, field


def _clamp_affinity(value: int) -> int:
    return max(-100, min(100, int(value)))


@dataclass
class Relationship:
    """描述兩名代理人之間的一條社會連結。"""

    other_agent_id: int
    affinity: int = 0
    interactions: int = 0

    def reinforce(self, gain: int) -> None:
        self.affinity = _clamp_affinity(self.affinity + gain)
        self.interactions += 1

    def decay(self, loss: int) -> None:
        self.affinity = _clamp_affinity(self.affinity - loss)


@dataclass
class RelationshipLedger:
    """管理單一代理人的所有社會關係。"""

    links: dict[int, Relationship] = field(default_factory=dict)

    def get_or_create(self, other_agent_id: int) -> Relationship:
        relation = self.links.get(other_agent_id)
        if relation is None:
            relation = Relationship(other_agent_id=other_agent_id)
            self.links[other_agent_id] = relation
        return relation

    def affinity_for(self, other_agent_id: int) -> int:
        relation = self.links.get(other_agent_id)
        return 0 if relation is None else relation.affinity

    def record_positive_interaction(self, other_agent_id: int, gain: int) -> None:
        self.get_or_create(other_agent_id).reinforce(gain)

    def record_negative_interaction(self, other_agent_id: int, loss: int) -> None:
        self.get_or_create(other_agent_id).decay(loss)

    def strongest_bond(self, candidate_ids: list[int]) -> int | None:
        ranked_candidates = [candidate_id for candidate_id in candidate_ids if candidate_id in self.links]
        if not ranked_candidates:
            return None

        return max(
            ranked_candidates,
            key=lambda candidate_id: (
                self.links[candidate_id].affinity,
                -candidate_id,
            ),
        )
