"""Compare Tank Battle search agents in headless matches."""

import argparse
import csv
import math
import multiprocessing
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from . import config
from .agents.loader import load_agent
from .game.match import Match
from .game.rules import GameRules
from .game.state import create_initial_state


GAMES_PER_ROW = 10
MAX_CYCLES = 50
MOVE_TIMEOUT_MS = 20_000
INITIAL_BENCHMARK_HP = 2
FIXED_OPPONENT_DEPTH = 2
MAPS = config.MAPS_DIR / "benchmark"
HEURISTIC_AGENTS = (config.HEURISTIC_AGENT, config.HEURISTIC_ALPHA_BETA_AGENT)


@dataclass(frozen=True)
class Experiment:
    map_name: str
    agent: str
    depth: int | None
    fixed_opponent: bool = False


EXPERIMENTS = {
    "A_MiniMap": (
        Experiment("suite_mini.txt", config.MINIMAX_AGENT, None),
        Experiment("suite_mini.txt", config.ALPHA_BETA_AGENT, None),
        *(Experiment("suite_mini.txt", agent, 3) for agent in HEURISTIC_AGENTS),
    ),
    "B_StandardMap": tuple(
        Experiment("suite_standard.txt", agent, depth)
        for depth in (2, 3, 4)
        for agent in HEURISTIC_AGENTS
    ),
    "C_ShortMap": (
        Experiment("suite_short.txt", config.MINIMAX_AGENT, None),
        Experiment("suite_short.txt", config.ALPHA_BETA_AGENT, None),
    ),
    "D_FixedOpponent": tuple(
        Experiment("suite_fixed_opponent.txt", config.HEURISTIC_ALPHA_BETA_AGENT,
                   depth, fixed_opponent=True)
        for depth in (2, 3, 4)
    ),
}
COLUMNS = (
    "suite", "agent", "depth", "avg_time_ms", "max_time_ms",
    "avg_nodes", "avg_cutoffs", "avg_cycles", "win_draw_loss",
)


@dataclass
class Statistics:
    decisions: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0
    nodes: int = 0
    cutoffs: int = 0
    cycles: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0

    def record_decision(self, elapsed_ms, nodes, cutoffs):
        self.decisions += 1
        self.total_ms += elapsed_ms
        self.max_ms = max(self.max_ms, elapsed_ms)
        self.nodes += nodes
        self.cutoffs += cutoffs

    def record_result(self, outcome, cycles):
        self.cycles += cycles
        self.wins += int(outcome == 1)
        self.draws += int(outcome == 0)
        self.losses += int(outcome == -1)

    def summary(self, suite, agent, depth):
        completed = self.wins + self.draws + self.losses
        return (
            suite, agent, "none" if depth is None else depth,
            self.total_ms / self.decisions if self.decisions else None,
            self.max_ms if self.decisions else None,
            self.nodes / self.decisions if self.decisions else None,
            self.cutoffs / self.decisions if self.decisions else None,
            self.cycles / completed if completed else None,
            f"{self.wins}W-{self.draws}D-{self.losses}L",
        )


def load_benchmark_map(map_name):
    state = create_initial_state(MAPS / map_name)
    for entity in (*state.tanks.values(), *state.bases.values()):
        entity.hp = INITIAL_BENCHMARK_HP
    return state


def play_game(sender, experiment, side, seed, max_cycles):
    """Play headlessly. Only the measured agent's decision is timed."""
    with sender:
        try:
            rules = GameRules()
            state = load_benchmark_map(experiment.map_name)
            agent = load_agent(experiment.agent, rules, depth_limit=experiment.depth)
            opponent = None
            if experiment.fixed_opponent:
                opponent = load_agent(
                    config.HEURISTIC_ALPHA_BETA_AGENT, rules, depth_limit=FIXED_OPPONENT_DEPTH,
                )
            rng = random.Random(seed)
            match = Match(state, rules, {side: agent}, config.DEFAULT_TURN_MS)
            seen = Counter({state.search_key(): 1})
            while match.tick < max_cycles:
                snapshot = match.agent_state(side)
                sender.send(("search", "agent"))
                start = perf_counter()
                action = agent.choose_action(snapshot)
                elapsed_ms = (perf_counter() - start) * 1000
                if action not in rules.actions(match.state, side):
                    raise ValueError(f"Illegal action: {action!r}")
                sender.send(("decision", (
                    elapsed_ms, agent.metrics.nodes_visited, agent.metrics.alpha_beta_cutoffs,
                )))
                opponent_actions = rules.actions(match.state, 1 - side)
                if opponent is None:
                    reply = rng.choice(opponent_actions)
                else:
                    opponent_state = match.agent_state(1 - side)
                    sender.send(("search", "opponent"))
                    start = perf_counter()
                    reply = opponent.choose_action(opponent_state)
                    sender.send(("opponent_decision", (perf_counter() - start) * 1000))
                match.play_tick({side: action, 1 - side: reply})
                if rules.terminal_test(match.state):
                    sender.send(("result", (rules.utility(match.state, side), match.tick)))
                    return
                key = match.state.search_key()
                seen[key] += 1
                if seen[key] >= 3:
                    break
            sender.send(("result", (0, match.tick)))
        except RecursionError:
            sender.send(("interrupted", "Python recursion limit"))
        except Exception as error:
            sender.send(("error", f"{type(error).__name__}: {error}"))


