"""Heuristic evaluation for nonterminal tank battle positions."""

from collections import deque
from dataclasses import dataclass
from math import ceil
from typing import Protocol

from ..config import (
    BASE_ALARM_RADIUS,
    BASE_ALARM_WEIGHT,
    BASE_DEFENSE_MAX_MOVES,
    BASE_DEFENSE_WEIGHT,
    BASE_NORMAL_WEIGHT,
    BULLET_MAX_RANGE,
    DAMAGE_PER_HIT,
    DODGE_WEIGHT,
    FIRING_POSITION_WEIGHT,
    HEURISTIC_SCORE_SCALE,
    TANK_SHOT_WEIGHT,
    THREAT_WEIGHT,
)
from ..game.actions import MOVE_ACTIONS, Action, Direction
from ..game.entities import Damageable, Position
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
    base_defense: float = BASE_DEFENSE_WEIGHT


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

        # Simulate each opponent firing while the defending tank stays in place.
        max_enemy_fire = self._enemy_fire_actions(state, max_player)
        min_enemy_fire = self._enemy_fire_actions(state, min_player)
        max_after_fire = self._after_enemy_fire(state, max_enemy_fire)
        min_after_fire = self._after_enemy_fire(state, min_enemy_fire)

        hp_diff = self._hp_diff(state, max_player, min_player)

        threat_diff = int(self._in_danger(state, min_after_fire, min_player)) - int(
            self._in_danger(state, max_after_fire, max_player)
        )

        max_base_cost = self._base_attack_cost(state, max_player)
        min_base_cost = self._base_attack_cost(state, min_player)
        firing_diff = (
            self._firing_position_score(max_base_cost)
            - self._firing_position_score(min_base_cost)
        )

        dodge_diff = self._dodge_risk(
            state, min_after_fire, min_player, min_enemy_fire
        ) - self._dodge_risk(state, max_after_fire, max_player, max_enemy_fire)

        max_can_shoot_tank = self._has_clear_tank_shot(state, max_player)
        min_can_shoot_tank = self._has_clear_tank_shot(state, min_player)
        tank_shot_diff = int(max_can_shoot_tank) - int(min_can_shoot_tank)

        if max_can_shoot_tank and min_can_shoot_tank:
            defense_score *= 0.5
        if self._weights.base_defense:
            defense_score += self._weights.base_defense * (
                self._counterattack_score(state, max_player, max_base_cost, max_enemy_fire)
                - self._counterattack_score(state, min_player, min_base_cost, min_enemy_fire)
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

    def _enemy_fire_actions(self, state: GameState, player: int) -> dict[int, str]:
        enemy = 1 - player
        if Action.FIRE in self._rules.actions(state, enemy):
            return {enemy: Action.FIRE.value}
        return {}

    def _after_enemy_fire(self, state: GameState, enemy_fire: dict[int, str]) -> GameState:
        if enemy_fire or (state.bullets and not self._rules.terminal_test(state)):
            return self._rules.result_tick(state, enemy_fire)
        return state

    def _dodge_risk(
        self, state: GameState, after_fire: GameState, player: int, enemy_fire: dict[int, str]
    ) -> float:
        if after_fire.tanks[player].hp >= state.tanks[player].hp:
            return 0.0

        safe_moves = self._count_dodges(state, player, enemy_fire)
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

    @staticmethod
    def _firing_position_score(cost: int | None) -> float:
        if cost is None:
            return 0.0
        return 1 / (1 + cost)

    def _counterattack_score(
        self,
        state: GameState,
        player: int,
        base_attack_cost: int | None,
        enemy_fire: dict[int, str],
    ) -> float:
        """Reward a reachable firing position when racing the enemy base is too slow."""
        opponent = 1 - player
        if opponent not in enemy_fire:
            return 0.0

        base = state.bases[player]
        enemy_base = state.bases[opponent]
        enemy_tank = state.tanks[opponent]
        shots_to_reach_base = self._shots_to_clear_line(
            state.game_map,
            enemy_tank.position,
            enemy_tank.direction,
            base.position,
            {enemy_base.position, state.tanks[player].position},
        )
        if shots_to_reach_base != 0:
            return 0.0

        # Estimate both races with the opposing tank in its current position.
        ticks_left = ceil(base.hp / DAMAGE_PER_HIT)
        if (
            base_attack_cost is not None
            and base_attack_cost + ceil(enemy_base.hp / DAMAGE_PER_HIT) <= ticks_left
        ):
            return 0.0

        shots_to_destroy_tank = ceil(enemy_tank.hp / DAMAGE_PER_HIT)
        max_moves = min(BASE_DEFENSE_MAX_MOVES, ticks_left - shots_to_destroy_tank)
        if max_moves < 0:
            return 0.0

        cost = self._attack_cost(state, player, enemy_tank, max_moves=max_moves)
        return self._firing_position_score(cost)

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
        return self._attack_cost(state, player, state.bases[1 - player])

    def _attack_cost(
        self,
        state: GameState,
        player: int,
        target_entity: Damageable,
        *,
        max_moves: int | None = None,
    ) -> int | None:
        opponent = 1 - player
        tank = state.tanks[player]
        if tank.is_destroyed or target_entity.is_destroyed:
            return None

        start = (tank.position, tank.direction)
        queue = deque([(start, 0)])
        visited = {start}
        board = state.game_map
        occupied = {
            state.tanks[opponent].position,
            state.bases[player].position,
            state.bases[opponent].position,
        }
        best_cost = None

        while queue:
            (position, direction), distance = queue.popleft()
            # Remaining firing positions need at least this many moves.
            if best_cost is not None and distance >= best_cost:
                return best_cost

            wall_shots = self._shots_to_clear_line(
                board, position, direction, target_entity.position, occupied
            )
            if wall_shots == 0:
                return distance
            if max_moves is not None and distance >= max_moves:
                continue
            if max_moves is None and wall_shots is not None:
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

    def _count_dodges(self, state: GameState, player: int, enemy_fire: dict[int, str]) -> int:
        current_hp = state.tanks[player].hp
        dodges = 0
        for action in self._rules.actions(state, player):
            if not Action(action).is_move:
                continue

            after_move = self._rules.result_tick(
                state, {**enemy_fire, player: action}
            )
            if after_move.tanks[player].hp == current_hp:
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
