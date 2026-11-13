"""Draw the battle controls and translate menu clicks into commands."""

from dataclasses import dataclass
from typing import Literal

import pygame

from .. import config
from ..game.state import GameState

Selector = int | Literal["map"]
PanelCommand = str | tuple[Selector, str]


AGENT_LABELS = {
    config.MINIMAX_AGENT: "Minimax",
    config.ALPHA_BETA_AGENT: "Alpha-Beta",
    config.HEURISTIC_AGENT: "Heuristic Minimax",
    config.HEURISTIC_ALPHA_BETA_AGENT: "Heuristic Minimax + Alpha-Beta",
}


@dataclass(frozen=True)
class PanelState:
    message: str = ""
    step: int = 0
    total: int | None = None
    actions: tuple[tuple[int, str], ...] = ()
    map_name: str | None = None
    map_options: tuple[str, ...] = ()
    agent_specs: tuple[str, str] | None = None
    agent_options: tuple[str, ...] = ()
    playing: bool = False
    can_play: bool = False
    can_go_back: bool = False
    can_go_forward: bool = False
    can_reset: bool = False


class ControlPanel:
    def __init__(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        self._screen = screen
        self._rect = rect
        self._heading = pygame.font.Font(None, config.UI_FONT_SIZE + 4)
        self._font = pygame.font.Font(None, config.UI_FONT_SIZE - 4)
        self._small = pygame.font.Font(None, config.UI_FONT_SIZE - 7)
        self._open_selector: Selector | None = None
        self._option_offset = 0
        self._max_option_offset = 0
        self._buttons: list[tuple[pygame.Rect, str]] = []
        self._selectors: list[tuple[pygame.Rect, Selector]] = []
        self._options: list[tuple[pygame.Rect, tuple[Selector, str]]] = []

    def click(self, position: tuple[int, int]) -> PanelCommand | None:
        for rect, choice in self._options:
            if rect.collidepoint(position):
                self._open_selector = None
                return choice
        for rect, selector in self._selectors:
            if rect.collidepoint(position):
                self._open_selector = None if self._open_selector == selector else selector
                self._option_offset = 0
                return None
        self._open_selector = None
        for rect, command in self._buttons:
            if rect.collidepoint(position):
                return command
        return None

    def scroll(self, delta: int) -> None:
        if self._open_selector is not None:
            self._option_offset = max(0, min(self._max_option_offset, self._option_offset - delta))

    def draw(self, state: GameState, panel: PanelState) -> None:
        self._buttons.clear()
        self._selectors.clear()
        self._options.clear()
        if isinstance(self._open_selector, int) and not panel.agent_options:
            self._open_selector = None
        pygame.draw.rect(self._screen, config.UI_PANEL, self._rect, border_radius=12)
        pygame.draw.rect(self._screen, config.UI_MUTED, self._rect, width=1, border_radius=12)

        x, y = self._rect.x + 14, self._rect.y + 12
        width = self._rect.width - 28
        step = f"Step {panel.step}" if panel.total is None else f"Step {panel.step} / {panel.total}"
        self._text(step, self._heading, (x, y), width, config.UI_TEXT)
        self._status(panel.message, x, y + 30, width)

        map_row_height = 0
        if panel.map_name is not None:
            self._text("Map", self._font, (x, y + 74), 40, config.UI_TEXT)
            self._draw_selector(
                pygame.Rect(x + 43, y + 66, width - 43, 29), "map", panel.map_name,
                config.UI_PLAYER_COLORS[0], bool(panel.map_options),
            )
            map_row_height = 37

        actions = dict(panel.actions)
        for player, name in enumerate(config.PLAYER_NAMES):
            card = pygame.Rect(x, y + 73 + map_row_height + player * 131, width, 122)
            self._draw_player(card, state, panel, player, name, actions.get(player, ""))

        controls_y = y + 342 + map_row_height
        play_label = "Pause  [Space]" if panel.playing else "Play  [Space]"
        play_rect = pygame.Rect(x, controls_y, width, 36)
        self._button(play_rect, play_label, "play", panel.can_play)
        half = (width - 8) // 2
        button_rows = (
            (
                ("Backward", "backward", panel.can_go_back),
                ("Forward", "forward", panel.can_go_forward),
            ),
            (("Reset", "reset", panel.can_reset), ("Quit", "quit", True)),
        )
        for row, buttons in enumerate(button_rows):
            for column, (label, command, enabled) in enumerate(buttons):
                rect = pygame.Rect(x + column * (half + 8), controls_y + 44 + 40 * row, half, 32)
                self._button(rect, label, command, enabled)
        self._draw_options(panel)

    def _draw_player(
        self, card: pygame.Rect, state: GameState, panel: PanelState,
        player: int, name: str, action: str,
    ) -> None:
        color = config.UI_PLAYER_COLORS[player]
        pygame.draw.rect(self._screen, config.UI_BACKGROUND, card, border_radius=8)
        pygame.draw.rect(self._screen, color, card, width=1, border_radius=8)
        x, y = card.x + 11, card.y + 9
        self._text(f"PLAYER {name}", self._font, (x, y), 105, color)
        if action:
            label = self._small.render(action, True, config.UI_MUTED)
            self._screen.blit(label, label.get_rect(topright=(card.right - 11, y + 2)))
        content_width = card.width - 22
        self._health(
            "Tank", state.tanks[player].hp, config.TANK_INITIAL_HP, x, y + 25, content_width, color
        )
        self._health(
            "Base", state.bases[player].hp, config.BASE_INITIAL_HP, x, y + 48, content_width, color
        )
        if panel.agent_specs is None:
            return

        selector = pygame.Rect(x, y + 73, content_width, 29)
        spec = panel.agent_specs[player]
        self._draw_selector(
            selector, player, AGENT_LABELS.get(spec, spec), color, bool(panel.agent_options)
        )

    def _draw_selector(
        self, rect: pygame.Rect, selector: Selector, label: str,
        color: tuple[int, int, int], enabled: bool,
    ) -> None:
        pygame.draw.rect(self._screen, config.UI_PANEL, rect, border_radius=5)
        border = color if self._open_selector == selector and enabled else config.UI_MUTED
        pygame.draw.rect(self._screen, border, rect, width=1, border_radius=5)
        self._text(
            label, self._small, (rect.x + 8, rect.y + 7), rect.width - 34, config.UI_TEXT
        )
        if enabled:
            cx, cy = rect.right - 13, rect.centery
            arrow = ((cx - 4, cy - 2), (cx + 4, cy - 2), (cx, cy + 3))
            pygame.draw.polygon(self._screen, color, arrow)
            self._selectors.append((rect, selector))

    def _health(
        self, name: str, hp: int, maximum: int, x: int, y: int, width: int,
        color: tuple[int, int, int],
    ) -> None:
        self._text(name, self._small, (x, y), 35, config.UI_MUTED)
        bar = pygame.Rect(x + 39, y + 2, width - 83, 10)
        pygame.draw.rect(self._screen, config.UI_PANEL, bar, border_radius=3)
        fill = bar.copy()
        fill.width = int(bar.width * min(max(hp, 0), maximum) / maximum)
        if fill.width:
            pygame.draw.rect(self._screen, color, fill, border_radius=3)
        self._text(f"{hp}/{maximum}", self._small, (bar.right + 8, y), 38, config.UI_TEXT)

    def _button(self, rect: pygame.Rect, label: str, command: str, enabled: bool) -> None:
        hovered = enabled and rect.collidepoint(pygame.mouse.get_pos())
        color = config.UI_PLAYER_COLORS[0] if command == "play" and enabled else config.UI_MUTED
        fill = config.UI_CELL_COLORS[1] if hovered else config.UI_BACKGROUND
        pygame.draw.rect(self._screen, fill, rect, border_radius=6)
        if enabled:
            pygame.draw.rect(self._screen, color, rect, width=1, border_radius=6)
            self._buttons.append((rect, command))
        text = self._font.render(label, True, config.UI_TEXT if enabled else config.UI_MUTED)
        self._screen.blit(text, text.get_rect(center=rect.center))

    def _draw_options(self, panel: PanelState) -> None:
        self._max_option_offset = 0
        for rect, selector in self._selectors:
            if selector != self._open_selector:
                continue
            if selector == "map":
                self._draw_option_list(rect, selector, panel.map_options, panel.map_name)
            elif panel.agent_specs is not None:
                self._draw_option_list(
                    rect, selector, panel.agent_options, panel.agent_specs[selector]
                )
            break

    def _draw_option_list(
        self, anchor: pygame.Rect, selector: Selector, options: tuple[str, ...],
        selected: str | None,
    ) -> None:
        row_height = 27
        available = self._rect.bottom - anchor.bottom - 8
        visible = max(1, available // row_height)
        if len(options) > visible:
            visible = max(1, (available - 18) // row_height)
        self._max_option_offset = max(0, len(options) - visible)
        start = min(self._option_offset, self._max_option_offset)
        for index, value in enumerate(options[start:start + visible]):
            rect = pygame.Rect(anchor.x, anchor.bottom + index * row_height, anchor.width, row_height)
            active = value == selected or rect.collidepoint(pygame.mouse.get_pos())
            fill = config.UI_CELL_COLORS[1] if active else config.UI_BACKGROUND
            pygame.draw.rect(self._screen, fill, rect)
            pygame.draw.rect(self._screen, config.UI_MUTED, rect, width=1)
            label = value if selector == "map" else AGENT_LABELS.get(value, value)
            self._text(label, self._small, (rect.x + 8, rect.y + 7), rect.width - 16, config.UI_TEXT)
            self._options.append((rect, (selector, value)))
        if self._max_option_offset:
            hint = pygame.Rect(anchor.x, anchor.bottom + visible * row_height, anchor.width, 18)
            pygame.draw.rect(self._screen, config.UI_BACKGROUND, hint)
            self._text(
                "Scroll for more", self._small, (hint.x + 8, hint.y + 2),
                hint.width - 16, config.UI_MUTED,
            )

    def _status(self, message: str, x: int, y: int, width: int) -> None:
        words = message.split()
        split_at = len(words)
        for index in range(1, len(words) + 1):
            if self._small.size(" ".join(words[:index]))[0] > width:
                split_at = max(1, index - 1)
                break
        self._text(" ".join(words[:split_at]), self._small, (x, y), width, config.UI_MUTED)
        self._text(" ".join(words[split_at:]), self._small, (x, y + 17), width, config.UI_MUTED)

    def _text(
        self, text: str, font: pygame.font.Font, position: tuple[int, int],
        width: int, color: tuple[int, int, int],
    ) -> None:
        if font.size(text)[0] > width:
            while text and font.size(text + "...")[0] > width:
                text = text[:-1]
            text += "..."
        self._screen.blit(font.render(text, True, color), position)
