from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    MOVE = "move"
    EAT = "eat"
    REST = "rest"
    WORK = "work"
    SOCIALIZE = "socialize"
    IDLE = "idle"


@dataclass
class ActionIntent:
    """代理人在世界結算前提出的行動意圖。"""

    action_type: ActionType
    target_id: str | None = None
    target_x: float | None = None
    target_y: float | None = None
    note: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionOutcome:
    """世界完成結算後產生的行動結果。"""

    agent_id: int
    action_type: ActionType
    success: bool
    summary: str
    state_changes: dict[str, Any] = field(default_factory=dict)
