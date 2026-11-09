from ..config import TANK_INITIAL_HP, BASE_INITIAL_HP, WALL_INITIAL_HP


def create_initial_state():
    tanks = {
        0: {"position": (2, 1), "direction": "RIGHT", "hp": TANK_INITIAL_HP},
        1: {"position": (5, 5), "direction": "LEFT", "hp": TANK_INITIAL_HP},
    }

    bases = {
        0: {"position": (1, 3), "hp": BASE_INITIAL_HP},
        1: {"position": (5, 3), "hp": BASE_INITIAL_HP},
    }

    wall_positions = [(3, 1), (1, 2), (5, 2), (3, 3), (1, 4), (5, 4), (3, 5)]
    walls = {position: WALL_INITIAL_HP for position in wall_positions}

    return GameState(
        game_map={"height": 5, "width": 5},
        tanks=tanks,
        bullets=[],
        walls=walls,
        bases=bases,
        current_turn=0,
    )


class GameState:

    def __init__(self, game_map, tanks, bullets, walls, bases, current_turn):
        self.game_map = game_map
        self.tanks = tanks
        self.bullets = bullets
        self.walls = walls
        self.bases = bases
        self.current_turn = current_turn
