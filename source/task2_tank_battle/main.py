"""Show a static board or play an AI-versus-AI tank battle."""

import argparse
from functools import partial
from pathlib import Path

from . import config
from .agents.loader import load_agent
from .game.match import Match
from .game.rules import GameRules
from .game.state import GameState, create_initial_state
from .ui.match_session import MatchSession
from .ui.pygame_app import run_window


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{config.WINDOW_TITLE} - Pygame")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preview", action="store_true", help="Show the initial board")
    mode.add_argument(
        "--live", action="store_true", help="Play while the agents are choosing"
    )
    mode.add_argument(
        "--replay", dest="live", action="store_false",
        help="Plan the match after pressing Play, then show the replay (default)",
    )
    parser.set_defaults(live=False)
    board = parser.add_mutually_exclusive_group()
    board.add_argument(
        "--demo",
        action="store_true",
        help="Start from the benchmark crossfire scenario",
    )
    board.add_argument(
        "--map",
        dest="map_path",
        type=Path,
        help="Text map path (default: bundled default.txt)",
    )
    parser.add_argument(
        "--agent-a",
        default=config.DEFAULT_AGENTS[0],
        help="Built-in name or module:factory",
    )
    parser.add_argument(
        "--agent-b",
        default=config.DEFAULT_AGENTS[1],
        help="Built-in name or module:factory",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=config.DEFAULT_SEARCH_DEPTH,
        help="Search depth in ticks for the built-in heuristic agents",
    )
    parser.add_argument(
        "--turn-ms",
        type=int,
        default=config.DEFAULT_TURN_MS,
        help="Time between live ticks or replay frames in ms",
    )
    args = parser.parse_args()
    if args.depth < 1 or args.turn_ms < 1:
        parser.error("--depth and --turn-ms must be positive integers")

    rules = GameRules()
    map_loaders = {
        path.name: partial(create_initial_state, path)
        for path in sorted(config.MAPS_DIR.glob("*.txt"))
        if path.is_file()
    }
    if args.demo:
        from .benchmark import create_scenario

        map_name = "Demo"
        map_loaders[map_name] = partial(create_scenario, config.DEMO_SCENARIO, rules)
    else:
        map_path = (args.map_path or config.DEFAULT_MAP_PATH).resolve()
        map_name = map_path.name
        if map_name in map_loaders and (config.MAPS_DIR / map_name).resolve() != map_path:
            map_name = str(map_path)
        map_loaders[map_name] = partial(create_initial_state, map_path)

    try:
        state = map_loaders[map_name]()
    except ValueError as error:
        parser.error(str(error))

    def make_match(initial_state: GameState, specs: tuple[str, str]) -> Match:
        agents = {}
        for player, spec in enumerate(specs):
            try:
                agents[player] = load_agent(spec, rules, depth_limit=args.depth)
            except Exception as error:
                name = config.PLAYER_NAMES[player]
                raise ValueError(f"Could not load Player {name} agent {spec!r}: {error}") from error
        return Match(initial_state.clone(), rules, agents, args.turn_ms)

    session = MatchSession(
        state, (args.agent_a, args.agent_b), args.turn_ms, make_match,
        map_name=map_name, map_loaders=map_loaders, live=args.live, preview=args.preview,
    )
    run_window(state, session=session)


if __name__ == "__main__":
    main()
