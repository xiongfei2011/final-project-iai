import sys
from queue import Empty, SimpleQueue
from threading import Thread
from time import perf_counter_ns
from typing import NamedTuple

from .. import config
from ..agents.search import Agent, SearchAgent
from .actions import Action
from .rules import GameRules
from .state import GameState, GameStateKey


class _AgentReply(NamedTuple):
    action: object
    error: str | None
    legal_actions: list[str]
    finished_at_ns: int


class Match:

    def __init__(
        self, state: GameState, rules: GameRules, agents: dict[int, Agent], turn_ms: int
    ) -> None:
        """Start with the given state, rules, and agents."""
        self.state = state
        self.rules = rules
        self.agents = agents
        self.turn_ms = turn_ms
        self.tick = 0
        self.message: str | None = None
        self._next_tick_at: int | None = None
        self._pending: dict[int, tuple[int, SimpleQueue[_AgentReply]]] = {}
        self._played_states: set[GameStateKey] = {state.search_key()}
        self._board_repeated = False
        self._last_actions: dict[int, str] = {}
        self._check_finished()

    def update(self, now_ms: int) -> dict[int, str] | None:
        if self.message is not None:
            return

        if self._next_tick_at is None:
            self._next_tick_at = now_ms + self.turn_ms
            self._request_actions()
            return
        if now_ms < self._next_tick_at:
            return

        replies = {}
        for player, (decision_tick, queue) in tuple(self._pending.items()):
            try:
                reply = queue.get_nowait()
            except Empty:
                continue
            del self._pending[player]
            if decision_tick == self.tick:
                replies[player] = reply

        actions = self._apply_replies(replies, fill_missing=True)
        self._next_tick_at = now_ms + self.turn_ms
        if self.message is None:
            self._request_actions()
        return actions

    def play_tick(
        self, planned_actions: dict[int, str] | None = None
    ) -> dict[int, str] | None:
        if self.message is not None:
            return None
        if planned_actions is not None:
            return self._advance_tick(planned_actions)

        searches = {player: self._start_search(player) for player in self.agents}
        replies = {player: queue.get() for player, queue in searches.items()}
        return self._apply_replies(replies)

    def agent_state(self, player: int) -> GameState:
        snapshot = self.state.clone()
        snapshot.current_turn = player
        snapshot.previous_action = self._last_actions.get(player)
        snapshot.played_states = (
            frozenset(key._replace(current_turn=player) for key in self._played_states)
            if self._board_repeated else frozenset()
        )
        return snapshot

    _agent_state = agent_state

    def _request_actions(self) -> None:
        budget_ms = self.turn_ms * config.LIVE_SEARCH_BUDGET_FRACTION
        for player in self.agents:
            if player not in self._pending:
                self._pending[player] = (self.tick, self._start_search(player, budget_ms))

    def _start_search(
        self, player: int, budget_ms: float | None = None
    ) -> SimpleQueue[_AgentReply]:
        queue: SimpleQueue[_AgentReply] = SimpleQueue()
        Thread(
            target=self._request_action,
            args=(player, self.agent_state(player), queue, budget_ms),
            daemon=True,
        ).start()
        return queue

    def _apply_replies(
        self, replies: dict[int, _AgentReply], *, fill_missing: bool = False
    ) -> dict[int, str] | None:
        actions = {}
        for player, (action, error, original_legal, _) in replies.items():
            player_name = config.PLAYER_NAMES[player]
            if error is not None:
                self.message = f"Player {player_name} agent error. See the terminal."
                print(f"Player {player_name} agent error: {error}", file=sys.stderr)
                return None
            if not isinstance(action, str) or action not in original_legal:
                self.message = (
                    f"Player {player_name} returned invalid action {action!r:.24}"
                )
                legal = ", ".join(original_legal)
                print(f"{self.message}. Legal actions: {legal}", file=sys.stderr)
                return None
            if action in self.rules.actions(self.state, player):
                actions[player] = action

        if fill_missing:
            for player in self.agents:
                actions.setdefault(player, Action.STAY.value)
        first_reply = None
        if self.rules.prioritize_first_reply and len(replies) == 2:
            first_reply = min(replies, key=lambda player: (replies[player].finished_at_ns, player))
        return self._advance_tick(actions, first_reply=first_reply)

    def _advance_tick(
        self, actions: dict[int, str], *, first_reply: int | None = None
    ) -> dict[int, str]:
        self.state = self.rules.result_tick(self.state, actions, first_reply=first_reply)
        self._last_actions = actions.copy()
        key = self.state.search_key()
        self._board_repeated = key in self._played_states
        self._played_states.add(key)
        self.tick += 1
        self._check_finished()
        return actions

    def _check_finished(self) -> None:
        if self.rules.terminal_test(self.state):
            score = self.rules.utility(self.state, 0)
            if score == 0:
                self.message = "Game over - Draw"
            else:
                winner = 0 if score > 0 else 1
                self.message = f"Game over - Player {config.PLAYER_NAMES[winner]} wins"

    def _request_action(
        self,
        player: int,
        state: GameState,
        replies: SimpleQueue[_AgentReply],
        budget_ms: float | None,
    ) -> None:
        replies.put(self._choose_action(player, state, budget_ms))

    def _choose_action(
        self, player: int, state: GameState, budget_ms: float | None
    ) -> _AgentReply:
        legal = self.rules.actions(state, player)
        agent = self.agents[player]
        try:
            if budget_ms is not None and isinstance(agent, SearchAgent):
                action = agent.choose_action_with_budget(state, budget_ms)
            else:
                action = agent.choose_action(state)
            return _AgentReply(action, None, legal, perf_counter_ns())
        except Exception as error:
            return _AgentReply(None, f"{type(error).__name__}: {error}", legal, perf_counter_ns())
