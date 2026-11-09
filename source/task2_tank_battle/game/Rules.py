class GameRules:
    
    def actions(self, state):
        entities = list(state.tanks.values()) + list(state.bases.values())
        if any(entity["hp"] <= 0 for entity in entities):
            return []

        height = state.game_map["height"]
        width = state.game_map["width"]
        pos_x, pos_y = state.tanks[state.current_turn]["position"]

        blocked = {position for position, hp in state.walls.items() if hp > 0}
        blocked.update(entity["position"] for entity in entities)

        legal_actions = ["FIRE", "STAY"]
        directions = {
            "MOVE_UP": (-1, 0),
            "MOVE_DOWN": (1, 0),
            "MOVE_LEFT": (0, -1),
            "MOVE_RIGHT": (0, 1),
        }

        for action, (x, y) in directions.items():
            next_pos_x, next_pos_y = pos_x + x, pos_y + y
            if 1 <= next_pos_x <= height and 1 <= next_pos_y <= width:
                if (next_pos_x, next_pos_y) not in blocked:
                    legal_actions.append(action)

        return legal_actions
        
        