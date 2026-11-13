"""Manage map and agent selection, match planning, and playback."""

import sys
from collections.abc import Callable, Mapping
from queue import Empty, SimpleQueue
from threading import Event, Thread

from ..agents.loader import BUILT_IN_AGENTS
from ..game.match import Match
from ..game.replay import Replay, ReplayFrame, record_match
from ..game.state import GameState
from .control_panel import PanelCommand, PanelState
from .replay_player import ReplayPlayer


class MatchSession:
    def __init__(
        self, state: GameState, agent_specs: tuple[str, str], turn_ms: int,
        make_match: Callable[[GameState, tuple[str, str]], Match], *,
        map_name: str, map_loaders: Mapping[str, Callable[[], GameState]],
        live: bool = False, preview: bool = False,
    ) -> None:
        self._initial_state = state
        self._map_name = map_name
        self._map_loaders = map_loaders
        self._agent_specs = agent_specs
        self._agent_options = tuple(dict.fromkeys((*BUILT_IN_AGENTS, *agent_specs)))
        self.turn_ms = turn_ms
        self._make_match = make_match
        self._live = live
        self._preview = preview
        self._player: ReplayPlayer | None = None
        self._match: Match | None = None
        self._single_step = False
        self._notice = ""
        self._stop_planning: Event | None = None
        self._plan_result: SimpleQueue[Replay | Exception] = SimpleQueue()

    @property
    def state(self) -> GameState:
        return self._initial_state if self._player is None else self._player.frame.state

    @property
    def map_name(self) -> str:
        return self._map_name

    def handle(self, command: PanelCommand, now_ms: int) -> None:
        if isinstance(command, tuple):
            selector, value = command
            if selector == "map":
                self._select_map(value)
            elif self._stop_planning is None and value in self._agent_options:
                current = list(self._agent_specs)
                if current[selector] != value:
                    current[selector] = value
                    self._agent_specs = (current[0], current[1])
                    self.reset()
        elif command == "reset":
            self.reset()
        elif command == "play":
            self._toggle_play(now_ms)
        elif command in ("backward", "forward") and self._player is not None:
            player = self._player
            self._single_step = (
                command == "forward" and player.step == player.total
                and self._match is not None and self._match.message is None
            )
            player.seek(player.step + (-1 if command == "backward" else 1))

    def _select_map(self, name: str) -> None:
        if name == self._map_name or name not in self._map_loaders:
            return
        try:
            state = self._map_loaders[name]()
        except ValueError as error:
            self._notice = f"Could not load {name}. See terminal."
            print(error, file=sys.stderr)
            return
        self.reset()
        self._initial_state = state
        self._map_name = name

    def reset(self) -> None:
        self.close()
        self._player = None
        self._match = None
        self._single_step = False
        self._notice = ""

    def close(self) -> None:
        if self._stop_planning is not None:
            self._stop_planning.set()

    def _toggle_play(self, now_ms: int) -> None:
        if self._preview or self._stop_planning is not None:
            return
        self._single_step = False
        self._notice = ""
        if self._player is not None:
            active_live_match = self._match is not None and self._match.message is None
            self._player.toggle(now_ms, restart_at_end=not active_live_match)
            return

        if self._live:
            try:
                self._match = self._make_match(self._initial_state, self._agent_specs)
            except Exception as error:
                self._notice = str(error)
                return
            self._player = ReplayPlayer(Replay((ReplayFrame(self._match.state),), ""), self.turn_ms)
        else:
            self._stop_planning = Event()
            Thread(
                target=self._plan,
                args=(self._initial_state, self._agent_specs, self._stop_planning),
                daemon=True,
            ).start()

    def _plan(self, state: GameState, specs: tuple[str, str], stop: Event) -> None:
        try:
            match = self._make_match(state, specs)
            replay = record_match(
                match, reuse_known_actions=all(spec in BUILT_IN_AGENTS for spec in specs),
                stop_requested=stop.is_set,
            )
        except Exception as error:
            self._plan_result.put(error)
        else:
            self._plan_result.put(replay)

    def _receive_plan(self) -> None:
        if self._stop_planning is None:
            return
        try:
            result = self._plan_result.get_nowait()
        except Empty:
            return
        canceled = self._stop_planning.is_set()
        self._stop_planning = None
        if not canceled:
            if isinstance(result, Exception):
                self._notice = str(result)
            else:
                self._player = ReplayPlayer(result, self.turn_ms)

    def update(self, now_ms: int) -> None:
        self._receive_plan()
        player, match = self._player, self._match
        if player is None:
            return
        if match is not None and match.message is None and player.step == player.total:
            if not player.paused or self._single_step:
                match.update(now_ms)
                if match.tick > player.total:
                    player.append_live_frame(ReplayFrame(match.state))
                    self._single_step = False
        else:
            player.update(now_ms)

    def panel_state(self) -> PanelState:
        player, match = self._player, self._match
        planning = self._stop_planning is not None
        map_options = tuple(self._map_loaders)
        if self._preview:
            return PanelState(
                message=self._notice or "Static preview",
                map_name=self._map_name, map_options=map_options,
            )
        if player is None:
            message = "Choose an algorithm for each tank, then press Play."
            if self._stop_planning is not None:
                message = (
                    "Waiting for the current search to stop."
                    if self._stop_planning.is_set() else "Planning both AI players..."
                )
            return PanelState(
                message=self._notice or message, agent_specs=self._agent_specs,
                map_name=self._map_name, map_options=map_options,
                agent_options=() if planning else self._agent_options,
                can_play=not planning, can_reset=planning or bool(self._notice),
            )

        active_live_match = match is not None and match.message is None
        finished = not active_live_match and player.step == player.total
        if finished:
            message = player.message if match is None else match.message or ""
        elif self._single_step:
            message = "Advancing one tick..."
        elif player.paused:
            message = "Paused"
        else:
            message = "Live match" if active_live_match else "Playing replay"
        can_go_forward = player.step < player.total or (active_live_match and not self._single_step)
        return PanelState(
            message=self._notice or message, step=player.step,
            map_name=self._map_name, map_options=map_options,
            total=None if active_live_match else player.total,
            actions=player.frame.actions, agent_specs=self._agent_specs,
            agent_options=self._agent_options, playing=not finished and not player.paused,
            can_play=True, can_go_back=player.step > 0,
            can_go_forward=can_go_forward,
            can_reset=True,
        )
