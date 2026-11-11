from ..config import MOVE_DELTAS


THREAT_WEIGHT = 4


def evaluate(state, max_player):
    min_player = 1 - max_player

    max_player_hp = state.tanks[max_player]["hp"] + state.bases[max_player]["hp"]
    min_player_hp = state.tanks[min_player]["hp"] + state.bases[min_player]["hp"]
    hp_diff = max_player_hp - min_player_hp

    bullet_targets = set()
    for bullet in state.bullets:
        row, col = bullet["position"]
        dr, dc = MOVE_DELTAS["MOVE_" + bullet["direction"]]
        bullet_targets.add((row + dr, col + dc))

    max_in_danger = _in_danger(state, max_player, bullet_targets)
    min_in_danger = _in_danger(state, min_player, bullet_targets)
    threat_diff = int(min_in_danger) - int(max_in_danger)

    return (hp_diff + THREAT_WEIGHT * threat_diff) / (16 + THREAT_WEIGHT)


def _in_danger(state, player, bullet_targets):
    base = state.bases[player]
    if base["hp"] == 1 and base["position"] in bullet_targets:
        return True

    tank = state.tanks[player]
    return (
        state.current_turn != player
        and tank["hp"] == 1
        and tank["position"] in bullet_targets
    )
