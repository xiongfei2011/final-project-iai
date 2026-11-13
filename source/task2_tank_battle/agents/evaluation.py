"""Heuristic evaluation for nonterminal tank battle positions."""

from collections import deque
from dataclasses import dataclass
from typing import Protocol

from ..config import (
    BULLET_MAX_RANGE,
    DAMAGE_PER_HIT,
    DODGE_WEIGHT,
    FIRING_POSITION_WEIGHT,
    HEURISTIC_SCORE_SCALE,
    TANK_SHOT_WEIGHT,
    THREAT_WEIGHT,
    BASE_ALARM_RADIUS,
    BASE_NORMAL_WEIGHT,
    BASE_ALARM_WEIGHT,
)
from ..game.actions import MOVE_ACTIONS, Action, Direction
from ..game.entities import Position, Bullet
from ..game.rules import GameRules
from ..game.state import GameMap, GameState


class Evaluator(Protocol):

    def evaluate(self, state: GameState, max_player: int) -> float: ...


@dataclass(frozen=True)
class EvaluationWeights:

    threat: float = THREAT_WEIGHT
    firing_position: float = FIRING_POSITION_WEIGHT
    dodge: float = DODGE_WEIGHT
    score_scale: float = HEURISTIC_SCORE_SCALE
    tank_shot: float = TANK_SHOT_WEIGHT


