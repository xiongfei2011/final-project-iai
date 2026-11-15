from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SolverResult:
    """queens[col] = hàng của hậu"""
    algorithm: str
    n: int
    solved: bool
    queens: List[int]
    conflicts: int
    elapsed_time_ms: float
    steps: int = 0
    clauses_count: int = 0
    history: Optional[List[List[int]]] = None
    message: str = ""