"""Run the Pygame event loop and dispatch menu and keyboard controls."""

import pygame

from .. import config
from ..game.match import Match
from ..game.state import GameState
from .control_panel import PanelState
from .match_session import MatchSession
from .pygame_view import PygameView
from .replay_player import ReplayPlayer


KEY_COMMANDS = {
    pygame.K_SPACE: "play",
    pygame.K_LEFT: "backward",
    pygame.K_RIGHT: "forward",
    pygame.K_r: "reset",
    pygame.K_ESCAPE: "quit",
}


def run_window(
    state: GameState,
    match: Match | None = None,
    *,
    replay: ReplayPlayer | None = None,
    session: MatchSession | None = None,
) -> None:
    """Show a preview, live match, or replay until the window closes."""
    pygame.init()
    try:
        view = PygameView(state)
        shown_map = None
        if session is not None:
            shown_map = session.map_name
            view.set_turn_ms(session.turn_ms)
        elif replay is not None:
            view.set_turn_ms(replay.turn_ms)
        elif match is not None:
            view.set_turn_ms(match.turn_ms)
        clock = pygame.time.Clock()
        while True:
            now_ms = pygame.time.get_ticks()
            if session is not None:
                session.update(now_ms)
                if shown_map != session.map_name:
                    view = PygameView(session.state)
                    view.set_turn_ms(session.turn_ms)
                    shown_map = session.map_name
                view.draw(session.state, panel=session.panel_state())
            elif replay is not None:
                replay.update(now_ms)
                replay.draw(view)
            elif match is None:
                view.draw(state, panel=PanelState(message="Static preview"))
            else:
                match.update(now_ms)
                view.draw(
                    match.state,
                    panel=PanelState(message=match.message or "Live match", step=match.tick),
                )

            if _handle_events(view, session, replay, now_ms):
                break
            clock.tick(config.RENDER_FPS)
    finally:
        if session is not None:
            session.close()
        pygame.quit()


def _handle_events(
    view: PygameView, session: MatchSession | None, replay: ReplayPlayer | None, now_ms: int,
) -> bool:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
        command = None
        if event.type == pygame.KEYDOWN:
            command = KEY_COMMANDS.get(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            command = view.controls.click(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            view.controls.scroll(event.y)
        if command == "quit":
            return True
        if session is not None and command is not None:
            session.handle(command, now_ms)
        elif replay is not None:
            if command == "play":
                replay.toggle(now_ms)
            elif command == "reset":
                replay.seek(0)
            elif command in ("backward", "forward"):
                replay.seek(replay.step + (-1 if command == "backward" else 1))
    return False
