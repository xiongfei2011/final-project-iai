from abc import ABC, abstractmethod
from typing import List
from ..board import NQueensBoard
from ..models import SolverResult


class BaseNQueensSolver(ABC):

    NAME = "Base"

    def __init__(self, n: int):
        if n < 4:
            raise ValueError("The size of the board must be at least 4.")
        self.n = n

    @abstractmethod
    def solve(self) -> SolverResult:
        """Giải và return kết quả."""

    def validate_solution(self, queens: List[int]) -> int:
        """Đếm số cặp hậu tấn công; trả -1 nếu bàn cờ chưa hợp lệ đủ N quân."""

        if len(queens) != self.n or any(not 0 <= r < self.n for r in queens):
            return -1
        return len(NQueensBoard.attacking_pairs(queens))

    def _build_result(self, queens: List[int], elapsed_ms: float, **extra) -> SolverResult:
        conflicts = self.validate_solution(queens)
        return SolverResult(
            algorithm=self.NAME,
            n=self.n,
            solved=(conflicts == 0),
            queens=queens,
            conflicts=conflicts,
            elapsed_time_ms=round(elapsed_ms, 3),
            **extra,
        )