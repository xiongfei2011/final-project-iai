"""Game state and construction from a validated map layout."""

from dataclasses import dataclass, field, replace
from pathlib import Path

from .. import config
from .actions import Direction
from .entities import Base, Bullet, Position, Tank, Wall
from .map_loader import MapLayout, load_map


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
    # Agent snapshots use this as their perspective, not as a live turn lock.
    current_turn: int
    # Draw these final positions for one tick without treating them as active shots.
    expired_bullet_positions: tuple[Position, ...] = field(
        default=(), compare=False, repr=False
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


def create_initial_state(map_path: str | Path | None = None) -> GameState:
    path = config.DEFAULT_MAP_PATH if map_path is None else map_path
    return create_state_from_layout(load_map(path))


def create_state_from_layout(layout: MapLayout) -> GameState:
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

    return GameState(
        game_map=GameMap(height=layout.height, width=layout.width, walls=walls),
        tanks=tanks,
        bullets=[],
        bases=bases,
        current_turn=config.FIRST_PLAYER,
    )
