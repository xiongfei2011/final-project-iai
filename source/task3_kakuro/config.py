from pathlib import Path

EMPTY_CELL = '.'
WALL_CELL = '#'

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
LINE_COLOR = (50, 50, 50)
TEXT_COLOR = (0, 0, 0)
CLUE_TEXT_COLOR = (255, 255, 255)


BASE_DIR = Path(__file__).parent
TESTS_DIR = BASE_DIR / "tests"

MAP_3000 = TESTS_DIR / "test3000.txt"
MAP_3001 = TESTS_DIR / "test3001.txt"