def run_game(context, statistics, experiment, side, seed, max_cycles, timeout_ms):
    """Stop the worker if a single search exceeds its deadline."""
    receiver, sender = context.Pipe(duplex=False)
    worker = context.Process(
        target=play_game,
        args=(sender, experiment, side, seed, max_cycles),
    )
    with receiver, sender:
        worker.start()
        sender.close()
        searching = None
        try:
            while receiver.poll(timeout_ms / 1000 if searching else 20):
                message, data = receiver.recv()
                if message == "search":
                    searching = data
                elif message == "decision":
                    if data[0] > timeout_ms:
                        return "agent decision timeout"
                    searching = None
                    statistics.record_decision(*data)
                elif message == "opponent_decision":
                    if data > timeout_ms:
                        return "opponent decision timeout"
                    searching = None
                elif message == "result":
                    statistics.record_result(*data)
                    return None
                elif message == "interrupted":
                    return data
                elif message == "error":
                    raise RuntimeError(data)
            return f"{searching} decision timeout" if searching else "worker did not respond"
        except EOFError as error:
            raise RuntimeError("Benchmark worker exited without a result") from error
        finally:
            if worker.is_alive():
                worker.terminate()
            worker.join()
            worker.close()


def write_summary(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(COLUMNS)
        writer.writerows(rows)

    print("\n| " + " | ".join(COLUMNS) + " |")
    print("| " + " | ".join("---" for _ in COLUMNS) + " |")
    for row in rows:
        display = ["-" if value is None else f"{value:.3f}" if isinstance(value, float)
                   else str(value) for value in row]
        print("| " + " | ".join(display) + " |")
    print(f"\nCSV saved to {path}")


def main():
    parser = argparse.ArgumentParser(description="Headless Tank Battle benchmark")
    parser.add_argument("--suite", choices=("a", "b", "c", "d", "all"), default="all")
    parser.add_argument("--runs", type=int, default=GAMES_PER_ROW, help="Games per row")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-ticks", type=int, default=MAX_CYCLES)
    parser.add_argument(
        "--timeout-ms", type=float, default=MOVE_TIMEOUT_MS,
        help="Deadline per decision in ms (default: %(default)s)",
    )
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    if not 1 <= args.runs <= 2**31 or args.max_ticks < 1:
        parser.error("--runs and --max-ticks must be positive")
    if not math.isfinite(args.timeout_ms) or args.timeout_ms <= 0:
        parser.error("--timeout-ms must be finite and positive")

    context = multiprocessing.get_context("spawn")
    seeds = random.Random(args.seed).sample(range(2**31), args.runs)
    rows = []
    for suite, experiments in EXPERIMENTS.items():
        if args.suite not in ("all", suite[0].lower()):
            continue
        for experiment in experiments:
            opponent = (
                f"{config.HEURISTIC_ALPHA_BETA_AGENT} depth {FIXED_OPPONENT_DEPTH}"
                if experiment.fixed_opponent else "Random"
            )
            print(
                f"{suite} | {experiment.agent} depth {experiment.depth} vs {opponent}"
                f" | {args.runs} games | {args.timeout_ms:g} ms per decision",
                flush=True,
            )
            statistics = Statistics()
            for index, seed in enumerate(seeds):
                interruption = run_game(
                    context, statistics, experiment, index % 2,
                    seed, args.max_ticks, args.timeout_ms,
                )
                if interruption:
                    print(f"  Game {index + 1}: {interruption}", flush=True)
            rows.append(statistics.summary(suite, experiment.agent, experiment.depth))
    write_summary(args.output_dir / "benchmark_summary.csv", rows)


if __name__ == "__main__":
    main()
