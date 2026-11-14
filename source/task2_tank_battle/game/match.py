import sys
from queue import Empty, SimpleQueue
from threading import Thread

from .. import config
from ..agents.search import Agent
from .rules import GameRules
from .state import GameState, GameStateKey


_AgentReply = tuple[object, str | None, list[str]]


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
        self._pending: dict[int, SimpleQueue[_AgentReply]] = {}
        self._played_states: set[GameStateKey] = {state.search_key()}
        self._board_repeated = False
        self._last_actions: dict[int, str] = {}
        self._check_finished()

    def update(self, now_ms: int) -> None:
        if self.message is not None:
            return

        if self._next_tick_at is None:
            self._next_tick_at = now_ms + self.turn_ms
            self._request_actions()
            return
        if now_ms < self._next_tick_at:
            return

        replies = {}
        for player, queue in self._pending.items():
            try:
                replies[player] = queue.get_nowait()
            except Empty:
                continue
        for player in replies:
            del self._pending[player]

        self._apply_replies(replies)
        self._next_tick_at = now_ms + self.turn_ms
        if self.message is None:
            self._request_actions()

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
        for player in self.agents:
            if player not in self._pending:
                self._pending[player] = self._start_search(player)

    def _start_search(self, player: int) -> SimpleQueue[_AgentReply]:
        queue: SimpleQueue[_AgentReply] = SimpleQueue()
        Thread(
            target=self._request_action,
            args=(player, self.agent_state(player), queue),
            daemon=True,
        ).start()
        return queue

    def _apply_replies(self, replies: dict[int, _AgentReply]) -> dict[int, str] | None:
        actions = {}
        for player, (action, error, original_legal) in replies.items():
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

        return self._advance_tick(actions)

    def _advance_tick(self, actions: dict[int, str]) -> dict[int, str]:
        self.state = self.rules.result_tick(self.state, actions)
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
    ) -> None:
        replies.put(self._choose_action(player, state))

    def _choose_action(self, player: int, state: GameState) -> _AgentReply:
        legal = self.rules.actions(state, player)
        try:
            return self.agents[player].choose_action(state), None, legal
        except Exception as error:
            return None, f"{type(error).__name__}: {error}", legal
