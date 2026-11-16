"""Show a static board or play an AI-versus-AI tank battle."""

import argparse
from functools import partial
from pathlib import Path

from . import config
from .agents.loader import AgentLoader
from .game.match import Match
from .game.rules import GameRules
from .game.state import GameState
from .ui.match_session import MatchSession
from .ui.pygame_app import run_window


def parse_standard_depth(value: str) -> int | None:
    if value.lower() == "none":
        return None
    try:
        depth = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a positive integer or 'none'") from None
    if depth < 1:
        raise argparse.ArgumentTypeError("expected a positive integer or 'none'")
    return depth


def create_demo_state() -> GameState:
    state = GameState.from_map(config.MAPS_DIR / "benchmark" / f"{config.DEMO_SCENARIO}.txt")
    for base in state.bases.values():
        base.hp = 1
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=f"{config.WINDOW_TITLE} - Pygame")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preview", action="store_true", help="Show the initial board")
    mode.add_argument(
        "--live", action="store_true", help="Play with a time budget for each AI decision (default)"
    )
    mode.add_argument(
        "--replay", dest="live", action="store_false",
        help="Plan the match after pressing Play, then show the replay",
    )
    mode.set_defaults(live=True)
    board = parser.add_mutually_exclusive_group()
    board.add_argument(
        "--demo",
        action="store_true",
        help="Start from the benchmark draw scenario",
    )
    board.add_argument(
        "--map",
        dest="map_path",
        type=Path,
        help="Text map path (default: bundled default.txt)",
    )
    parser.add_argument(
        "--tank-a-hp",
        type=int,
        metavar="HP",
        help="Starting HP for tank A on the selected map",
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
        help="Default search depth in ticks for the built-in agents",
    )
    parser.add_argument(
        "--standard-depth",
        type=parse_standard_depth,
        default=argparse.SUPPRESS,
        metavar="TICKS|none",
        help="Override --depth for Minimax and Alpha-Beta",
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
    if args.tank_a_hp is not None and not 1 <= args.tank_a_hp <= config.TANK_INITIAL_HP:
        parser.error(f"--tank-a-hp must be between 1 and {config.TANK_INITIAL_HP}")
    standard_depth = getattr(args, "standard_depth", args.depth)

    rules = GameRules(prioritize_first_reply=True)
    map_loaders = {
        path.name: partial(GameState.from_map, path)
        for path in sorted(config.MAPS_DIR.glob("*.txt"))
        if path.is_file()
    }
    if args.demo:
        map_name = "Demo"
        map_loaders[map_name] = create_demo_state
    else:
        map_path = (args.map_path or config.DEFAULT_MAP_PATH).resolve()
        map_name = map_path.name
        if map_name in map_loaders and (config.MAPS_DIR / map_name).resolve() != map_path:
            map_name = str(map_path)
        map_loaders[map_name] = partial(GameState.from_map, map_path)

    if args.tank_a_hp is not None:
        load_selected_map = map_loaders[map_name]

        def load_with_tank_a_hp() -> GameState:
            state = load_selected_map()
            state.tanks[0].hp = args.tank_a_hp
            return state

        map_loaders[map_name] = load_with_tank_a_hp

    try:
        state = map_loaders[map_name]()
    except ValueError as error:
        parser.error(str(error))

    def make_match(initial_state: GameState, specs: tuple[str, str]) -> Match:
        agents = {}
        for player, spec in enumerate(specs):
            depth_limit = args.depth
            if spec in (config.MINIMAX_AGENT, config.ALPHA_BETA_AGENT):
                depth_limit = standard_depth
            try:
                agents[player] = AgentLoader.load(spec, rules, depth_limit=depth_limit)
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
