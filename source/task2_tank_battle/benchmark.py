"""Compare the four search configurations on finite tank battle positions.

Run from source with python -m task2_tank_battle.benchmark --help.
"""

import argparse
import csv
import math
import multiprocessing
import sys
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from statistics import median

from .agents.search import (
    create_alpha_beta_agent,
    create_heuristic_minimax_agent,
    create_heuristic_minimax_alpha_beta_agent,
    create_minimax_agent,
)
from .config import DEFAULT_SEARCH_DEPTH
from .game.actions import Direction
from .game.entities import Bullet, Position
from .game.rules import GameRules
from .game.state import GameState, create_state_from_layout
from .game.map_loader import MapLayout


TITLE = "T2-03 - Tank Battle Search Benchmark"

CONFIGURATIONS = {
    "Minimax": (create_minimax_agent, False),
    "Alpha-Beta": (create_alpha_beta_agent, False),
    "Heuristic Minimax": (create_heuristic_minimax_agent, True),
    "Heuristic Minimax + Alpha-Beta": (
        create_heuristic_minimax_alpha_beta_agent,
        True,
    ),
}


@dataclass(frozen=True)
class Scenario:
    height: int
    target_column: int
    defender_column: int
    impact_in: int


# The incoming bullet is already in range of B's base at the measured tick.
# Both tanks are too far away to intercept it before it reaches the base.
SCENARIOS = {
    "incoming_shot": Scenario(height=5, target_column=5, defender_column=5, impact_in=1),
    "countershot": Scenario(height=7, target_column=10, defender_column=3, impact_in=2),
    "long_crossfire": Scenario(height=7, target_column=16, defender_column=12, impact_in=3),
}


@dataclass(frozen=True)
class Measurement:
    elapsed_ms: float
    states_visited: int
    max_depth: int
    action: str
    value: float


@dataclass(frozen=True)
class ResultRow:
    scenario: str
    configuration: str
    runs: int
    completed_runs: int
    median_ms: float | None
    median_states_visited: float | None
    median_max_depth: float | None
    status: str
    action: str | None
    search_value: float | None
    depth_limit: int | None
    timeout_ms: float


def create_scenario(name: str, rules: GameRules) -> GameState:
    """Build a bounded search position without advancing the game rules."""
    scenario = SCENARIOS[name]
    layout = MapLayout(
        height=scenario.height,
        width=scenario.target_column,
        tank_positions=((2, 1), (scenario.height, scenario.defender_column)),
        base_positions=((scenario.height, 1), (2, scenario.target_column)),
        wall_positions=(),
    )
    state = create_state_from_layout(layout)
    state.tanks[0].direction = Direction.RIGHT
    state.tanks[1].direction = Direction.LEFT
    for base in state.bases.values():
        base.hp = 1
    state.current_turn = 1
    state.bullets.append(
        Bullet(
            position=Position(2, scenario.target_column - scenario.impact_in),
            direction=Direction.RIGHT,
            steps_left=scenario.impact_in,
        )
    )
    return state


def create_agent(configuration, rules, depth):
    factory, uses_heuristic = CONFIGURATIONS[configuration]
    if uses_heuristic:
        return factory(rules, depth_limit=depth)
    return factory(rules)


def measure_search(sender, scenario, configuration, depth):
    with sender:
        try:
            rules = GameRules()
            state = create_scenario(scenario, rules)
            agent = create_agent(configuration, rules, depth)
            legal_actions = rules.actions(state)
            sender.send(("ready", None))

            start = time.perf_counter()
            action, value = agent.search(state)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if action not in legal_actions:
                raise ValueError(f"Search selected an illegal action: {action!r}")
            sender.send(("ok", Measurement(
                elapsed_ms, agent.states_visited, agent.max_depth, action, value
            )))
        except Exception as error:
            sender.send(("error", f"{type(error).__name__}: {error}"))


def run_trial(context, scenario, configuration, depth, timeout_ms):
    receiver, sender = context.Pipe(duplex=False)
    with receiver, sender:
        worker = context.Process(
            target=measure_search, args=(sender, scenario, configuration, depth)
        )
        worker.start()
        sender.close()
        try:
            if not receiver.poll(10):
                raise RuntimeError("Worker did not finish setup within 10 seconds")
            status, result = receiver.recv()
            if status != "ready":
                raise RuntimeError(result)

            if not receiver.poll(timeout_ms / 1000):
                return None
            status, result = receiver.recv()
            if status != "ok":
                raise RuntimeError(result)
            return result if result.elapsed_ms <= timeout_ms else None
        except EOFError as error:
            raise RuntimeError("Worker exited before reporting a result") from error
        finally:
            if worker.is_alive():
                worker.terminate()
            worker.join()
            worker.close()


