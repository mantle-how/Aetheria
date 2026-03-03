from __future__ import annotations

from dataclasses import dataclass

from model.config import NeedConfig


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


@dataclass
class NeedState:
    """代理人在模擬中維護的基本需求狀態。"""

    hunger: int
    energy: int
    mood: int

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
        self.hunger += config.hunger_growth_per_tick
        self.energy -= config.energy_loss_per_tick
        self.mood -= config.mood_loss_per_tick
        self.normalize(config)

    def apply_work_cost(self, config: NeedConfig) -> None:
        self.hunger += config.work_hunger_cost
        self.energy -= config.work_energy_cost
        self.normalize(config)

    def apply_move_cost(self, config: NeedConfig) -> None:
        self.energy -= config.move_energy_cost
        self.normalize(config)

    def recover_from_eating(self, config: NeedConfig) -> None:
        self.hunger -= config.eat_hunger_recovery
        self.normalize(config)

    def recover_from_rest(self, config: NeedConfig, multiplier: float = 1.0) -> None:
        energy_gain = int(round(config.rest_energy_recovery * multiplier))
        mood_gain = int(round(config.social_mood_recovery * 0.3 * multiplier))
        self.energy += energy_gain
        self.mood += mood_gain
        self.normalize(config)

    def recover_from_social(self, config: NeedConfig, multiplier: float = 1.0) -> None:
        mood_gain = int(round(config.social_mood_recovery * multiplier))
        self.mood += mood_gain
        self.normalize(config)

    def as_dict(self) -> dict[str, int]:
        return {
            "hunger": self.hunger,
            "energy": self.energy,
            "mood": self.mood,
        }
