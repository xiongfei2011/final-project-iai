"""Record an AI match as a sequence of board states."""

from collections.abc import Callable
from dataclasses import dataclass

from ..config import REPLAY_MAX_TURNS
from .actions import Action
from .match import Match
from .state import GameState


@dataclass(frozen=True)
class ReplayFrame:

    state: GameState
    actions: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class Replay:
    frames: tuple[ReplayFrame, ...]
    message: str


def record_match(
    match: Match,
    max_turns: int = REPLAY_MAX_TURNS,
    *,
    reuse_known_actions: bool = False,
    stop_requested: Callable[[], bool] | None = None,
) -> Replay:
    """Plan a match to its result or step limit before playing the frames.

    Reuse decisions only for agents whose choices depend solely on the board.
    """
    frames = [ReplayFrame(match.state.clone())]

    for _ in range(max_turns):
        if stop_requested is not None and stop_requested():
            return Replay(tuple(frames), "Planning canceled")

        planned_actions = None
        if reuse_known_actions:
            for index, frame in enumerate(frames[:-1]):
                if frame.state == match.state:
                    planned_actions = dict(frames[index + 1].actions)
                    break

        actions = match.play_tick(planned_actions)
        if actions is None:
            break

        action_names = tuple(
            (player, action.value if isinstance(action, Action) else action)
            for player, action in sorted(actions.items())
        )
        frames.append(ReplayFrame(match.state.clone(), action_names))
        if match.message is not None:
            break

    message = match.message or f"Replay stopped: tick limit reached ({max_turns})"
    return Replay(tuple(frames), message)
