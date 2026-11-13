"""Read and validate a text map before creating a game state."""

from dataclasses import dataclass
from pathlib import Path

REQUIRED_SYMBOLS = "ABab"


@dataclass(frozen=True)
class MapLayout:
    height: int
    width: int
    tank_positions: tuple[tuple[int, int], ...]
    base_positions: tuple[tuple[int, int], ...]
    wall_positions: tuple[tuple[int, int], ...]


def load_map(path: str | Path) -> MapLayout:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as error:
        raise ValueError(f"{path}: map file not found") from error
    except (OSError, UnicodeError) as error:
        raise ValueError(f"{path}: could not read map: {error}") from error

    if not text.strip():
        raise ValueError(f"{path}: map is empty")

    rows = text.removesuffix("\n").split("\n")
    width = len(rows[0])
    if width == 0:
        raise ValueError(f"{path}: line 1: map row is empty")

    entities = {}
    walls = []
    for line_number, row in enumerate(rows, start=1):
        if len(row) != width:
            raise ValueError(
                f"{path}: line {line_number}: expected {width} columns, got {len(row)}"
            )

        for column, symbol in enumerate(row, start=1):
            position = (line_number, column)
            location = f"{path}: line {line_number}, column {column}"
            if symbol == "#":
                walls.append(position)
            elif symbol in REQUIRED_SYMBOLS:
                if symbol in entities:
                    raise ValueError(f"{location}: duplicate symbol {symbol!r}")
                entities[symbol] = position
            elif symbol != ".":
                raise ValueError(f"{location}: invalid symbol {symbol!r}")

    missing = [symbol for symbol in REQUIRED_SYMBOLS if symbol not in entities]
    if missing:
        raise ValueError(f"{path}: missing required symbols: {', '.join(missing)}")

    return MapLayout(
        height=len(rows),
        width=width,
        tank_positions=(entities["A"], entities["B"]),
        base_positions=(entities["a"], entities["b"]),
        wall_positions=tuple(walls),
    )
