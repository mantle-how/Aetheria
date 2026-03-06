from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationEvent:
    """每次代理人行動結算後產生的事件。"""

    tick: int
    minute_of_day: int
    actor_id: int | None
    event_type: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_log_line(self) -> str:
        hour = self.minute_of_day // 60
        minute = self.minute_of_day % 60
        actor = "系統" if self.actor_id is None else f"代理:{self.actor_id}"
        event_label = {
            "move": "移動",
            "eat": "進食",
            "rest": "休息",
            "work": "工作",
            "socialize": "社交",
            "idle": "待命",
            "birth": "誕生",
            "death": "死亡",
        }.get(self.event_type, self.event_type)
        return f"[步次={self.tick:03d} 時間={hour:02d}:{minute:02d} {actor} {event_label}] {self.message}"
