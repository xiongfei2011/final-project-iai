"""Maximin search over simultaneous actions, with optional alpha-beta pruning."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from ..config import DEFAULT_SEARCH_DEPTH
from ..game.actions import Action
from ..game.rules import GameRules
from ..game.state import GameState
from .evaluation import Evaluator, HeuristicEvaluator


@runtime_checkable
class Agent(Protocol):
    def choose_action(self, state: GameState) -> Action | str | None: # Trả về action
        ...


class SearchAgent(ABC):

    def __init__(
        self,
        rules: GameRules,
        depth_limit: int | None,
        *,
        evaluator: Evaluator | None = None,
        opponent_model: Agent | None = None
    ) -> None:
        self.rules = rules
        self.depth_limit = depth_limit
        self.evaluator = evaluator
        self.states_visited = 0
        self.max_depth = 0
        self.opponent_model = opponent_model

    def search(self, state: GameState) -> tuple[str | None, float]:
        """Choose the action with the best worst-case opponent reply."""
        self.states_visited = 1  # The root is visited at depth 0.
        self.max_depth = 0
        return self._best_action(
            state, state.current_turn, float("-inf"), float("inf"), 0
        )

    def _best_action(
        self, state: GameState, max_player: int, alpha: float, beta: float, depth: int
    ) -> tuple[str | None, float]:
        best_action = None
        best_score = float("-inf")
        replies = self._opponent_replies(state, max_player)

        for action in self.rules.actions(state, max_player):
            score = self._action_value(
                state, max_player, action, replies, alpha, beta, depth
            )

            if score > best_score:
                best_action = action
                best_score = score

            alpha, beta = self._update_bounds(alpha, beta, best_score, maximizing=True)
            if beta <= alpha:
                break

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
    ) -> float:
        # Both actions are chosen on the same board and applied in one tick.
        opponent = 1 - max_player
        best_score = float("inf")
        for reply in replies:
            actions = {max_player: action, opponent: reply}
            child = self.rules.result_tick(state, actions)
            score = self._value(child, max_player, alpha, beta, depth + 1)
            best_score = min(best_score, score)
            alpha, beta = self._update_bounds(alpha, beta, best_score, maximizing=False)
            if beta <= alpha:
                break
        return best_score

    def _value(
        self, state: GameState, max_player: int, alpha: float, beta: float, depth: int
    ) -> float:
        self.states_visited += 1
        self.max_depth = max(self.max_depth, depth)

        if self.rules.terminal_test(state):
            return self.rules.utility(state, max_player)

        if self.depth_limit is not None and depth >= self.depth_limit:
            if self.evaluator is not None:
                return self.evaluator.evaluate(state, max_player)
            return 0.0

        return self._best_action(state, max_player, alpha, beta, depth)[1]

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
    rules: GameRules, depth_limit: int | None = None
) -> MinimaxAgent:
    return MinimaxAgent(rules, depth_limit)


def create_alpha_beta_agent(
    rules: GameRules, depth_limit: int | None = None
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
