from __future__ import annotations

from dataclasses import dataclass

from domain.simulation.config import NeedConfig


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(float(minimum), min(float(maximum), float(value)))


@dataclass
class NeedState:
    """代理人在模擬中維護的基本需求狀態。"""

    hunger: float
    energy: float
    mood: float

    @classmethod
    def from_config(cls, config: NeedConfig) -> "NeedState":
        return cls(
            hunger=config.initial_hunger,
            energy=config.initial_energy,
            mood=config.initial_mood,
        )

    def normalize(self, config: NeedConfig) -> None:
        self.hunger = _clamp(self.hunger, config.min_value, config.max_value)
        self.energy = _clamp(self.energy, config.min_value, config.max_value)
        self.mood = _clamp(self.mood, config.min_value, config.max_value)

    def apply_passive_decay(self, config: NeedConfig) -> None:
        self.hunger -= config.hunger_decay_per_tick
        self.energy -= config.energy_decay_per_tick
        self.mood -= config.mood_decay_per_tick
        self.normalize(config)

    def apply_work_cost(self, config: NeedConfig) -> None:
        self.hunger -= config.work_hunger_decay
        self.energy -= config.work_energy_decay
        self.normalize(config)

    def apply_move_cost(self, config: NeedConfig) -> None:
        self.energy -= config.move_energy_decay
        self.normalize(config)

    def recover_from_eating(self, config: NeedConfig) -> None:
        self.hunger += config.eat_hunger_recovery
        self.normalize(config)

    def recover_from_rest(self, config: NeedConfig, multiplier: float = 1.0) -> None:
        self.energy += config.rest_energy_recovery * multiplier
        self.normalize(config)

    def recover_from_social(self, config: NeedConfig, multiplier: float = 1.0) -> None:
        self.mood += config.social_mood_recovery * multiplier
        self.normalize(config)

    def as_dict(self) -> dict[str, float]:
        return {
            "hunger": self.hunger,
            "energy": self.energy,
            "mood": self.mood,
        }
