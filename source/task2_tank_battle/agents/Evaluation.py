from collections import deque

from ..config import BULLET_STEPS_PER_TURN, MOVE_DELTAS, STAY
from ..game.Rules import GameRules


THREAT_WEIGHT = 4
FIRING_POSITION_WEIGHT = 1
DODGE_WEIGHT = 1


def evaluate(state, max_player):
    min_player = 1 - max_player

    max_player_hp = state.tanks[max_player]["hp"] + state.bases[max_player]["hp"]
    min_player_hp = state.tanks[min_player]["hp"] + state.bases[min_player]["hp"]
    hp_diff = max_player_hp - min_player_hp

    rules = GameRules()
    after_stay = state
    if state.bullets and not rules.terminal_test(state):
        # Khi đạt độ sâu giới hạn nhưng trên bàn đấu vẫn còn đạn thì sẽ tính tiếp 1 bước nữa để dự đoán chính xác hơn
        after_stay = rules.result(state, STAY)

    bullet_targets = set()
    for bullet in state.bullets:
        row, col = bullet["position"]
        dr, dc = MOVE_DELTAS["MOVE_" + bullet["direction"]]
        bullet_targets.add((row + dr, col + dc))

    max_in_danger = _in_danger(state, max_player, after_stay.bases, bullet_targets)
    min_in_danger = _in_danger(state, min_player, after_stay.bases, bullet_targets)
    threat_diff = int(min_in_danger) - int(max_in_danger)

    firing_diff = _firing_position_score(state, max_player) - _firing_position_score(
        state, min_player
    )

    dodge_diff = 0.0
    player_to_move = state.current_turn
    if after_stay.tanks[player_to_move]["hp"] < state.tanks[player_to_move]["hp"]:
        safe_moves = count_dodges(state, rules, after_stay)
        dodge_risk = 1 - safe_moves / len(MOVE_DELTAS)
        dodge_diff = -dodge_risk if player_to_move == max_player else dodge_risk

    score = (
        hp_diff
        + THREAT_WEIGHT * threat_diff
        + FIRING_POSITION_WEIGHT * firing_diff
        + DODGE_WEIGHT * dodge_diff
    )
    score_scale = 16 + THREAT_WEIGHT + FIRING_POSITION_WEIGHT + DODGE_WEIGHT
    return score / score_scale


def _firing_position_score(state, player):
    if has_clear_shot(state, player):
        return 1.0

    distance = distance_to_clear_shot(state, player)
    if distance is None:
        return 0.0
    return 1 / (1 + distance)


def _in_danger(state, player, projected_bases, bullet_targets):
    if state.bases[player]["hp"] > 0 and projected_bases[player]["hp"] == 0:
        return True

    tank = state.tanks[player]
    return (
        state.current_turn != player
        and tank["hp"] == 1
        and tank["position"] in bullet_targets
    )


def has_clear_shot(state, player):
    tank = state.tanks[player]
    return _has_clear_shot_from(state, player, tank["position"], tank["direction"])


def _has_clear_shot_from(state, player, position, direction):
    opponent = 1 - player
    opponent_base = state.bases[opponent]
    if state.tanks[player]["hp"] <= 0 or opponent_base["hp"] <= 0:
        return False

    row, col = position
    dr, dc = MOVE_DELTAS["MOVE_" + direction]
    height = state.game_map["height"]
    width = state.game_map["width"]
    blocking_positions = {
        state.tanks[opponent]["position"],
        state.bases[player]["position"],
    }

    for step in range(1, BULLET_STEPS_PER_TURN + 1):
        next_row = row + dr * step
        next_col = col + dc * step
        if not (1 <= next_row <= height and 1 <= next_col <= width):
            return False

        target = (next_row, next_col)
        if state.walls.get(target, 0) > 0:
            return False
        if target == opponent_base["position"]:
            return True
        if target in blocking_positions:
            return False

    return False


def distance_to_clear_shot(state, player):
    opponent = 1 - player
    tank = state.tanks[player]
    if tank["hp"] <= 0 or state.bases[opponent]["hp"] <= 0:
        return None

    start = (tank["position"], tank["direction"])
    queue = deque([(start, 0)])
    visited = {start}
    height = state.game_map["height"]
    width = state.game_map["width"]
    occupied = {
        state.tanks[opponent]["position"],
        state.bases[player]["position"],
        state.bases[opponent]["position"],
    }

    while queue:
        (position, direction), distance = queue.popleft()
        if _has_clear_shot_from(state, player, position, direction):
            return distance

        row, col = position
        for action, (dr, dc) in MOVE_DELTAS.items():
            next_row, next_col = row + dr, col + dc
            if not (1 <= next_row <= height and 1 <= next_col <= width):
                continue

            target = (next_row, next_col)
            if target in occupied or state.walls.get(target, 0) > 0:
                continue

            next_node = (target, action.removeprefix("MOVE_"))
            if next_node in visited:
                continue

            visited.add(next_node)
            queue.append((next_node, distance + 1))

    return None


def count_dodges(state, rules, after_stay):
    player = state.current_turn
    current_hp = state.tanks[player]["hp"]

    if after_stay.tanks[player]["hp"] == current_hp:
        return 0

    dodges = 0
    for action in rules.actions(state):
        if action in MOVE_DELTAS:
            after_move = rules.result(state, action)
            if after_move.tanks[player]["hp"] == current_hp:
                dodges += 1

    return dodges
