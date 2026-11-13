from enum import Enum


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    @property
    def delta(self) -> tuple[int, int]:
        return _DIRECTION_DELTAS[self]


_DIRECTION_DELTAS = {
    Direction.UP: (-1, 0),
    Direction.DOWN: (1, 0),
    Direction.LEFT: (0, -1),
    Direction.RIGHT: (0, 1),
}


class Action(str, Enum):
    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    FIRE = "FIRE"
    STAY = "STAY"

    @property
    def direction(self) -> Direction | None:
        return _ACTION_DIRECTIONS.get(self)

    @property
    def is_move(self) -> bool:
        return self in _ACTION_DIRECTIONS


_ACTION_DIRECTIONS = {
    Action.MOVE_UP: Direction.UP,
    Action.MOVE_DOWN: Direction.DOWN,
    Action.MOVE_LEFT: Direction.LEFT,
    Action.MOVE_RIGHT: Direction.RIGHT,
}

MOVE_ACTIONS = tuple(_ACTION_DIRECTIONS)