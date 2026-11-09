# Initial HP
TANK_INITIAL_HP = 6
BASE_INITIAL_HP = 9
WALL_INITIAL_HP = 3 

# Max bullet steps per turn
BULLET_STEPS_PER_TURN = 3

# Tank actions
MOVE_UP = "MOVE_UP"
MOVE_DOWN = "MOVE_DOWN"
MOVE_LEFT = "MOVE_LEFT"
MOVE_RIGHT = "MOVE_RIGHT"
FIRE = "FIRE"
STAY = "STAY"

# Offsets as (row, column)
MOVE_DELTAS = {
    MOVE_UP: (-1, 0),
    MOVE_DOWN: (1, 0),
    MOVE_LEFT: (0, -1),
    MOVE_RIGHT: (0, 1),
}

