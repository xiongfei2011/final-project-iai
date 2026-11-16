from abc import ABC, abstractmethod
from contextlib import nullcontext
from math import inf
from time import perf_counter
from typing import Protocol, runtime_checkable

from ..game.actions import Action
from ..game.rules import GameRules
from ..game.state import GameState, GameStateKey
from .evaluation import Evaluator, HeuristicEvaluator
from .metrics import SearchMetrics


@runtime_checkable
class Agent(Protocol):
    def choose_action(self, state: GameState) -> Action | str | None:  # Trả về action
        ...


class _SearchDeadlineReached(Exception):
    pass


class SearchAgent(ABC):

    def __init__(
        self,
        rules: GameRules,
        depth_limit: int | None,
        *,
        evaluator: Evaluator | None = None,
    ) -> None:
        if depth_limit is None and evaluator is not None:
            raise ValueError("Heuristic search requires a depth limit")
        if depth_limit is not None and depth_limit < 1:
            raise ValueError("Search depth must be a positive integer")
        self.rules = rules
        self.depth_limit = depth_limit
        self.evaluator = evaluator
        self.metrics = SearchMetrics()
        self._deadline: float | None = None
        self._evaluation_scores: dict[GameStateKey, float] | None = None

    @property
    def states_visited(self) -> int:
        return self.metrics.nodes_visited

    @property
    def max_depth(self) -> int:
        return self.metrics.max_depth

    def search(
        self, state: GameState, *, root_action: str | None = None
    ) -> tuple[str | None, float]:
        self._check_deadline()
        self.metrics = SearchMetrics(nodes_visited=1)  # The root is at depth 0.
        max_player = state.current_turn
        actions = self.rules.actions(state, max_player)

        if root_action is not None:
            if root_action not in actions:
                raise ValueError(f"Illegal root action: {root_action!r}")
            actions = [root_action]
        if self.rules.terminal_test(state):
            return None, self.rules.utility(state, max_player)

        if root_action is None:
            if state.played_states:
                actions = self._prefer_new_boards(state, max_player, actions)
            if state.previous_action in actions:
                actions = sorted(actions, key=lambda action: action == state.previous_action)

        return self._best_action(
            state, max_player, actions, -inf, inf, depth=0, visited_states=set()
        )

    def _prefer_new_boards(
        self, state: GameState, player: int, actions: list[str]
    ) -> list[str]:
        replies = self.rules.actions(state, 1 - player)

        def count_repeats(action: str) -> int:
            repeats = 0
            for reply in replies:
                self._check_deadline()
                children = self.rules.possible_results(state, {player: action, 1 - player: reply})
                if any(child.search_key() in state.played_states for child in children):
                    repeats += 1
            return repeats

        # Earlier actions win score ties, so try actions with fewer repeats first.
        return sorted(actions, key=count_repeats)

    def _best_action(
        self,
        state: GameState,
        max_player: int,
        actions: list[str],
        alpha: float,
        beta: float,
        depth: int,
        visited_states: set[GameStateKey],
    ) -> tuple[str | None, float]:
        replies = self.rules.actions(state, 1 - max_player)
        best_action = None
        best_score = -inf
        state_key = state.search_key()
        visited_states.add(state_key)

        try:
            for index, action in enumerate(actions):
                score = self._action_value(
                    state,
                    max_player,
                    action,
                    replies,
                    alpha,
                    beta,
                    depth,
                    visited_states,
                )
                if score > best_score:
                    best_action, best_score = action, score
                alpha, beta = self._update_bounds(
                    alpha, beta, best_score, maximizing=True
                )
                if beta <= alpha:
                    self.metrics.alpha_beta_cutoffs += int(index + 1 < len(actions))
                    break
        finally:
            # Backtrack so sibling branches can evaluate this board independently.
            visited_states.remove(state_key)
        return best_action, best_score

    def _action_value(
        self,
        state: GameState,
        max_player: int,
        action: str,
        replies: list[str],
        alpha: float,
        beta: float,
        depth: int,
        visited_states: set[GameStateKey],
    ) -> float:
        worst_score = inf

        for index, reply in enumerate(replies):
            self._check_deadline()
            children = self.rules.possible_results(
                state, {max_player: action, 1 - max_player: reply}
            )
            # Use the worst outcome when a contested move has no known winner.
            for child_index, child in enumerate(children):
                score = self._value(
                    child, max_player, alpha, beta, depth + 1, visited_states
                )
                worst_score = min(worst_score, score)
                alpha, beta = self._update_bounds(
                    alpha, beta, worst_score, maximizing=False
                )
                if beta <= alpha:
                    if child_index + 1 < len(children) or index + 1 < len(replies):
                        self.metrics.alpha_beta_cutoffs += 1
                    return worst_score
        return worst_score

    def _value(
        self,
        state: GameState,
        max_player: int,
        alpha: float,
        beta: float,
        depth: int,
        visited_states: set[GameStateKey],
    ) -> float:

        self._check_deadline()
        self.metrics.visit(depth)

        state_key = state.search_key()
        if state_key in visited_states:
            return 0.0
        if self.rules.terminal_test(state):
            return self.rules.utility(state, max_player)
        if self.depth_limit is not None and depth >= self.depth_limit:
            if self.evaluator is None:
                return 0.0
            scores = self._evaluation_scores
            if scores is None:
                return self.evaluator.evaluate(state, max_player)
            # Cache only the heuristic for this board, never a path-dependent search value.
            if state_key not in scores:
                scores[state_key] = self.evaluator.evaluate(state, max_player)
            return scores[state_key]

        actions = self.rules.actions(state, max_player)

        return self._best_action(
            state, max_player, actions, alpha, beta, depth, visited_states
        )[1]

    @abstractmethod
    def _update_bounds(
        self, alpha: float, beta: float, best_score: float, *, maximizing: bool
    ) -> tuple[float, float]:
        ...

    def choose_action(self, state: GameState) -> str | None:
        action, _ = self.search(state)
        return action

    def choose_action_with_budget(self, state: GameState, budget_ms: float) -> str | None:
        deadline = perf_counter() + budget_ms / 1000
        if self.rules.terminal_test(state):
            return None

        best_action = Action.STAY.value
        completed_metrics = SearchMetrics()
        max_depth = self.depth_limit
        self._deadline = deadline
        if isinstance(self.evaluator, HeuristicEvaluator):
            self._evaluation_scores = {}
        pathfinding = (
            self.evaluator.reuse_pathfinding()
            if isinstance(self.evaluator, HeuristicEvaluator)
            else nullcontext()
        )
        try:
            with pathfinding:
                depth = 1
                while max_depth is None or depth <= max_depth:
                    self.depth_limit = depth
                    action, _ = self.search(state)
                    self._check_deadline()
                    best_action = action
                    completed_metrics = self.metrics
                    if completed_metrics.max_depth < depth:
                        break
                    depth += 1
        except (_SearchDeadlineReached, RecursionError):
            pass
        finally:
            self.depth_limit = max_depth
            self._deadline = None
            self._evaluation_scores = None
            self.metrics = completed_metrics
        return best_action

    def _check_deadline(self) -> None:
        if self._deadline is not None and perf_counter() >= self._deadline:
            raise _SearchDeadlineReached


class MinimaxAgent(SearchAgent):
    def _update_bounds(
        self, alpha: float, beta: float, best_score: float, *, maximizing: bool
    ) -> tuple[float, float]:
        return alpha, beta


class AlphaBetaAgent(SearchAgent):
    def _update_bounds(
        self, alpha: float, beta: float, best_score: float, *, maximizing: bool
    ) -> tuple[float, float]:
        if maximizing:
            return max(alpha, best_score), beta
        return alpha, min(beta, best_score)
