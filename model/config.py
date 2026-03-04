from __future__ import annotations

from dataclasses import dataclass, field


def _ensure_int(name: str, value: int, minimum: int = 0) -> None:
    if int(value) != value:
        raise ValueError(f"{name} 必須是整數，目前為 {value!r}")
    if value < minimum:
        raise ValueError(f"{name} 必須大於等於 {minimum}，目前為 {value!r}")


def _ensure_float(name: str, value: float, minimum: float = 0.0) -> None:
    if float(value) < minimum:
        raise ValueError(f"{name} 必須大於等於 {minimum}，目前為 {value!r}")


@dataclass
class LoggingConfig:
    enabled: bool = True
    print_to_stdout: bool = True
    max_events: int = 500

    def __post_init__(self) -> None:
        _ensure_int("LoggingConfig.max_events", self.max_events, 1)


@dataclass
class NeedConfig:
    min_value: int = 0
    max_value: int = 100
    initial_hunger: int = 35
    initial_energy: int = 80
    initial_mood: int = 70
    hunger_growth_per_tick: int = 1
    energy_loss_per_tick: int = 1
    mood_loss_per_tick: int = 1
    eat_hunger_recovery: int = 35
    rest_energy_recovery: int = 20
    social_mood_recovery: int = 12
    work_hunger_cost: int = 6
    work_energy_cost: int = 8
    move_energy_cost: int = 2

    def __post_init__(self) -> None:
        _ensure_int("NeedConfig.min_value", self.min_value, 0)
        _ensure_int("NeedConfig.max_value", self.max_value, self.min_value + 1)

        numeric_fields = {
            "initial_hunger": self.initial_hunger,
            "initial_energy": self.initial_energy,
            "initial_mood": self.initial_mood,
            "hunger_growth_per_tick": self.hunger_growth_per_tick,
            "energy_loss_per_tick": self.energy_loss_per_tick,
            "mood_loss_per_tick": self.mood_loss_per_tick,
            "eat_hunger_recovery": self.eat_hunger_recovery,
            "rest_energy_recovery": self.rest_energy_recovery,
            "social_mood_recovery": self.social_mood_recovery,
            "work_hunger_cost": self.work_hunger_cost,
            "work_energy_cost": self.work_energy_cost,
            "move_energy_cost": self.move_energy_cost,
        }
        for field_name, field_value in numeric_fields.items():
            _ensure_int(f"NeedConfig.{field_name}", field_value, 0)

        initial_values = [self.initial_hunger, self.initial_energy, self.initial_mood]
        if any(value > self.max_value for value in initial_values):
            raise ValueError("NeedConfig 的初始值必須落在 max_value 範圍內。")


@dataclass
class WorldConfig:
    width: int = 120
    height: int = 120
    interaction_radius: float = 18.0
    move_step: float = 8.0
    starting_minute: int = 8 * 60
    tick_minutes: int = 30

    def __post_init__(self) -> None:
        _ensure_int("WorldConfig.width", self.width, 10)
        _ensure_int("WorldConfig.height", self.height, 10)
        _ensure_float("WorldConfig.interaction_radius", self.interaction_radius, 1.0)
        _ensure_float("WorldConfig.move_step", self.move_step, 0.1)
        _ensure_int("WorldConfig.starting_minute", self.starting_minute, 0)
        _ensure_int("WorldConfig.tick_minutes", self.tick_minutes, 1)

        if self.starting_minute >= 24 * 60:
            raise ValueError("WorldConfig.starting_minute 必須落在單日範圍內。")


@dataclass
class PopulationConfig:
    agent_count: int = 5
    initial_food_per_agent: int = 2
    workplace_food_reward: int = 1
    social_affinity_gain: int = 8
    social_affinity_loss: int = 1
    low_energy_threshold: int = 30
    high_hunger_threshold: int = 65
    low_mood_threshold: int = 40
    work_start_minute: int = 9 * 60
    work_end_minute: int = 17 * 60

    def __post_init__(self) -> None:
        numeric_fields = {
            "agent_count": self.agent_count,
            "initial_food_per_agent": self.initial_food_per_agent,
            "workplace_food_reward": self.workplace_food_reward,
            "social_affinity_gain": self.social_affinity_gain,
            "social_affinity_loss": self.social_affinity_loss,
            "low_energy_threshold": self.low_energy_threshold,
            "high_hunger_threshold": self.high_hunger_threshold,
            "low_mood_threshold": self.low_mood_threshold,
            "work_start_minute": self.work_start_minute,
            "work_end_minute": self.work_end_minute,
        }
        for field_name, field_value in numeric_fields.items():
            _ensure_int(f"PopulationConfig.{field_name}", field_value, 0)

        if self.agent_count < 2:
            raise ValueError("PopulationConfig.agent_count 至少要是 2，才能形成多代理人系統。")
        if self.work_start_minute >= 24 * 60 or self.work_end_minute >= 24 * 60:
            raise ValueError("PopulationConfig 的工作時間必須落在單日範圍內。")


@dataclass
class SimulationConfig:
    """管理者可調參數的唯一設定來源。"""

    logging: LoggingConfig = field(default_factory=LoggingConfig)
    needs: NeedConfig = field(default_factory=NeedConfig)
    world: WorldConfig = field(default_factory=WorldConfig)
    population: PopulationConfig = field(default_factory=PopulationConfig)


def build_default_config() -> SimulationConfig:
    return SimulationConfig()
