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
TANK_INITIAL_HP = 9
BASE_INITIAL_HP = 6
WALL_INITIAL_HP = 3
DAMAGE_PER_HIT = 1

# A bullet moves one cell per tick and expires at this range.
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
BASE_ALARM_WEIGHT = 6
BASE_NORMAL_WEIGHT = 1
BASE_ALARM_RADIUS = 3
TANK_SHOT_WEIGHT = 2
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
DEMO_SCENARIO = "long_crossfire"
UI_PADDING = 24
UI_MIN_WINDOW_WIDTH = 560
UI_CONTROL_PANEL_WIDTH = 292
UI_CONTROL_PANEL_HEIGHT = 532
UI_BOARD_MAX_WIDTH = 680
UI_BOARD_MAX_HEIGHT = 480
UI_MIN_CELL_SIZE = 16
UI_MAX_CELL_SIZE = 78
UI_TITLE_FONT_SIZE = 37
UI_FONT_SIZE = 24

# Pygame palette
UI_BACKGROUND = (19, 24, 33)
UI_PANEL = (29, 37, 50)
UI_TEXT = (236, 241, 247)
UI_MUTED = (173, 187, 204)
UI_PLAYER_COLORS = ((68, 173, 243), (247, 154, 81))
UI_CELL_COLORS = ((41, 52, 66), (47, 59, 73))
UI_WALL_COLOR = (107, 118, 134)
UI_BULLET_COLOR = (255, 220, 94)
UI_DESTROYED_COLOR = (76, 83, 94)

