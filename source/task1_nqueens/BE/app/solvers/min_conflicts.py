import random
import time
from typing import Dict, List, Optional
from .base_solver import BaseNQueensSolver
from ..models import SolverResult


class MinConflictsSolver(BaseNQueensSolver):

    NAME = "Min-Conflicts"

    def __init__(self, n: int, max_steps: int = 15000, record_history: bool = False, seed: Optional[int] = None):
        super().__init__(n)
        self.max_steps = max_steps
        self.record_history = record_history
        self.rng = random.Random(seed)
        self.queens: List[int] = []
        # Counters for queens per row and two diagonals -> O(1) conflict computation
        # Note: Bảng đếm số hậu theo hàng và 2 đường chéo để tính xung đột O(1).
        self._rows = [0] * n
        self._diag1 = [0] * (2 * n - 1)
        self._diag2 = [0] * (2 * n - 1)

    def _place(self, col: int, row: int, delta: int) -> None:
        self._rows[row] += delta
        self._diag1[row - col + self.n - 1] += delta
        self._diag2[row + col] += delta

    def _load(self, queens: List[int]) -> None:
        self.queens = list(queens)
        self._rows = [0] * self.n
        self._diag1 = [0] * (2 * self.n - 1)
        self._diag2 = [0] * (2 * self.n - 1)
        for col, row in enumerate(self.queens):
            self._place(col, row, +1)

    def _conflicts(self, col: int, row: int) -> int:
        """Số hậu khác tấn công ô (row, col)"""
        total = self._rows[row] + self._diag1[row - col + self.n - 1] + self._diag2[row + col]
        return total - 3 if self.queens[col] == row else total

    def _conflicted_columns(self) -> Dict[int, int]:
        """Dict cột đang xung đột -> số xung đột của cột đó"""
        counts = {col: self._conflicts(col, row) for col, row in enumerate(self.queens)}
        return {col: k for col, k in counts.items() if k > 0}

    def _select_variable(self, conflicted: Dict[int, int]) -> int:
        """Standard: chọn ngẫu nhiên một cột đang xung đột"""
        return self.rng.choice(list(conflicted))

    def _best_row(self, col: int) -> int:
        counts = [self._conflicts(col, row) for row in range(self.n)]
        best = min(counts)
        return self.rng.choice([row for row, k in enumerate(counts) if k == best])

    def solve(self, initial: Optional[List[int]] = None) -> SolverResult:
        start = time.perf_counter()
        self._load(initial if initial else [self.rng.randrange(self.n) for _ in range(self.n)])
        history = [list(self.queens)] if self.record_history else None

        steps = 0
        while steps < self.max_steps:
            conflicted = self._conflicted_columns()
            if not conflicted:
                break
            col = self._select_variable(conflicted)
            old_row, new_row = self.queens[col], self._best_row(col)
            steps += 1
            if new_row != old_row:
                self._place(col, old_row, -1)
                self.queens[col] = new_row
                self._place(col, new_row, +1)
                if history is not None:
                    history.append(list(self.queens))

        elapsed_ms = (time.perf_counter() - start) * 1000
        result = self._build_result(list(self.queens), elapsed_ms, steps=steps, history=history)
        result.message = (
            f"Found a solution after {steps} steps." if result.solved
            else f"Reached {self.max_steps} steps, {result.conflicts} conflict pairs remain."
        )
        return result


class HeuristicMinConflictsSolver(MinConflictsSolver):
    """Ưu tiên cột xung đột nhiều nhất; với xác suất random_walk_prob thì chọn ngẫu nhiên"""

    NAME = "Min-Conflicts (Heuristic)"

    def __init__(self, n: int, max_steps: int = 15000, record_history: bool = False,
                 seed: Optional[int] = None, random_walk_prob: float = 0.15):
        super().__init__(n, max_steps, record_history, seed)
        self.random_walk_prob = random_walk_prob

    def _select_variable(self, conflicted: Dict[int, int]) -> int:
        if self.rng.random() < self.random_walk_prob:
            return super()._select_variable(conflicted)
        worst = max(conflicted.values())
        return self.rng.choice([col for col, k in conflicted.items() if k == worst])