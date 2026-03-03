from __future__ import annotations

from dataclasses import dataclass

from model.config import SimulationConfig


@dataclass(frozen=True)
class WorldRules:
    """由共用設定推導出的純規則輔助類別。"""

    config: SimulationConfig

    @property
    def world(self):
        return self.config.world

    @property
    def needs(self):
        return self.config.needs

    @property
    def population(self):
        return self.config.population

    @property
    def arrival_radius(self) -> float:
        return max(1.0, self.world.move_step / 2.0)

    def is_work_time(self, minute_of_day: int) -> bool:
        start = self.population.work_start_minute
        end = self.population.work_end_minute
        if start <= end:
            return start <= minute_of_day < end
        return minute_of_day >= start or minute_of_day < end

    def clamp_position(self, x: float, y: float) -> tuple[float, float]:
        clamped_x = max(0.0, min(float(self.world.width), float(x)))
        clamped_y = max(0.0, min(float(self.world.height), float(y)))
        return clamped_x, clamped_y
