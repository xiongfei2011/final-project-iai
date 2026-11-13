from dataclasses import dataclass
from typing import NamedTuple

from ..config import BULLET_MAX_RANGE, DAMAGE_PER_HIT
from .actions import Direction


class Position(NamedTuple):
    row: int
    column: int

    def moved(self, direction: Direction) -> "Position":
        dr, dc = direction.delta
        return Position(self.row + dr, self.column + dc)


@dataclass(kw_only=True)
class Damageable:
    position: Position
    hp: int

    @property
    def is_destroyed(self) -> bool:
        return self.hp <= 0

    def take_hit(self, damage: int = DAMAGE_PER_HIT) -> None:
        self.hp = max(0, self.hp - damage)


@dataclass(kw_only=True)
class Tank(Damageable):
    direction: Direction


@dataclass(kw_only=True)
class Base(Damageable):
    ...


@dataclass(kw_only=True)
class Wall(Damageable):
    ...


@dataclass(kw_only=True)
class Bullet:

    position: Position
    direction: Direction
    steps_left: int = BULLET_MAX_RANGE
    owner: int | None = None

    def next_position(self) -> Position:
        return self.position.moved(self.direction)