class HeuristicEvaluator:

    def __init__(
        self, rules: GameRules, weights: EvaluationWeights = EvaluationWeights()
    ) -> None:
        self._rules = rules
        self._weights = weights

    def evaluate(self, state: GameState, max_player: int) -> float:
        min_player = 1 - max_player

        max_base_pressure = self._base_pressure(state, max_player)
        min_base_pressure = self._base_pressure(state, min_player)
        defense_score = min_base_pressure - max_base_pressure

        after_stay = state
        if state.bullets and not self._rules.terminal_test(state):
            after_stay = self._rules.result_tick(state, {})

        hp_diff = self._hp_diff(state, max_player, min_player)
        threat_diff = self._threat_diff(state, after_stay, max_player, min_player)
        firing_diff = self._firing_diff(state, max_player, min_player)
        dodge_diff = self._dodge_diff(state, after_stay, max_player)
        tank_shot_diff = int(self._has_clear_tank_shot(state, max_player)) - int(
            self._has_clear_tank_shot(state, min_player)
        )

        score = (
            hp_diff
            + self._weights.threat * threat_diff
            + self._weights.firing_position * firing_diff
            + self._weights.dodge * dodge_diff
            + self._weights.tank_shot * tank_shot_diff
            + defense_score
        )
        return score / self._weights.score_scale

    @staticmethod
    def _hp_diff(state: GameState, max_player: int, min_player: int) -> int:
        max_hp = state.tanks[max_player].hp + state.bases[max_player].hp
        min_hp = state.tanks[min_player].hp + state.bases[min_player].hp
        return max_hp - min_hp

    def _threat_diff(
        self, state: GameState, after_stay: GameState, max_player: int, min_player: int
    ) -> int:
        max_in_danger = self._in_danger(state, after_stay, max_player)
        min_in_danger = self._in_danger(state, after_stay, min_player)
        return int(min_in_danger) - int(max_in_danger)

    def _firing_diff(self, state: GameState, max_player: int, min_player: int) -> float:
        max_score = self._firing_position_score(state, max_player)
        min_score = self._firing_position_score(state, min_player)
        return max_score - min_score

    def _dodge_diff(
        self, state: GameState, after_stay: GameState, max_player: int
    ) -> float:

        max_risk = self._dodge_risk(state, after_stay, max_player)
        min_risk = self._dodge_risk(state, after_stay, 1 - max_player)

        dodge_diff = min_risk - max_risk
        return dodge_diff

    def _dodge_risk(
        self, state: GameState, after_stay: GameState, player: int
    ) -> float:

        tank = after_stay.tanks[player]
        lost_hp = tank.hp < state.tanks[player].hp

        still_in_danger = any(
            self._bullet_can_reach(after_stay, bullet, tank.position)
            for bullet in after_stay.bullets
        )

        if not lost_hp and not still_in_danger:
            return 0.0

        safe_moves = self._count_dodges(state, player)
        return 1 - safe_moves / len(MOVE_ACTIONS)

    @staticmethod
    def _in_danger(
        state: GameState,
        after_stay: GameState,
        player: int,
    ) -> bool:
        if state.bases[player].hp > 0 and after_stay.bases[player].hp == 0:
            return True

        return state.tanks[player].hp > 0 and after_stay.tanks[player].is_destroyed

    def _firing_position_score(self, state: GameState, player: int) -> float:
        cost = self._base_attack_cost(state, player)
        if cost is None:
            return 0.0
        return 1 / (1 + cost)

    def _has_clear_tank_shot(self, state: GameState, player: int) -> bool:
        shooter = state.tanks[player]
        target = state.tanks[1 - player]
        if shooter.is_destroyed or target.is_destroyed:
            return False

        wall_shots = self._shots_to_clear_line(
            state.game_map,
            shooter.position,
            shooter.direction,
            target.position,
            {base.position for base in state.bases.values()},
        )
        return wall_shots == 0

    def _base_attack_cost(self, state: GameState, player: int) -> int | None:
        opponent = 1 - player
        tank = state.tanks[player]
        target_base = state.bases[opponent]
        if tank.is_destroyed or target_base.is_destroyed:
            return None

        start = (tank.position, tank.direction)
        queue = deque([(start, 0)])
        visited = {start}
        board = state.game_map
        occupied = {
            state.tanks[opponent].position,
            state.bases[player].position,
            target_base.position,
        }
        best_cost = None

        while queue:
            (position, direction), distance = queue.popleft()
            # Remaining firing positions need at least this many moves.
            if best_cost is not None and distance >= best_cost:
                return best_cost

            wall_shots = self._shots_to_clear_line(
                board, position, direction, target_base.position, occupied
            )
            if wall_shots == 0:
                return distance
            if wall_shots is not None:
                cost = distance + wall_shots
                best_cost = cost if best_cost is None else min(best_cost, cost)

            for action in MOVE_ACTIONS:
                next_direction = action.direction
                if next_direction is None:
                    continue
                target = position.moved(next_direction)
                if not board.in_bounds(target):
                    continue
                if target in occupied or board.wall_at(target) is not None:
                    target = position

                next_node = (target, next_direction)
                if next_node in visited:
                    continue

                visited.add(next_node)
                queue.append((next_node, distance + 1))

        return best_cost

    @staticmethod
    def _shots_to_clear_line(
        board: GameMap,
        position: Position,
        direction: Direction,
        target_position: Position,
        occupied: set[Position],
    ) -> int | None:
        """Count shots needed to clear walls on a viable firing line."""
        target = position
        shots = 0
        for _ in range(BULLET_MAX_RANGE):
            target = target.moved(direction)
            if not board.in_bounds(target):
                return None

            wall = board.wall_at(target)
            if wall is not None:
                shots += (wall.hp + DAMAGE_PER_HIT - 1) // DAMAGE_PER_HIT
            if target == target_position:
                return shots
            if target in occupied:
                return None

        return None

    def _count_dodges(self, state: GameState, player: int) -> int:
        current_hp = state.tanks[player].hp
        dodges = 0
        for action in self._rules.actions(state, player):
            if not Action(action).is_move:
                continue

            after_move = self._rules.result_tick(state, {player: action})
            tank = after_move.tanks[player]

            if tank.hp < current_hp:
                continue

            still_in_danger = any(
                self._bullet_can_reach(after_move, bullet, tank.position)
                for bullet in after_move.bullets
            )

            if not still_in_danger:
                dodges += 1

        return dodges

    def _base_distances(self, state: GameState, player: int) -> dict[Position, int]:
        base_position = state.bases[player].position
        distances = {base_position: 0}
        queue = deque([base_position])
        board = state.game_map

        while queue:
            current = queue.popleft()

            for direction in Direction:
                neighbor = current.moved(direction)
                if (
                    not board.in_bounds(neighbor)
                    or board.wall_at(neighbor) is not None
                    or neighbor in distances
                ):
                    continue

                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)

        return distances

    def _base_pressure(self, state: GameState, player: int) -> float:
        enemy_position = state.tanks[1 - player].position
        distance = self._base_distances(state, player).get(enemy_position)

        if distance is None:
            return 0.0

        weight = (
            BASE_ALARM_WEIGHT if distance <= BASE_ALARM_RADIUS else BASE_NORMAL_WEIGHT
        )

        return weight / (1 + distance)

    def _bullet_can_reach(
        self, state: GameState, bullet: Bullet, target: Position
    ) -> bool:
        row_offset = target.row - bullet.position.row
        col_offset = target.column - bullet.position.column
        distance = abs(row_offset) + abs(col_offset)
        dr, dc = bullet.direction.delta

        if distance == 0 or distance > bullet.steps_left:
            return False

        if (row_offset, col_offset) != (dr * distance, dc * distance):
            return False

        board = state.game_map
        occupied = {tank.position for tank in state.tanks.values()}
        occupied.update(base.position for base in state.bases.values())

        position = bullet.position

        for _ in range(distance):
            position = position.moved(bullet.direction)

            if not board.in_bounds(position) or board.wall_at(position) is not None:
                return False
            if position == target:
                return True
            if position in occupied:
                return False

        return False
