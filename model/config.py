from __future__ import annotations

from dataclasses import dataclass, field


def _ensure_int(name: str, value: int, minimum: int = 0) -> None:
    if int(value) != value:
        raise ValueError(f"{name} 必須是整數，目前為 {value!r}")
    if value < minimum:
        raise ValueError(f"{name} 必須大於等於 {minimum}，目前為 {value!r}")


def _ensure_float(name: str, value: float, minimum: float = 0.0) -> None:
    try:
        numeric_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必須是數值，目前為 {value!r}") from exc
    if numeric_value < minimum:
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
    min_value: float = 0.0
    max_value: float = 100.0
    initial_hunger: float = 35.0
    initial_energy: float = 80.0
    initial_mood: float = 70.0
    hunger_decay_per_tick: float = 0.1
    energy_decay_per_tick: float = 0.01
    mood_decay_per_tick: float = 0.05
    eat_hunger_recovery: float = 50.0
    rest_energy_recovery: float = 0.02
    social_mood_recovery: float = 0.12
    work_hunger_decay: float = 0.0
    work_energy_decay: float = 0.0
    move_energy_decay: float = 0.0

    def __post_init__(self) -> None:
        _ensure_float("NeedConfig.min_value", self.min_value, 0.0)
        _ensure_float("NeedConfig.max_value", self.max_value, self.min_value + 1.0)

        numeric_fields = {
            "initial_hunger": self.initial_hunger,
            "initial_energy": self.initial_energy,
            "initial_mood": self.initial_mood,
            "hunger_decay_per_tick": self.hunger_decay_per_tick,
            "energy_decay_per_tick": self.energy_decay_per_tick,
            "mood_decay_per_tick": self.mood_decay_per_tick,
            "eat_hunger_recovery": self.eat_hunger_recovery,
            "rest_energy_recovery": self.rest_energy_recovery,
            "social_mood_recovery": self.social_mood_recovery,
            "work_hunger_decay": self.work_hunger_decay,
            "work_energy_decay": self.work_energy_decay,
            "move_energy_decay": self.move_energy_decay,
        }
        for field_name, field_value in numeric_fields.items():
            _ensure_float(f"NeedConfig.{field_name}", field_value, 0.0)

        initial_values = [self.initial_hunger, self.initial_energy, self.initial_mood]
        if any(value < self.min_value or value > self.max_value for value in initial_values):
            raise ValueError("NeedConfig 的初始值必須落在 min_value 與 max_value 範圍內。")


@dataclass
class WorldConfig:
    width: int = 120
    height: int = 120
    interaction_radius: float = 18.0
    move_step: float = 8.0
    starting_minute: int = 8 * 60
    tick_minutes: int = 1

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
    workplace_food_reward: int = 2
    eat_threshold: float = 50.0
    rest_threshold: float = 10.0
    social_start_threshold: float = 80.0
    social_stop_threshold: float = 95.0
    social_affinity_gain_active: int = 10
    social_affinity_gain_passive: int = 5
    affinity_birth_threshold: int = 100
    initial_health: float = 100.0
    critical_need_threshold: float = 1.0
    critical_health_loss_per_tick: float = 1.0
    passive_health_loss_per_tick: float = 0.0000002
    work_start_minute: int = 9 * 60
    work_end_minute: int = 17 * 60

    def __post_init__(self) -> None:
        int_fields = {
            "agent_count": self.agent_count,
            "initial_food_per_agent": self.initial_food_per_agent,
            "workplace_food_reward": self.workplace_food_reward,
            "social_affinity_gain_active": self.social_affinity_gain_active,
            "social_affinity_gain_passive": self.social_affinity_gain_passive,
            "affinity_birth_threshold": self.affinity_birth_threshold,
            "work_start_minute": self.work_start_minute,
            "work_end_minute": self.work_end_minute,
        }
        for field_name, field_value in int_fields.items():
            _ensure_int(f"PopulationConfig.{field_name}", field_value, 0)

        float_fields = {
            "eat_threshold": self.eat_threshold,
            "rest_threshold": self.rest_threshold,
            "social_start_threshold": self.social_start_threshold,
            "social_stop_threshold": self.social_stop_threshold,
            "initial_health": self.initial_health,
            "critical_need_threshold": self.critical_need_threshold,
            "critical_health_loss_per_tick": self.critical_health_loss_per_tick,
            "passive_health_loss_per_tick": self.passive_health_loss_per_tick,
        }
        for field_name, field_value in float_fields.items():
            _ensure_float(f"PopulationConfig.{field_name}", field_value, 0.0)

        if self.agent_count < 2:
            raise ValueError("PopulationConfig.agent_count 至少要是 2，才能形成多代理人系統。")
        if self.work_start_minute >= 24 * 60 or self.work_end_minute >= 24 * 60:
            raise ValueError("PopulationConfig 的工作時間必須落在單日範圍內。")
        if self.social_stop_threshold < self.social_start_threshold:
            raise ValueError("PopulationConfig.social_stop_threshold 不可小於 social_start_threshold。")


@dataclass
class SimulationConfig:
    """管理者可調參數的唯一設定來源。"""

    logging: LoggingConfig = field(default_factory=LoggingConfig)
    needs: NeedConfig = field(default_factory=NeedConfig)
    world: WorldConfig = field(default_factory=WorldConfig)
    population: PopulationConfig = field(default_factory=PopulationConfig)


def build_default_config() -> SimulationConfig:
    return SimulationConfig()
