"""Pixel-art retro arcade battle controls and menu dispatch."""

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
    config.HEURISTIC_AGENT: "Heuristic",
    config.HEURISTIC_ALPHA_BETA_AGENT: "Heuristic+AB",
}

# Retro 8-bit / Arcade Palette
PIXEL_PANEL_BG = (22, 26, 38)
PIXEL_DARK = (13, 15, 22)
PIXEL_BORDER = (8, 10, 16)
PIXEL_HIGHLIGHT = (68, 80, 110)
PIXEL_SHADOW = (12, 14, 22)
PIXEL_TEXT = (242, 246, 252)
PIXEL_MUTED = (145, 160, 182)
PIXEL_GOLD = (255, 215, 0)
PIXEL_GREEN = (52, 211, 110)
PIXEL_YELLOW = (250, 204, 21)
PIXEL_RED = (248, 113, 113)


def draw_pixel_box(
    surface: pygame.Surface,
    rect: pygame.Rect,
    fill_color: tuple[int, int, int],
    border_color: tuple[int, int, int] = PIXEL_BORDER,
    highlight_color: tuple[int, int, int] | None = None,
    shadow_color: tuple[int, int, int] | None = None,
    border_width: int = 1,
) -> None:
    """Draw a classic 3D beveled pixel-art box with outer outline and inner bevel."""
    # Main fill
    pygame.draw.rect(surface, fill_color, rect)
    # Outer dark pixel border
    if border_width > 0:
        pygame.draw.rect(surface, border_color, rect, width=border_width)

    # Inner bevel highlights (top & left = light, bottom & right = dark)
    if highlight_color is not None and rect.width > 4 and rect.height > 4:
        inner = rect.inflate(-2 * border_width, -2 * border_width)
        # Top line
        pygame.draw.line(surface, highlight_color, inner.topleft, inner.topright, 1)
        # Left line
        pygame.draw.line(surface, highlight_color, inner.topleft, inner.bottomleft, 1)

    if shadow_color is not None and rect.width > 4 and rect.height > 4:
        inner = rect.inflate(-2 * border_width, -2 * border_width)
        # Bottom line
        pygame.draw.line(surface, shadow_color, (inner.left, inner.bottom - 1), (inner.right - 1, inner.bottom - 1), 1)
        # Right line
        pygame.draw.line(surface, shadow_color, (inner.right - 1, inner.top), (inner.right - 1, inner.bottom - 1), 1)


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
    """Retro 8-bit arcade control panel displayed on the left side."""

    def __init__(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        self._screen = screen
        self._rect = rect
        self._heading = pygame.font.Font(None, config.UI_FONT_SIZE + 4)
        self._font = pygame.font.Font(None, config.UI_FONT_SIZE - 4)
        self._tiny = pygame.font.Font(None, 14)
        self._open_selector: Selector | None = None
        self._option_offset = 0
        self._max_option_offset = 0
        self._buttons: list[tuple[pygame.Rect, str]] = []
        self._selectors: list[tuple[pygame.Rect, Selector]] = []
        self._options: list[tuple[pygame.Rect, tuple[Selector, str]]] = []
        # Text rendering cache: (text, font_id, color, shadow) → Surface
        self._text_cache: dict[tuple, pygame.Surface] = {}
        self._text_shadow_cache: dict[tuple, pygame.Surface] = {}

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

        # 1. Main Retro Bezel Cabinet
        draw_pixel_box(
            self._screen,
            self._rect,
            fill_color=PIXEL_PANEL_BG,
            border_color=PIXEL_BORDER,
            highlight_color=PIXEL_HIGHLIGHT,
            shadow_color=PIXEL_SHADOW,
            border_width=2,
        )

        # Pixel corner bolts
        self._draw_bolts()

        x, y = self._rect.x + 14, self._rect.y + 12
        width = self._rect.width - 28

        # Header Title Banner
        self._text("TANK BATTLE", self._heading, (x, y), width, PIXEL_GOLD, shadow=True)
        sub_title = "8-BIT RETRO COMBAT"
        self._text(sub_title, self._tiny, (x, y + 24), width, PIXEL_MUTED)

        # Step / Turn Status Banner
        status_box = pygame.Rect(x, y + 42, width, 48)
        draw_pixel_box(self._screen, status_box, fill_color=PIXEL_DARK, border_color=PIXEL_BORDER, border_width=1)

        step_text = f"STEP {panel.step}" if panel.total is None else f"STEP {panel.step}/{panel.total}"
        self._text(step_text, self._font, (x + 8, y + 48), width - 16, PIXEL_TEXT)
        self._status(panel.message, x + 8, y + 68, width - 16)

        map_row_height = 0
        if panel.map_name is not None:
            self._text("MAP", self._font, (x, y + 100), 40, PIXEL_TEXT)
            self._draw_selector(
                pygame.Rect(x + 44, y + 95, width - 44, 28),
                "map",
                panel.map_name,
                config.UI_PLAYER_COLORS[0],
                bool(panel.map_options),
            )
            map_row_height = 36

        # Player Cards (Player A & Player B)
        actions = dict(panel.actions)
        card_start_y = y + 98 + map_row_height
        for player, name in enumerate(config.PLAYER_NAMES):
            card = pygame.Rect(x, card_start_y + player * 128, width, 120)
            self._draw_player(card, state, panel, player, name, actions.get(player, ""))

        # Controls & Push-Buttons
        controls_y = card_start_y + 258
        play_label = "PAUSE  [Space]" if panel.playing else "PLAY  [Space]"
        play_rect = pygame.Rect(x, controls_y, width, 34)
        self._button(play_rect, play_label, "play", panel.can_play, is_primary=True)

        half = (width - 8) // 2
        button_rows = (
            (
                ("BACK", "backward", panel.can_go_back),
                ("FWD", "forward", panel.can_go_forward),
            ),
            (("RESET", "reset", panel.can_reset), ("QUIT", "quit", True)),
        )
        for row, buttons in enumerate(button_rows):
            for column, (label, command, enabled) in enumerate(buttons):
                rect = pygame.Rect(x + column * (half + 8), controls_y + 40 + 36 * row, half, 30)
                self._button(rect, label, command, enabled)

        # Options dropdown if selector is open
        self._draw_options(panel)

    def _draw_bolts(self) -> None:
        """Render 4 corner pixel bolts."""
        corners = [
            (self._rect.left + 5, self._rect.top + 5),
            (self._rect.right - 8, self._rect.top + 5),
            (self._rect.left + 5, self._rect.bottom - 8),
            (self._rect.right - 8, self._rect.bottom - 8),
        ]
        for bx, by in corners:
            pygame.draw.rect(self._screen, PIXEL_BORDER, (bx, by, 4, 4))
            pygame.draw.rect(self._screen, (170, 180, 200), (bx + 1, by + 1, 2, 2))

    def _draw_player(
        self,
        card: pygame.Rect,
        state: GameState,
        panel: PanelState,
        player: int,
        name: str,
        action: str,
    ) -> None:
        color = config.UI_PLAYER_COLORS[player]
        # Pixel player card box
        draw_pixel_box(
            self._screen,
            card,
            fill_color=PIXEL_DARK,
            border_color=color,
            highlight_color=PIXEL_HIGHLIGHT,
            shadow_color=PIXEL_BORDER,
            border_width=1,
        )

        x, y = card.x + 8, card.y + 7
        content_width = card.width - 16

        # Mini Pixel Tank Icon
        self._draw_mini_tank_icon(x, y + 1, color)

        # Player Name
        self._text(f"PLAYER {name}", self._font, (x + 18, y), 85, color, shadow=True)

        # Current action badge
        if action:
            act_txt = self._tiny.render(action[:10], False, PIXEL_TEXT)
            act_bg = act_txt.get_rect(topright=(card.right - 8, y + 2))
            pygame.draw.rect(self._screen, (35, 42, 60), act_bg.inflate(4, 2))
            pygame.draw.rect(self._screen, PIXEL_BORDER, act_bg.inflate(4, 2), 1)
            self._screen.blit(act_txt, act_bg)

        # Segmented Pixel Health Bars
        self._pixel_health(
            "TANK",
            state.tanks[player].hp,
            config.TANK_INITIAL_HP,
            x,
            y + 24,
            content_width,
            color,
        )
        self._pixel_health(
            "BASE",
            state.bases[player].hp,
            config.BASE_INITIAL_HP,
            x,
            y + 46,
            content_width,
            color,
        )

        # Agent selector
        if panel.agent_specs is not None:
            selector = pygame.Rect(x, y + 70, content_width, 27)
            spec = panel.agent_specs[player]
            label = AGENT_LABELS.get(spec, spec)
            self._draw_selector(selector, player, label, color, bool(panel.agent_options))

    def _draw_mini_tank_icon(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        """Render a small 12x10 pixel art tank icon."""
        # Tracks
        pygame.draw.rect(self._screen, (30, 35, 45), (x, y + 1, 3, 8))
        pygame.draw.rect(self._screen, (30, 35, 45), (x + 9, y + 1, 3, 8))
        # Hull
        pygame.draw.rect(self._screen, color, (x + 3, y + 2, 6, 6))
        # Turret
        pygame.draw.rect(self._screen, PIXEL_BORDER, (x + 4, y + 3, 4, 4))
        # Barrel
        pygame.draw.rect(self._screen, color, (x + 5, y - 1, 2, 4))

    def _pixel_health(
        self,
        label: str,
        hp: int,
        maximum: int,
        x: int,
        y: int,
        width: int,
        player_color: tuple[int, int, int],
    ) -> None:
        """Render retro segmented block health bar."""
        self._text(label, self._tiny, (x, y + 1), 35, PIXEL_MUTED)

        bar_x = x + 38
        bar_w = width - 78
        bar_h = 10
        bar_rect = pygame.Rect(bar_x, y + 1, bar_w, bar_h)

        # Dark slot track
        draw_pixel_box(self._screen, bar_rect, fill_color=(10, 12, 18), border_color=PIXEL_BORDER, border_width=1)

        # Segmented blocks
        num_blocks = maximum
        gap = 1
        block_w = max(2, (bar_w - (num_blocks - 1) * gap - 2) // num_blocks)

        curr_hp = max(0, min(hp, maximum))
        for i in range(num_blocks):
            bx = bar_x + 1 + i * (block_w + gap)
            by = y + 2
            block_rect = pygame.Rect(bx, by, block_w, bar_h - 2)
            if i < curr_hp:
                # Dynamic health color: Green -> Yellow -> Red
                if curr_hp > maximum * 0.6:
                    col = PIXEL_GREEN
                elif curr_hp > maximum * 0.3:
                    col = PIXEL_YELLOW
                else:
                    col = PIXEL_RED
                pygame.draw.rect(self._screen, col, block_rect)
            else:
                pygame.draw.rect(self._screen, (25, 28, 38), block_rect)

        # Value text
        self._text(f"{curr_hp}/{maximum}", self._tiny, (bar_rect.right + 6, y + 1), 34, PIXEL_TEXT)

    def _draw_selector(
        self,
        rect: pygame.Rect,
        selector: Selector,
        label: str,
        color: tuple[int, int, int],
        enabled: bool,
    ) -> None:
        is_open = self._open_selector == selector and enabled
        fill = (34, 40, 58) if is_open else (26, 30, 44)
        border = color if is_open else PIXEL_BORDER

        draw_pixel_box(
            self._screen,
            rect,
            fill_color=fill,
            border_color=border,
            highlight_color=PIXEL_HIGHLIGHT if not is_open else None,
            shadow_color=PIXEL_BORDER if not is_open else None,
            border_width=1,
        )

        self._text(label, self._tiny, (rect.x + 6, rect.y + 7), rect.width - 24, PIXEL_TEXT)
        if enabled:
            cx, cy = rect.right - 10, rect.centery
            # Pixel triangle arrow
            pts = [(cx - 4, cy - 2), (cx + 4, cy - 2), (cx, cy + 3)]
            pygame.draw.polygon(self._screen, color, pts)
            self._selectors.append((rect, selector))

    def _button(
        self,
        rect: pygame.Rect,
        label: str,
        command: str,
        enabled: bool,
        is_primary: bool = False,
    ) -> None:
        """Render retro arcade push button with beveled 3D look."""
        hovered = enabled and rect.collidepoint(pygame.mouse.get_pos())

        if not enabled:
            fill = (20, 22, 32)
            high = None
            shad = None
            txt_col = (75, 82, 98)
        elif is_primary:
            fill = (36, 120, 180) if hovered else (28, 95, 145)
            high = (70, 175, 240)
            shad = (12, 45, 75)
            txt_col = (255, 255, 255)
        elif hovered:
            fill = (45, 54, 78)
            high = (85, 100, 140)
            shad = (20, 24, 36)
            txt_col = PIXEL_TEXT
        else:
            fill = (32, 38, 56)
            high = (60, 72, 100)
            shad = (14, 18, 28)
            txt_col = PIXEL_TEXT

        draw_pixel_box(
            self._screen,
            rect,
            fill_color=fill,
            border_color=PIXEL_BORDER,
            highlight_color=high,
            shadow_color=shad,
            border_width=1,
        )

        if enabled:
            self._buttons.append((rect, command))

        # Text with 1px shadow (cached)
        sk = (label, id(self._font), PIXEL_BORDER)
        shadow_txt = self._text_shadow_cache.get(sk)
        if shadow_txt is None:
            shadow_txt = self._font.render(label, False, PIXEL_BORDER)
            self._text_shadow_cache[sk] = shadow_txt

        tk = (label, id(self._font), txt_col)
        surf = self._text_cache.get(tk)
        if surf is None:
            surf = self._font.render(label, False, txt_col)
            self._text_cache[tk] = surf

        text_center = rect.center
        if hovered:
            text_center = (text_center[0] + 1, text_center[1] + 1)
        self._screen.blit(shadow_txt, shadow_txt.get_rect(center=(text_center[0] + 1, text_center[1] + 1)))
        self._screen.blit(surf, surf.get_rect(center=text_center))

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
        self,
        anchor: pygame.Rect,
        selector: Selector,
        options: tuple[str, ...],
        selected: str | None,
    ) -> None:
        row_height = 26
        available = self._rect.bottom - anchor.bottom - 8
        visible = max(1, available // row_height)
        if len(options) > visible:
            visible = max(1, (available - 18) // row_height)
        self._max_option_offset = max(0, len(options) - visible)
        start = min(self._option_offset, self._max_option_offset)

        # Dropdown container outline
        total_h = visible * row_height + (18 if self._max_option_offset else 0)
        container = pygame.Rect(anchor.x, anchor.bottom, anchor.width, total_h)
        draw_pixel_box(self._screen, container, fill_color=PIXEL_DARK, border_color=PIXEL_BORDER, border_width=1)

        for index, value in enumerate(options[start:start + visible]):
            rect = pygame.Rect(anchor.x, anchor.bottom + index * row_height, anchor.width, row_height)
            active = value == selected or rect.collidepoint(pygame.mouse.get_pos())
            fill = (45, 56, 80) if active else PIXEL_DARK
            pygame.draw.rect(self._screen, fill, rect)
            pygame.draw.rect(self._screen, PIXEL_BORDER, rect, width=1)
            label = value if selector == "map" else AGENT_LABELS.get(value, value)
            self._text(label, self._tiny, (rect.x + 8, rect.y + 6), rect.width - 16, PIXEL_TEXT)
            self._options.append((rect, (selector, value)))

        if self._max_option_offset:
            hint = pygame.Rect(anchor.x, anchor.bottom + visible * row_height, anchor.width, 18)
            pygame.draw.rect(self._screen, PIXEL_DARK, hint)
            self._text(
                "Scroll for more", self._tiny, (hint.x + 8, hint.y + 2),
                hint.width - 16, PIXEL_MUTED,
            )

    def _status(self, message: str, x: int, y: int, width: int) -> None:
        words = message.split()
        split_at = len(words)
        for index in range(1, len(words) + 1):
            if self._tiny.size(" ".join(words[:index]))[0] > width:
                split_at = max(1, index - 1)
                break
        self._text(" ".join(words[:split_at]), self._tiny, (x, y), width, PIXEL_MUTED)
        self._text(" ".join(words[split_at:]), self._tiny, (x, y + 14), width, PIXEL_MUTED)

    def _text(
        self,
        text: str,
        font: pygame.font.Font,
        position: tuple[int, int],
        width: int,
        color: tuple[int, int, int],
        shadow: bool = False,
    ) -> None:
        # Truncation (use font.size which is fast C call)
        if font.size(text)[0] > width:
            while text and font.size(text + "...")[0] > width:
                text = text[:-1]
            text += "..."
        # Use id(font) as cheap key component
        fid = id(font)
        if shadow:
            sk = (text, fid, PIXEL_BORDER)
            s_surf = self._text_shadow_cache.get(sk)
            if s_surf is None:
                s_surf = font.render(text, False, PIXEL_BORDER)
                self._text_shadow_cache[sk] = s_surf
            self._screen.blit(s_surf, (position[0] + 1, position[1] + 1))
        key = (text, fid, color)
        surf = self._text_cache.get(key)
        if surf is None:
            surf = font.render(text, False, color)
            self._text_cache[key] = surf
        self._screen.blit(surf, position)
