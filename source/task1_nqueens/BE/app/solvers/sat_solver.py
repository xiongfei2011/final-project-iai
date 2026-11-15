import time
from itertools import combinations
from typing import Dict, List
from pysat.solvers import Glucose3
from .base_solver import BaseNQueensSolver
from ..board import NQueensBoard
from ..models import SolverResult


class NQueensSATSolver(BaseNQueensSolver):
    """Mã hóa N-Queens thành CNF (mỗi ô là biến)"""

    NAME = "Glucose3 (SAT)"

    def __init__(self, n: int):
        super().__init__(n)
        self.clauses: List[List[int]] = []

    def _var(self, row: int, col: int) -> int:
        return row * self.n + col + 1

    def _lines(self) -> Dict[str, List[List[int]]]:
        """Gom biến theo hàng, cột và 2 loại đường chéo"""
        n = self.n
        diag1: Dict[int, List[int]] = {}
        diag2: Dict[int, List[int]] = {}
        for r in range(n):
            for c in range(n):
                diag1.setdefault(r - c, []).append(self._var(r, c))
                diag2.setdefault(r + c, []).append(self._var(r, c))
        return {
            "rows": [[self._var(r, c) for c in range(n)] for r in range(n)],
            "cols": [[self._var(r, c) for r in range(n)] for c in range(n)],
            "diags": list(diag1.values()) + list(diag2.values()),
        }

    @staticmethod
    def _at_least_one(line: List[int]) -> List[List[int]]:
        return [list(line)]

    @staticmethod
    def _at_most_one(line: List[int]) -> List[List[int]]:
        return [[-a, -b] for a, b in combinations(line, 2)]

    def build_cnf(self) -> List[List[int]]:
        lines = self._lines()
        clauses: List[List[int]] = []
        for line in lines["rows"] + lines["cols"]:        # mỗi hàng/cột có ít nhất 1 hậu
            clauses += self._at_least_one(line)
        for line in lines["rows"] + lines["cols"] + lines["diags"]:   # mỗi hàng/cột/chéo có nhiều nhất 1 hậu.
            clauses += self._at_most_one(line)
        self.clauses = clauses
        return clauses

    def _decode(self, model: List[int]) -> List[int]:
        queens = [NQueensBoard.EMPTY] * self.n
        for lit in model:
            if 0 < lit <= self.n * self.n:
                queens[(lit - 1) % self.n] = (lit - 1) // self.n
        return queens

    def solve(self) -> SolverResult:
        self.build_cnf()
        with Glucose3(bootstrap_with=self.clauses) as glucose:
            start = time.perf_counter()
            satisfiable = glucose.solve()
            elapsed_ms = (time.perf_counter() - start) * 1000   # Chỉ tính thời gian giải
            model = glucose.get_model() if satisfiable else []
        return self._build_result(
            self._decode(model),
            elapsed_ms,
            clauses_count=len(self.clauses),
            message=(
                f"{self.n * self.n} variables, {len(self.clauses)} CNF clauses."
                if satisfiable else "UNSAT."
            ),
        )