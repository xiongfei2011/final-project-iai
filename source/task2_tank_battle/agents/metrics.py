"""Counters for one completed or in-progress search."""

from dataclasses import dataclass


@dataclass
class SearchMetrics:
    nodes_visited: int = 0
    max_depth: int = 0
    alpha_beta_cutoffs: int = 0

    def visit(self, depth: int) -> None:
        self.nodes_visited += 1
        self.max_depth = max(self.max_depth, depth)
