"""Play recorded match states one tick at a time."""

import pygame

from ..game.replay import Replay, ReplayFrame
from .control_panel import PanelState
from .pygame_view import PygameView


class ReplayPlayer:

    def __init__(self, replay: Replay, turn_ms: int) -> None:
        self._message = replay.message
        self._frames = list(replay.frames)
        self._turn_ms = turn_ms
        self._index = 0
        self._paused = False
        self._next_frame_at: int | None = None

    @property
    def turn_ms(self) -> int:
        return self._turn_ms

    @property
    def step(self) -> int:
        return self._index

    @property
    def total(self) -> int:
        return len(self._frames) - 1

    @property
    def frame(self) -> ReplayFrame:
        return self._frames[self._index]

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def message(self) -> str:
        return self._message

    def toggle(self, now_ms: int, *, restart_at_end: bool = True) -> None:
        if restart_at_end and self.step == self.total:
            self._index = 0
            self._paused = False
        else:
            self._paused = not self._paused
        self._next_frame_at = now_ms + self._turn_ms

    def seek(self, step: int) -> None:
        self._index = max(0, min(self.total, step))
        self._paused = True

    def append_live_frame(self, frame: ReplayFrame) -> None:
        self._frames.append(frame)
        self._index = self.total

    def handle_key(self, key: int, now_ms: int) -> None:
        if key == pygame.K_SPACE:
            self.toggle(now_ms)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            step = -1 if key == pygame.K_LEFT else 1
            self.seek(self.step + step)

    def update(self, now_ms: int) -> None:
        if self._paused or self.step == self.total:
            return
        if self._next_frame_at is None:
            self._next_frame_at = now_ms + self._turn_ms
        elif now_ms >= self._next_frame_at:
            self._index += 1
            self._next_frame_at = now_ms + self._turn_ms

    def draw(self, view: PygameView) -> None:
        view.set_turn_ms(self._turn_ms)
        finished = self.step == self.total
        view.draw(
            self.frame.state,
            panel=PanelState(
                message=self.message if finished else "Paused" if self.paused else "Playing replay",
                step=self.step,
                total=self.total,
                actions=self.frame.actions,
                playing=not finished and not self.paused,
                can_play=True,
                can_go_back=self.step > 0,
                can_go_forward=not finished,
                can_reset=True,
            ),
        )
