from __future__ import annotations

from dataclasses import dataclass, field
from math import dist


@dataclass
class Place:
    """模擬世界中的固定地點。"""

    place_id: str
    name: str
    kind: str
    x: float
    y: float
    food_stock: int = 0
    tags: set[str] = field(default_factory=set)

    def distance_to(self, x: float, y: float) -> float:
        return dist((self.x, self.y), (x, y))

    def has_food(self) -> bool:
        return self.food_stock > 0

    def consume_food(self, amount: int = 1) -> bool:
        if amount <= 0:
            return False
        if self.food_stock < amount:
            return False
        self.food_stock -= amount
        return True

    def restock_food(self, amount: int = 1) -> None:
        if amount > 0:
            self.food_stock += amount
