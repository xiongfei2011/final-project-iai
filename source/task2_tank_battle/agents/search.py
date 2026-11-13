"""Maximin search over simultaneous actions, with optional alpha-beta pruning."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from math import inf
from typing import Protocol, runtime_checkable

from ..config import DEFAULT_SEARCH_DEPTH
from ..game.actions import Action
from ..game.rules import GameRules
from ..game.state import GameState, GameStateKey
from .evaluation import Evaluator, HeuristicEvaluator


@runtime_checkable
class Agent(Protocol):
    def choose_action(self, state: GameState) -> Action | str | None: # Trả về action
        ...


@dataclass
class _SearchFrame:
    """Keep one board's progress while a child board is being evaluated."""

    state: GameState
    key: GameStateKey
    actions: Iterator[str]
    replies: list[str]
    alpha: float
    beta: float
    best_action: str | None = None
    best_score: float = -inf
    action: str | None = None
    reply_index: int = 0
    reply_score: float = inf
    reply_alpha: float = -inf
    reply_beta: float = inf


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

    def search(
        self, state: GameState, *, root_action: str | None = None
    ) -> tuple[str | None, float]:
        """Find the best action, or score one specified legal root action."""
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

        root_key = state.search_key()
        root = _SearchFrame(
            state, root_key, iter(actions), self._opponent_replies(state, max_player), -inf, inf
        )
        stack = [root]
        visited_states = {root_key}
        while True:
            frame = stack[-1]
            if frame.action is None:
                if frame.alpha < frame.beta:
                    frame.action = next(frame.actions, None)
                if frame.action is None:
                    stack.pop()
                    # Backtrack so sibling branches can evaluate this board again.
                    visited_states.remove(frame.key)
                    if not stack:
                        return frame.best_action, frame.best_score
                    self._record_reply(stack[-1], frame.best_score)
                    continue
                frame.reply_index = 0
                frame.reply_score = inf
                frame.reply_alpha, frame.reply_beta = frame.alpha, frame.beta

            if frame.reply_index == len(frame.replies) or frame.reply_beta <= frame.reply_alpha:
                if frame.reply_score > frame.best_score:
                    frame.best_action, frame.best_score = frame.action, frame.reply_score
                frame.alpha, frame.beta = self._update_bounds(
                    frame.alpha, frame.beta, frame.best_score, maximizing=True
                )
                frame.action = None
                continue

            reply = frame.replies[frame.reply_index]
            frame.reply_index += 1
            actions_for_tick = {max_player: frame.action, 1 - max_player: reply}
            child = self.rules.result_tick(frame.state, actions_for_tick)
            depth = len(stack)
            self.states_visited += 1
            self.max_depth = max(self.max_depth, depth)
            child_key = child.search_key()
            if child_key in visited_states:
                # A repetition contributes a draw to MIN's comparison.
                self._record_reply(frame, 0.0)
                continue

            score = self._leaf_value(child, max_player, depth)
            if score is not None:
                self._record_reply(frame, score)
            else:
                visited_states.add(child_key)
                stack.append(_SearchFrame(
                    child, child_key, iter(self.rules.actions(child, max_player)),
                    self._opponent_replies(child, max_player), frame.reply_alpha, frame.reply_beta,
                ))

    def _record_reply(self, frame: _SearchFrame, score: float) -> None:
        frame.reply_score = min(frame.reply_score, score)
        frame.reply_alpha, frame.reply_beta = self._update_bounds(
            frame.reply_alpha, frame.reply_beta, frame.reply_score, maximizing=False
        )

    def _leaf_value(self, state: GameState, max_player: int, depth: int) -> float | None:
        if self.rules.terminal_test(state):
            return self.rules.utility(state, max_player)
        if self.depth_limit is not None and depth >= self.depth_limit:
            if self.evaluator is not None:
                return self.evaluator.evaluate(state, max_player)
            return 0.0
        return None

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