def summarize(scenario, configuration, runs, samples, depth, timeout_ms):
    first = samples[0] if samples else None
    if first and any(
        sample.action != first.action or sample.value != first.value for sample in samples
    ):
        raise RuntimeError(f"Repeated searches disagree for {scenario} / {configuration}")

    return ResultRow(
        scenario=scenario,
        configuration=configuration,
        runs=runs,
        completed_runs=len(samples),
        median_ms=median(sample.elapsed_ms for sample in samples) if samples else None,
        median_states_visited=median(sample.states_visited for sample in samples) if samples else None,
        median_max_depth=median(sample.max_depth for sample in samples) if samples else None,
        status="ok" if len(samples) == runs else "timeout",
        action=first.action if first else None,
        search_value=first.value if first else None,
        depth_limit=depth if CONFIGURATIONS[configuration][1] else None,
        timeout_ms=timeout_ms,
    )


def compare_pair(plain, pruned, depth):
    label = f"{plain.scenario} / {plain.configuration} vs {pruned.configuration}"
    if plain.search_value is None or pruned.search_value is None:
        return f"{label}: comparison unavailable (timeout)"
    if not math.isclose(plain.search_value, pruned.search_value, abs_tol=1e-12):
        raise RuntimeError(f"{label}: different values {plain.search_value} and {pruned.search_value}")
    if plain.action == pruned.action:
        return f"{label}: {plain.action}, value {plain.search_value:g}"

    # Check the pruned choice with a full window because a cutoff may return a bound.
    rules = GameRules()
    state = create_scenario(plain.scenario, rules)
    agent = create_agent(plain.configuration, rules, depth)
    player = state.current_turn
    replies = rules.actions(state, 1 - player)
    exact_value = agent._action_value(
        state, player, pruned.action, replies, -math.inf, math.inf, depth=0
    )
    if not math.isclose(exact_value, plain.search_value, abs_tol=1e-12):
        raise RuntimeError(f"{label}: {pruned.action} is not tied for the best value")
    return f"{label}: {plain.action} and {pruned.action} tie at {exact_value:g}"


def print_table(rows):
    def number(value, precision="g"):
        return "" if value is None else format(value, precision)

    table = [("Scenario", "Configuration", "Done/runs", "Median ms", "States", "Depth", "Status")]
    for row in rows:
        table.append((
            row.scenario,
            row.configuration,
            f"{row.completed_runs}/{row.runs}",
            number(row.median_ms, ".3f"),
            number(row.median_states_visited),
            number(row.median_max_depth),
            row.status,
        ))
    widths = [max(map(len, column)) for column in zip(*table)]
    for row in table:
        print("  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=[field.name for field in fields(ResultRow)])
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def main():
    parser = argparse.ArgumentParser(description=TITLE)
    parser.add_argument("--runs", type=int, default=5, help="Repetitions per configuration")
    parser.add_argument(
        "--depth", type=int, default=DEFAULT_SEARCH_DEPTH,
        help="Shared heuristic depth limit in ticks",
    )
    parser.add_argument("--timeout-ms", type=float, default=2000, help="Search deadline per run in ms")
    parser.add_argument("--csv", type=Path, default=Path(__file__).with_name("benchmark_results.csv"))
    args = parser.parse_args()
    if args.runs < 1 or args.depth < 1:
        parser.error("--runs and --depth must be positive integers")
    if not math.isfinite(args.timeout_ms) or args.timeout_ms <= 0:
        parser.error("--timeout-ms must be finite and positive")

    print(TITLE)
    print(f"Runs per configuration: {args.runs} | Heuristic depth: {args.depth} | "
          f"Timeout per run: {args.timeout_ms:g} ms", flush=True)
    context = multiprocessing.get_context("spawn")
    rows = []
    comparisons = []
    for scenario in SCENARIOS:
        by_configuration = {}
        for configuration in CONFIGURATIONS:
            samples = []
            for _ in range(args.runs):
                try:
                    sample = run_trial(context, scenario, configuration, args.depth, args.timeout_ms)
                except RuntimeError as error:
                    raise RuntimeError(f"{scenario} / {configuration}: {error}") from error
                if sample is not None:
                    samples.append(sample)
            row = summarize(scenario, configuration, args.runs, samples, args.depth, args.timeout_ms)
            by_configuration[configuration] = row
            rows.append(row)

        for plain, pruned in (
            ("Minimax", "Alpha-Beta"),
            ("Heuristic Minimax", "Heuristic Minimax + Alpha-Beta"),
        ):
            comparisons.append(compare_pair(by_configuration[plain], by_configuration[pruned], args.depth))

    print("States count the root at depth 0 and every visited search node, including leaves.")
    print("One tick applies both players' actions and moves bullets one cell.")
    print("Time, states and depth use medians of completed runs.")
    print("Any timed-out run marks its row as timeout. Metrics are blank when no run completes.")
    print_table(rows)
    print("\nSearch value checks")
    for comparison in comparisons:
        print(comparison)
    write_csv(args.csv, rows)
    print(f"\nCSV saved to {args.csv}")


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="backslashreplace")
    main()
