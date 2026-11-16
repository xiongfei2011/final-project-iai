import random
from typing import List, Optional
from .solvers import NQueensSATSolver, MinConflictsSolver, HeuristicMinConflictsSolver


class NQueensBenchmark:
    def __init__(
        self,
        sat_sizes: Optional[List[int]] = None,
        mc_sizes: Optional[List[int]] = None,
        trials: int = 30,
        seed: Optional[int] = 42,
        report_file: str = "benchmark_report.txt",
    ):
        self.sat_sizes = sat_sizes or [4, 8, 12, 16, 20, 30, 40, 50]
        self.mc_sizes = mc_sizes or [10, 20, 50, 100]
        self.trials = trials
        self.seed = seed
        self.rng = random.Random(seed)
        self.report_file = report_file
        self._lines: List[str] = []

    def _log(self, text: str = "") -> None:
        print(text, flush=True)
        self._lines.append(text)

    def run_sat(self) -> None:
        self._log("=== [T1-02] GLUCOSE3 (SAT) ===")
        self._log(f"{'N':<5} | {'CNF Clauses':<15} | {'Time (ms)':<15} | Valid")
        self._log("-" * 52)
        for n in self.sat_sizes:
            res = NQueensSATSolver(n).solve()
            self._log(f"{n:<5} | {res.clauses_count:<15} | {res.elapsed_time_ms:<15} | {res.solved}")

    def run_min_conflicts(self) -> None:
        self._log(f"\n=== [T1-03] MIN-CONFLICTS STANDARD vs HEURISTIC ({self.trials} trials/N) ===")
        self._log(f"{'N':<5} | {'Algorithm':<27} | {'Solved':<9} | {'Avg Steps':<10} | Avg Time (ms)")
        self._log("-" * 75)
        for n in self.mc_sizes:
            solvers = [
                MinConflictsSolver(n, seed=self.seed),
                HeuristicMinConflictsSolver(n, seed=self.seed),
            ]
            totals = {s.NAME: [0, 0, 0.0] for s in solvers}
            for _ in range(self.trials):
                start_board = [self.rng.randrange(n) for _ in range(n)]
                for solver in solvers:
                    res = solver.solve(start_board)
                    total = totals[solver.NAME]
                    total[0] += res.solved
                    total[1] += res.steps
                    total[2] += res.elapsed_time_ms
            for name, (ok, steps, ms) in totals.items():
                self._log(
                    f"{n:<5} | {name:<27} | {ok}/{self.trials:<6} | {round(steps / self.trials, 1):<10} | {round(ms / self.trials, 3)}"
                )

    def run(self) -> None:
        self._lines.clear()
        self.run_sat()
        self.run_min_conflicts()
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(self._lines) + "\n")
        print(f"\nDone! Saved report to: {self.report_file}")


if __name__ == "__main__":
    NQueensBenchmark().run()