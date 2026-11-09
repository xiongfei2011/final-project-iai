from copy import deepcopy

from .. import config


class GameRules:
    MOVE_DELTAS = config.MOVE_DELTAS
    
    def actions(self, state):
        entities = list(state.tanks.values()) + list(state.bases.values())
        if self.terminal_test(state):
            return []

        height = state.game_map["height"]
        width = state.game_map["width"]
        pos_x, pos_y = state.tanks[state.current_turn]["position"]

        blocked = {position for position, hp in state.walls.items() if hp > 0}
        blocked.update(entity["position"] for entity in entities)

        legal_actions = [config.FIRE, config.STAY]

        for action, (x, y) in self.MOVE_DELTAS.items():
            next_pos_x, next_pos_y = pos_x + x, pos_y + y
            if 1 <= next_pos_x <= height and 1 <= next_pos_y <= width and (next_pos_x, next_pos_y) not in blocked:
                legal_actions.append(action)

        return legal_actions
        
    def terminal_test(self, state):
        entities = list(state.tanks.values()) + list(state.bases.values())
        return any(entity["hp"] <= 0 for entity in entities)
    
    def utility(self, state, player):
        opponent = 1 - player
        
        player_lost = (state.tanks[player]["hp"] <= 0
                        or state.bases[player]["hp"] <= 0)
        
        opponent_lost = (state.tanks[opponent]["hp"] <= 0
                        or state.bases[opponent]["hp"] <=0)

        if player_lost and opponent_lost:
            return 0
        
        return -1 if player_lost else 1
    
    def result(self, state, action):
        if action not in self.actions(state):
            raise ValueError(f"Invalid action: {action}")

        next_state = deepcopy(state)
        self._apply_action(next_state, action)

        for _ in range(3):
            if not next_state.bullets:
                break
            self._advance_bullets_one_step(next_state)
            if self.terminal_test(next_state):
                return next_state

        next_state.current_turn = 1 - next_state.current_turn
        return next_state

    def _apply_action(self, state, action):
        tank = state.tanks[state.current_turn]

        if action in self.MOVE_DELTAS:
            r, c = tank["position"]
            dr, dc = self.MOVE_DELTAS[action]
            tank["position"] = (r + dr, c + dc)
            tank["direction"] = action.removeprefix("MOVE_")
        elif action == config.FIRE:
            state.bullets.append({
                "position": tank["position"],
                "direction": tank["direction"],
            })

    def _advance_bullets_one_step(self, state):
        height = state.game_map["height"]
        width = state.game_map["width"]
        targets = {}

        for kind, group in (("tank", state.tanks), ("base", state.bases)):
            for player, entity in group.items():
                targets[entity["position"]] = (kind, player)

        hits = []
        remaining_bullets = []

        for bullet in state.bullets:
            r, c = bullet["position"]
            move = "MOVE_" + bullet["direction"]
            dr, dc = self.MOVE_DELTAS[move]
            next_r, next_c = r + dr, c + dc

            if not (1 <= next_r <= height and 1 <= next_c <= width):
                continue

            target = (next_r, next_c)
            if state.walls.get(target, 0) > 0:
                hits.append(("wall", target))
            elif target in targets:
                hits.append(targets[target])
            else:
                bullet["position"] = target
                remaining_bullets.append(bullet)

        for kind, key in hits:
            if kind == "wall":
                state.walls[key] = max(0, state.walls[key] - 1)
            else:
                group = state.tanks if kind == "tank" else state.bases
                entity = group[key]
                entity["hp"] = max(0, entity["hp"] - 1)

        state.bullets = remaining_bullets
