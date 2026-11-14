from pathlib import Path

from .game.actions import MOVE_ACTIONS, Action


# Compatibility for agents that import action constants from config.
FIRE = Action.FIRE.value
STAY = Action.STAY.value
MOVE_UP = Action.MOVE_UP.value
MOVE_DOWN = Action.MOVE_DOWN.value
MOVE_LEFT = Action.MOVE_LEFT.value
MOVE_RIGHT = Action.MOVE_RIGHT.value
MOVE_DELTAS = {
    action.value: direction.delta
    for action in MOVE_ACTIONS
    if (direction := action.direction) is not None
}


# Initial HP
TANK_INITIAL_HP = 6
BASE_INITIAL_HP = 9
WALL_INITIAL_HP = 3
DAMAGE_PER_HIT = 1

# A bullet can cover its full range in the tick when it is fired.
BULLET_MAX_RANGE = 3
BULLET_STEPS_PER_TURN = BULLET_MAX_RANGE  # Compatibility for partner agents.

# Opening board
MAPS_DIR = Path(__file__).with_name("maps")
DEFAULT_MAP_PATH = MAPS_DIR / "default.txt"
INITIAL_TANK_DIRECTIONS = ("RIGHT", "LEFT")
FIRST_PLAYER = 0

# Search and evaluation
MINIMAX_AGENT = "minimax"
ALPHA_BETA_AGENT = "alpha-beta"
HEURISTIC_AGENT = "heuristic"
HEURISTIC_ALPHA_BETA_AGENT = "heuristic-alpha-beta"
DEFAULT_AGENTS = (HEURISTIC_AGENT, HEURISTIC_ALPHA_BETA_AGENT)
DEFAULT_SEARCH_DEPTH = 3
THREAT_WEIGHT = 4
FIRING_POSITION_WEIGHT = 3
DODGE_WEIGHT = 1
BASE_ALARM_WEIGHT = 4
BASE_NORMAL_WEIGHT = 1
BASE_ALARM_RADIUS = 2
TANK_SHOT_WEIGHT = 2
BASE_DEFENSE_WEIGHT = 3
BASE_DEFENSE_MAX_MOVES = 2
HEURISTIC_SCORE_SCALE = (
    TANK_INITIAL_HP + BASE_INITIAL_HP + 1
    + THREAT_WEIGHT + FIRING_POSITION_WEIGHT + DODGE_WEIGHT + TANK_SHOT_WEIGHT
    + BASE_ALARM_WEIGHT
)

# Pygame settings
PLAYER_NAMES = ("A", "B")
WINDOW_TITLE = "Tank Battle"
RENDER_FPS = 60
DEFAULT_TURN_MS = 450
REPLAY_MAX_TURNS = 100
DEMO_SCENARIO = "opening_draw"
UI_PADDING = 24
UI_MIN_WINDOW_WIDTH = 560
UI_CONTROL_PANEL_WIDTH = 292
UI_CONTROL_PANEL_HEIGHT = 532
UI_BOARD_MAX_WIDTH = 680
UI_BOARD_MAX_HEIGHT = 480
UI_MIN_CELL_SIZE = 16
UI_MAX_CELL_SIZE = 78
UI_FONT_SIZE = 24

# Pygame palette
UI_PLAYER_COLORS = ((68, 173, 243), (247, 154, 81))

