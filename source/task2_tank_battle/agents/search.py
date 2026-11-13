"""Maximin search over simultaneous actions, with optional alpha-beta pruning."""

from abc import ABC, abstractmethod
from math import inf
from typing import Protocol, runtime_checkable

from ..config import DEFAULT_SEARCH_DEPTH
from ..game.actions import Action
from ..game.rules import GameRules
from ..game.state import GameState, GameStateKey
from .evaluation import Evaluator, HeuristicEvaluator


@runtime_checkable
class Agent(Protocol):
    def choose_action(self, state: GameState) -> Action | str | None:  # Trả về action
        ...


class SearchAgent(ABC):

    def __init__(
        self,
        rules: GameRules,
        depth_limit: int | None,
        *,
        evaluator: Evaluator | None = None,
        opponent_model: Agent | None = None,
    ) -> None:
        if depth_limit is None and evaluator is not None:
            raise ValueError("Heuristic search requires a depth limit")
        if depth_limit is not None and depth_limit < 1:
            raise ValueError("Search depth must be a positive integer")
        self.rules = rules
        self.depth_limit = depth_limit
        self.evaluator = evaluator
        self.states_visited = 0
        self.max_depth = 0
        self.opponent_model = opponent_model

    def search(
        self, state: GameState, *, root_action: str | None = None
    ) -> tuple[str | None, float]:
        self.states_visited = 1  # The root is visited at depth 0.
        self.max_depth = 0
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
                # Keep the earlier action on a score tie, so try the last action last.
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
                child = self.rules.result_tick(state, {player: action, 1 - player: reply})
                if child.search_key() in state.played_states:
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
        replies = self._opponent_replies(state, max_player)
        best_action = None
        best_score = -inf
        state_key = state.search_key()
        visited_states.add(state_key)

        try:
            for action in actions:
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

        for reply in replies:
            child = self.rules.result_tick(
                state, {max_player: action, 1 - max_player: reply}
            )
            score = self._value(
                child, max_player, alpha, beta, depth + 1, visited_states
            )
            worst_score = min(worst_score, score)
            alpha, beta = self._update_bounds(
                alpha, beta, worst_score, maximizing=False
            )
            if beta <= alpha:
                break
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

        self.states_visited += 1
        self.max_depth = max(self.max_depth, depth)

        if state.search_key() in visited_states:
            return 0.0
        if self.rules.terminal_test(state):
            return self.rules.utility(state, max_player)
        if self.depth_limit is not None and depth >= self.depth_limit:
            if self.evaluator is not None:
                return self.evaluator.evaluate(state, max_player)
            return 0.0

        actions = self.rules.actions(state, max_player)
        return self._best_action(
            state, max_player, actions, alpha, beta, depth, visited_states
        )[1]

    def _opponent_replies(self, state: GameState, max_player: int) -> list[str]:
        opponent = 1 - max_player
        legal_replies = self.rules.actions(state, opponent)

        if self.opponent_model is None or not legal_replies:
            return legal_replies

        opponent_state = state.clone()
        opponent_state.current_turn = opponent
        predicted_action = self.opponent_model.choose_action(opponent_state)

        if predicted_action in legal_replies:
            return [predicted_action]

        return legal_replies

    @abstractmethod
    def _update_bounds(
        self, alpha: float, beta: float, best_score: float, *, maximizing: bool
    ) -> tuple[float, float]:
        """Return the bounds to use for the next child."""
        ...

    def choose_action(self, state: GameState) -> str | None:
        action, _ = self.search(state)
        return action


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


def create_minimax_agent(
    rules: GameRules, depth_limit: int | None = DEFAULT_SEARCH_DEPTH
) -> MinimaxAgent:
    return MinimaxAgent(rules, depth_limit)


def create_alpha_beta_agent(
    rules: GameRules, depth_limit: int | None = DEFAULT_SEARCH_DEPTH
) -> AlphaBetaAgent:
    return AlphaBetaAgent(rules, depth_limit)


def create_heuristic_minimax_agent(
    rules: GameRules, depth_limit: int = DEFAULT_SEARCH_DEPTH
) -> MinimaxAgent:
    return MinimaxAgent(
        rules, depth_limit=depth_limit, evaluator=HeuristicEvaluator(rules)
    )


def create_heuristic_minimax_alpha_beta_agent(
    rules: GameRules, depth_limit: int = DEFAULT_SEARCH_DEPTH
) -> AlphaBetaAgent:
    return AlphaBetaAgent(
        rules, depth_limit=depth_limit, evaluator=HeuristicEvaluator(rules)
    )
