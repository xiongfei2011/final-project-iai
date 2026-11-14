from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import NamedTuple

from .. import config
from .actions import Direction
from .entities import Base, Bullet, Position, Tank, Wall
from .map_loader import MapLayout, MapLoader


class GameStateKey(NamedTuple):
    dimensions: tuple[int, int]
    current_turn: int
    tanks: tuple[tuple[int, Position, Direction, int], ...]
    bases: tuple[tuple[int, Position, int], ...]
    walls: tuple[tuple[Position, int], ...]
    bullets: tuple[tuple[Position, str, int, int], ...]


class BulletFlight(NamedTuple):
    start: Position
    end: Position
    owner: int | None


@dataclass
class GameMap:

    height: int
    width: int
    walls: dict[Position, Wall]

    def in_bounds(self, position: Position) -> bool:
        return 1 <= position.row <= self.height and 1 <= position.column <= self.width

    def wall_at(self, position: Position) -> Wall | None:
        wall = self.walls.get(position)
        if wall is None or wall.is_destroyed:
            return None
        return wall


@dataclass
class GameState:

    game_map: GameMap
    tanks: dict[int, Tank]
    bullets: list[Bullet]
    bases: dict[int, Base]
    current_turn: int
    bullet_flights: tuple[BulletFlight, ...] = field(default=(), compare=False, repr=False)
    played_states: frozenset[GameStateKey] = field(
        default_factory=frozenset, compare=False, repr=False
    )
    previous_action: str | None = field(default=None, compare=False, repr=False)

    def search_key(self) -> GameStateKey:
        return GameStateKey(
            dimensions=(self.game_map.height, self.game_map.width),
            current_turn=self.current_turn,
            tanks=tuple(
                (player, tank.position, tank.direction, tank.hp)
                for player, tank in sorted(self.tanks.items())
            ),
            bases=tuple(
                (player, base.position, base.hp)
                for player, base in sorted(self.bases.items())
            ),
            walls=tuple(sorted(
                (position, wall.hp) for position, wall in self.game_map.walls.items()
            )),
            bullets=tuple(sorted(
                (bullet.position, bullet.direction.value, bullet.steps_left,
                 bullet.owner if bullet.owner is not None else -1)
                for bullet in self.bullets
            )),
        )

    def clone(self) -> "GameState":
        walls = {
            position: replace(wall) for position, wall in self.game_map.walls.items()
        }
        return replace(
            self,
            game_map=replace(self.game_map, walls=walls),
            tanks={player: replace(tank) for player, tank in self.tanks.items()},
            bases={player: replace(base) for player, base in self.bases.items()},
            bullets=[replace(bullet) for bullet in self.bullets],
        )

    @classmethod
    def from_map(cls, map_path: str | Path | None = None) -> "GameState":
        path = config.DEFAULT_MAP_PATH if map_path is None else map_path
        return cls.from_layout(MapLoader.load(path))

    @classmethod
    def from_layout(cls, layout: MapLayout) -> "GameState":
        tanks = {
            player: Tank(
                position=Position(*position),
                direction=Direction(config.INITIAL_TANK_DIRECTIONS[player]),
                hp=config.TANK_INITIAL_HP,
            )
            for player, position in enumerate(layout.tank_positions)
        }

        bases = {
            player: Base(position=Position(*position), hp=config.BASE_INITIAL_HP)
            for player, position in enumerate(layout.base_positions)
        }

        wall_positions = (Position(*position) for position in layout.wall_positions)
        walls = {
            position: Wall(position=position, hp=config.WALL_INITIAL_HP)
            for position in wall_positions
        }

        return cls(
            game_map=GameMap(height=layout.height, width=layout.width, walls=walls),
            tanks=tanks,
            bullets=[],
            bases=bases,
            current_turn=config.FIRST_PLAYER,
        )


create_initial_state = GameState.from_map
create_state_from_layout = GameState.from_layout
