"""Pixel-art retro arcade Pygame view for Tank Battle.

Features:
- Left-side retro arcade control panel with 3D beveled pixel buttons & cards
- Full pixel-art aesthetics for tanks, bases, brick walls, and projectiles
- Per-entity segmented pixel health bars directly on the battlefield
- Damage hit-flash effects (white/red flashing) and floating '-1' combat numbers
- Smooth quintic smootherstep motion interpolation for 60 FPS gameplay
"""

import math
import pygame
from pygame.math import Vector2, clamp

from .. import config
from ..game.actions import Direction
from ..game.entities import Position
from ..game.state import GameState
from .control_panel import ControlPanel, PanelState, draw_pixel_box
from .effects import ParticleManager
from .geometry import lerp_angle, smootherstep

# Pixel Art Retro Arcade Palette
RETRO_BG = (14, 16, 24)
RETRO_BOARD_BORDER = (10, 12, 18)
RETRO_BOARD_BG = (18, 22, 32)
RETRO_CELL_A = (28, 34, 48)
RETRO_CELL_B = (34, 40, 56)
RETRO_GRID_LINE = (20, 24, 34)

RETRO_PLAYER_A = (34, 180, 240)   # Cyan 8-bit
RETRO_PLAYER_B = (248, 128, 40)   # Orange 8-bit
RETRO_HIGHLIGHT_A = (130, 225, 255)
RETRO_SHADOW_A = (14, 85, 140)
RETRO_HIGHLIGHT_B = (255, 185, 90)
RETRO_SHADOW_B = (140, 50, 15)

RETRO_WALL_BRICK = (175, 75, 45)
RETRO_WALL_LIGHT = (215, 115, 75)
RETRO_WALL_DARK = (105, 35, 20)
RETRO_WALL_MORTAR = (30, 32, 40)

RETRO_HP_GREEN = (52, 211, 110)
RETRO_HP_YELLOW = (250, 204, 21)
RETRO_HP_RED = (248, 113, 113)


class PygameView:
    """Renders the battlefield, pixel-art armor units, per-entity HP, and combat dynamics."""

    def __init__(self, state: GameState) -> None:
        self.rows = state.game_map.height
        self.columns = state.game_map.width
        padding = config.UI_PADDING
        panel_width = config.UI_CONTROL_PANEL_WIDTH
        desktop_width = pygame.display.get_desktop_sizes()[0][0]

        # Dynamically scale cell size
        self.cell_size = max(
            config.UI_MIN_CELL_SIZE,
            min(
                config.UI_MAX_CELL_SIZE,
                config.UI_BOARD_MAX_WIDTH // self.columns,
                (desktop_width - panel_width - 3 * padding) // self.columns,
                config.UI_BOARD_MAX_HEIGHT // self.rows,
            ),
        )

        board_width = self.columns * self.cell_size
        board_height = self.rows * self.cell_size

        window_width = max(
            config.UI_MIN_WINDOW_WIDTH,
            board_width + panel_width + 3 * padding,
        )
        window_height = max(board_height + 48, config.UI_CONTROL_PANEL_HEIGHT + 2 * padding)

        self.screen = pygame.display.set_mode((window_width, window_height))
        pygame.display.set_caption(f"{config.WINDOW_TITLE} - 8-Bit Retro Pixel Combat")

        # LEFT SIDE MENU PANEL LAYOUT
        panel_x = padding
        panel_rect = pygame.Rect(panel_x, padding, panel_width, window_height - 2 * padding)
        self.controls = ControlPanel(self.screen, panel_rect)

        # RIGHT SIDE BOARD LAYOUT
        board_area_x = panel_x + panel_width + padding
        board_area_w = window_width - board_area_x - padding
        self.board_x = board_area_x + max(0, (board_area_w - board_width) // 2)
        self.board_y = max(padding, (window_height - board_height) // 2)

        # Fonts
        self.font = pygame.font.Font(None, config.UI_FONT_SIZE)
        self.tiny_font = pygame.font.Font(None, 13)

        self.turn_ms = config.DEFAULT_TURN_MS
        self._last_step = 0

        # Damage hit-flash timers (records timestamp of last hit)
        self.tank_hit_flash: dict[int, int] = {0: 0, 1: 0}
        self.base_hit_flash: dict[int, int] = {0: 0, 1: 0}
        self.wall_hit_flash: dict[Position, int] = {}

        self._reset_dynamics(state)

    def _reset_dynamics(self, state: GameState) -> None:
        """Clear visual effects and snap entities to current board."""
        self.particle_mgr = ParticleManager()

        now_ms = pygame.time.get_ticks()
        self.last_update_ms = now_ms
        self.last_tick_time = now_ms
        self._shown_state: GameState | None = None
        self.last_state_signature: tuple | None = None

        # Tank smooth motion interpolation
        self.tank_prev_grid_pos: dict[int, Position] = {
            p: t.position for p, t in state.tanks.items()
        }
        self.tank_move_from: dict[int, Vector2] = {}
        self.tank_move_to: dict[int, Vector2] = {}
        self.tank_move_start: dict[int, int] = {}
        self.tank_is_moving: dict[int, bool] = {0: False, 1: False}
        self.tank_move_progress: dict[int, float] = {0: 1.0, 1: 1.0}

        self.tank_rot_from: dict[int, float] = {}
        self.tank_rot_to: dict[int, float] = {}
        self.tank_rot_start: dict[int, int] = {}

        self.tank_visual_pos: dict[int, Vector2] = {}
        self.tank_target_pos: dict[int, Vector2] = {}
        self.tank_visual_angle: dict[int, float] = {}
        self.tank_target_angle: dict[int, float] = {}
        self.tank_recoil: dict[int, float] = {0: 0.0, 1: 0.0}

        for player, tank in state.tanks.items():
            init_center = self._tile_center_vec(tank.position)
            self.tank_move_from[player] = Vector2(init_center)
            self.tank_move_to[player] = Vector2(init_center)
            self.tank_move_start[player] = 0
            self.tank_visual_pos[player] = Vector2(init_center)
            self.tank_target_pos[player] = Vector2(init_center)
            init_ang = self._direction_to_angle(tank.direction)
            self.tank_rot_from[player] = init_ang
            self.tank_rot_to[player] = init_ang
            self.tank_rot_start[player] = 0
            self.tank_visual_angle[player] = init_ang
            self.tank_target_angle[player] = init_ang

        self.prev_tank_hp = {p: t.hp for p, t in state.tanks.items()}
        self.prev_base_hp = {p: b.hp for p, b in state.bases.items()}
        self.prev_wall_hp = {
            pos: w.hp for pos, w in state.game_map.walls.items() if not w.is_destroyed
        }

    def set_turn_ms(self, turn_ms: int) -> None:
        if turn_ms > 0:
            self.turn_ms = turn_ms

    def _direction_to_angle(self, direction: Direction) -> float:
        dr, dc = direction.delta
        return math.degrees(math.atan2(dr, dc))

    def _tile_center_vec(self, position: Position) -> Vector2:
        row, col = position
        cx = self.board_x + (col - 0.5) * self.cell_size
        cy = self.board_y + (row - 0.5) * self.cell_size
        return Vector2(cx, cy)

    def _tile(self, position: Position) -> pygame.Rect:
        row, col = position
        return pygame.Rect(
            self.board_x + (col - 1) * self.cell_size,
            self.board_y + (row - 1) * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def draw(
        self,
        state: GameState,
        message: str | None = None,
        *,
        show_turn: bool = True,
        turn_label: str | None = None,
        panel: PanelState | None = None,
    ) -> None:
        """Render frame with pixel graphics, per-entity HP bars, and damage flashes."""
        if panel is None:
            panel = PanelState(message=message or (turn_label if show_turn else None) or "")
        if panel.step < self._last_step:
            self._reset_dynamics(state)
        self._last_step = panel.step

        now_ms = pygame.time.get_ticks()
        dt = clamp((now_ms - self.last_update_ms) / 1000.0, 0.001, 0.08)
        self.last_update_ms = now_ms

        # 1. Update dynamics & damage events
        self._update_dynamics(state, dt, now_ms)

        # 2. Clear Screen with dark retro backdrop
        self.screen.fill(RETRO_BG)

        # 3. Draw Left-Side Pixel Control Panel
        self.controls.draw(state, panel)

        # 4. Draw Right-Side Pixel Battlefield
        offset = Vector2(0.0, 0.0)
        self._draw_pixel_board(offset)
        self._draw_pixel_walls(state, offset, now_ms)
        self._draw_pixel_bases(state, offset, now_ms)
        self._draw_pixel_tanks(state, offset, dt, now_ms)
        self._draw_pixel_bullets(state, offset, now_ms)

        # 5. Draw Particles & Floating Damage Numbers on top
        self.particle_mgr.draw(self.screen)

        pygame.display.flip()

    def _update_dynamics(self, state: GameState, dt: float, now_ms: int) -> None:
        """Update physics, floating text arcs, and detect damage hits for flashing."""
        self.particle_mgr.update(dt)

        state_sig = (
            state.current_turn,
            tuple(t.position for t in state.tanks.values()),
            tuple(t.direction for t in state.tanks.values()),
            tuple(b.position for b in state.bullets),
        )
        new_frame = state is not self._shown_state
        if new_frame or state_sig != self.last_state_signature:
            if self.last_state_signature is not None:
                interval = now_ms - self.last_tick_time
                if 80 <= interval <= 2500:
                    self.turn_ms = interval
            self.last_tick_time = now_ms
            self.last_state_signature = state_sig
            self._shown_state = state

        # A. Detect Tank Movements & Rotations
        for player, tank in state.tanks.items():
            prev_cell = self.tank_prev_grid_pos.get(player, tank.position)
            if tank.position != prev_cell:
                self.tank_move_from[player] = Vector2(self.tank_visual_pos[player])
                self.tank_move_to[player] = self._tile_center_vec(tank.position)
                self.tank_move_start[player] = now_ms
                self.tank_prev_grid_pos[player] = tank.position

            target_ang = self._direction_to_angle(tank.direction)
            if abs(target_ang - self.tank_rot_to.get(player, target_ang)) > 0.01:
                self.tank_rot_from[player] = self.tank_visual_angle[player]
                self.tank_rot_to[player] = target_ang
                self.tank_rot_start[player] = now_ms

            # Quintic smootherstep translation across full step duration (no end-of-tick freeze)
            elapsed_move = now_ms - self.tank_move_start.get(player, 0)
            move_duration = max(60.0, float(self.turn_ms))
            move_t = clamp(elapsed_move / move_duration, 0.0, 1.0)
            smooth_move_t = smootherstep(move_t)
            self.tank_visual_pos[player] = self.tank_move_from[player].lerp(
                self.tank_move_to[player], smooth_move_t
            )
            self.tank_is_moving[player] = (move_t < 1.0)
            self.tank_move_progress[player] = smooth_move_t

            # Angular rotation
            elapsed_rot = now_ms - self.tank_rot_start.get(player, 0)
            rot_duration = max(40.0, self.turn_ms * 0.55)
            rot_t = clamp(elapsed_rot / rot_duration, 0.0, 1.0)
            smooth_rot_t = smootherstep(rot_t)
            self.tank_visual_angle[player] = lerp_angle(
                self.tank_rot_from[player], self.tank_rot_to[player], smooth_rot_t
            )

            # Recoil recovery
            self.tank_recoil[player] = clamp(
                self.tank_recoil[player] - dt * 5.0, 0.0, 1.0
            )

        # B. Detect Damage Hits -> Trigger Hit Flash & Floating Damage Numbers
        # 1. Walls
        for pos, wall in state.game_map.walls.items():
            old_hp = self.prev_wall_hp.get(pos, wall.hp)
            if wall.hp < old_hp:
                dmg = old_hp - wall.hp
                center = self._tile_center_vec(pos)
                self.wall_hit_flash[pos] = now_ms
                self.particle_mgr.spawn_floating_damage(center, text=f"-{dmg}", color=RETRO_HP_YELLOW)
                self.particle_mgr.spawn_wall_debris(center, count=14)
            self.prev_wall_hp[pos] = wall.hp

        # 2. Bases
        for player, base in state.bases.items():
            old_hp = self.prev_base_hp.get(player, base.hp)
            if base.hp < old_hp:
                dmg = old_hp - base.hp
                center = self._tile_center_vec(base.position)
                self.base_hit_flash[player] = now_ms
                self.particle_mgr.spawn_floating_damage(center, text=f"-{dmg}", color=RETRO_HP_RED)
                color = RETRO_PLAYER_A if player == 0 else RETRO_PLAYER_B
                self.particle_mgr.spawn_explosion(center, primary_color=color, count=24)
            self.prev_base_hp[player] = base.hp

        # 3. Tanks
        for player, tank in state.tanks.items():
            old_hp = self.prev_tank_hp.get(player, tank.hp)
            if tank.hp < old_hp:
                dmg = old_hp - tank.hp
                center = self._tile_center_vec(tank.position)
                self.tank_hit_flash[player] = now_ms
                self.particle_mgr.spawn_floating_damage(center, text=f"-{dmg}", color=RETRO_HP_RED)
                color = RETRO_PLAYER_A if player == 0 else RETRO_PLAYER_B
                self.particle_mgr.spawn_explosion(center, primary_color=color, count=20)
            self.prev_tank_hp[player] = tank.hp

        # Muzzle flashes
        if new_frame:
            for flight in state.bullet_flights:
                tank = state.tanks.get(flight.owner)
                if tank is not None and flight.start == tank.position:
                    center = self._tile_center_vec(flight.start)
                    angle = self._direction_to_angle(tank.direction)
                    self.particle_mgr.spawn_muzzle_flash(center, angle, count=10)
                    self.tank_recoil[flight.owner] = 1.0

    def _draw_pixel_board(self, offset: Vector2) -> None:
        """Render retro arcade checkered battlefield with double pixel border."""
        board_w = self.columns * self.cell_size
        board_h = self.rows * self.cell_size
        bx = int(self.board_x + offset.x)
        by = int(self.board_y + offset.y)

        # Outer double pixel frame
        outer_rect = pygame.Rect(bx - 6, by - 6, board_w + 12, board_h + 12)
        draw_pixel_box(
            self.screen,
            outer_rect,
            fill_color=RETRO_BOARD_BG,
            border_color=RETRO_BOARD_BORDER,
            highlight_color=(60, 72, 98),
            shadow_color=(12, 14, 20),
            border_width=2,
        )

        # Checkered Pixel Cells
        for row in range(1, self.rows + 1):
            for col in range(1, self.columns + 1):
                rect = self._tile(Position(row, col))
                rect.x += int(offset.x)
                rect.y += int(offset.y)

                tile_color = RETRO_CELL_A if (row + col) % 2 == 0 else RETRO_CELL_B
                pygame.draw.rect(self.screen, tile_color, rect)
                pygame.draw.rect(self.screen, RETRO_GRID_LINE, rect, width=1)

                # Pixel corner dots
                pygame.draw.rect(self.screen, (22, 26, 36), (rect.left, rect.top, 2, 2))

    def _draw_pixel_walls(self, state: GameState, offset: Vector2, now_ms: int) -> None:
        """Render Battle-City style pixel brick barriers with damage flash and mini HP bars."""
        for pos, wall in state.game_map.walls.items():
            if wall.is_destroyed:
                continue

            rect = self._tile(pos)
            rect.x += int(offset.x)
            rect.y += int(offset.y)

            # Inset wall block
            inset = max(2, self.cell_size // 10)
            wall_rect = rect.inflate(-inset * 2, -inset * 2)

            # Check Damage Hit Flash (Chớp trắng khi nhận sát thương)
            is_flashing = (now_ms - self.wall_hit_flash.get(pos, 0)) < 130

            if is_flashing:
                # White-hot hit flash
                pygame.draw.rect(self.screen, (255, 255, 255), wall_rect)
                pygame.draw.rect(self.screen, (200, 50, 50), wall_rect, width=2)
            else:
                # Pixel Brick Texture
                self._render_brick_texture(wall_rect, wall.hp)

            # Per-Entity Health Bar for Wall (3 pixel segments at bottom of wall)
            self._draw_wall_hp_bar(wall_rect, wall.hp)

    def _render_brick_texture(self, rect: pygame.Rect, hp: int) -> None:
        """Procedurally render classic 8-bit brick patterns with mortar lines."""
        # Dark Mortar Background
        pygame.draw.rect(self.screen, RETRO_WALL_MORTAR, rect)
        pygame.draw.rect(self.screen, RETRO_BOARD_BORDER, rect, width=1)

        # 3 Rows of bricks
        rows = 3
        brick_h = (rect.height - 4) // rows
        for r in range(rows):
            by = rect.y + 1 + r * (brick_h + 1)
            # Offset every second row like classic masonry
            cols = 2
            brick_w = (rect.width - 4) // cols
            shift = (brick_w // 2) if r % 2 == 1 else 0

            for c in range(-1, cols + 1):
                bx = rect.x + 1 + c * (brick_w + 1) + shift
                b_rect = pygame.Rect(bx, by, brick_w, brick_h)
                clip_rect = b_rect.clip(rect.inflate(-2, -2))
                if clip_rect.width <= 0 or clip_rect.height <= 0:
                    continue

                # Damage chipped corners based on HP
                if hp == 2 and r == 0 and c == 0:
                    continue  # chipped brick
                if hp == 1 and (r == 0 or (r == 2 and c == 1)):
                    continue  # broken bricks

                pygame.draw.rect(self.screen, RETRO_WALL_BRICK, clip_rect)
                # 1px top highlight
                pygame.draw.line(self.screen, RETRO_WALL_LIGHT, clip_rect.topleft, clip_rect.topright, 1)
                # 1px bottom shadow
                pygame.draw.line(self.screen, RETRO_WALL_DARK, clip_rect.bottomleft, clip_rect.bottomright, 1)

    def _draw_wall_hp_bar(self, wall_rect: pygame.Rect, hp: int) -> None:
        """Render 3 mini pixel blocks indicating wall integrity (3/3 HP)."""
        bar_w = 18
        bar_h = 4
        bar_x = wall_rect.centerx - bar_w // 2
        bar_y = wall_rect.bottom - bar_h - 2

        # Black slot backing
        pygame.draw.rect(self.screen, (10, 12, 16), (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2))

        seg_w = 5
        gap = 1
        for i in range(3):
            sx = bar_x + i * (seg_w + gap)
            seg_rect = pygame.Rect(sx, bar_y, seg_w, bar_h)
            if i < hp:
                col = RETRO_HP_GREEN if hp == 3 else (RETRO_HP_YELLOW if hp == 2 else RETRO_HP_RED)
                pygame.draw.rect(self.screen, col, seg_rect)
            else:
                pygame.draw.rect(self.screen, (30, 34, 44), seg_rect)

    def _draw_pixel_bases(self, state: GameState, offset: Vector2, now_ms: int) -> None:
        """Render fortified pixel command bases with animated radar antenna and HP bars."""
        for player, base in state.bases.items():
            center = self._tile_center_vec(base.position) + offset
            player_color = RETRO_PLAYER_A if player == 0 else RETRO_PLAYER_B
            is_active = not base.is_destroyed
            is_flashing = (now_ms - self.base_hit_flash.get(player, 0)) < 130

            size = int(self.cell_size * 0.82)
            base_rect = pygame.Rect(int(center.x - size // 2), int(center.y - size // 2), size, size)

            if is_flashing:
                # White hit flash on damage
                pygame.draw.rect(self.screen, (255, 255, 255), base_rect)
                pygame.draw.rect(self.screen, (220, 50, 50), base_rect, width=2)
            elif not is_active:
                # Destroyed rubble
                draw_pixel_box(self.screen, base_rect, fill_color=(45, 48, 56), border_color=RETRO_BOARD_BORDER, border_width=2)
                # Red X over ruins
                pygame.draw.line(self.screen, (200, 50, 50), base_rect.topleft, base_rect.bottomright, 2)
                pygame.draw.line(self.screen, (200, 50, 50), base_rect.topright, base_rect.bottomleft, 2)
            else:
                # Active Pixel Command Outpost
                draw_pixel_box(
                    self.screen,
                    base_rect,
                    fill_color=(24, 28, 40),
                    border_color=RETRO_BOARD_BORDER,
                    highlight_color=(70, 85, 115),
                    shadow_color=(12, 14, 20),
                    border_width=2,
                )

                # Inner fortified shield
                inner_s = size - 8
                inner_rect = pygame.Rect(int(center.x - inner_s // 2), int(center.y - inner_s // 2), inner_s, inner_s)
                pygame.draw.rect(self.screen, player_color, inner_rect, width=2)

                # Gold Command Star / Emblem
                star_s = max(4, size // 4)
                star_rect = pygame.Rect(int(center.x - star_s // 2), int(center.y - star_s // 2), star_s, star_s)
                pygame.draw.rect(self.screen, (255, 215, 0), star_rect)
                pygame.draw.rect(self.screen, (255, 255, 255), star_rect.inflate(-2, -2))

                # Animated Blinking 8-bit Antenna Light
                blink = (now_ms // 250) % 2 == 0
                ant_col = (255, 255, 255) if blink else player_color
                pygame.draw.line(self.screen, player_color, (center.x, base_rect.top), (center.x, base_rect.top - 4), 2)
                pygame.draw.rect(self.screen, ant_col, (center.x - 2, base_rect.top - 6, 4, 3))

            # Per-Entity Health Bar for Base
            bar_y = base_rect.top - 7 if player == 0 else base_rect.bottom + 2
            self._draw_entity_hp_bar(
                center_x=int(center.x),
                y=bar_y,
                hp=base.hp,
                max_hp=config.BASE_INITIAL_HP,
                width=int(size * 0.9),
                label="BASE",
                player_color=player_color,
            )

    def _draw_pixel_tanks(self, state: GameState, offset: Vector2, dt: float, now_ms: int) -> None:
        """Render 8-bit / Metal Slug inspired pixel battle tanks with per-tank health bars."""
        for player, tank in state.tanks.items():
            center = self.tank_visual_pos[player] + offset
            angle = self.tank_visual_angle[player]
            is_active = not tank.is_destroyed
            player_color = RETRO_PLAYER_A if player == 0 else RETRO_PLAYER_B
            hi_color = RETRO_HIGHLIGHT_A if player == 0 else RETRO_HIGHLIGHT_B
            sh_color = RETRO_SHADOW_A if player == 0 else RETRO_SHADOW_B

            is_flashing = (now_ms - self.tank_hit_flash.get(player, 0)) < 130
            scale = self.cell_size * 0.44

            forward = Vector2(1.0, 0.0).rotate(angle)
            right = forward.rotate(90.0)

            # Dimensions
            tread_w = scale * 1.65
            tread_h = scale * 0.40
            tread_offset = scale * 0.58

            hull_w = scale * 1.35
            hull_h = scale * 1.05

            if is_flashing:
                # White-hot Damage Flash across entire tank silhouette
                chassis_rect = pygame.Rect(0, 0, int(scale * 2.0), int(scale * 1.8))
                chassis_rect.center = (int(center.x), int(center.y))
                pygame.draw.rect(self.screen, (255, 255, 255), chassis_rect)
                pygame.draw.rect(self.screen, (220, 50, 50), chassis_rect, width=2)
            elif not is_active:
                # Destroyed tank chassis (burnt wreckage)
                for sign in (-1, 1):
                    t_c = center + right * (sign * tread_offset)
                    pts = self._rect_points(t_c, tread_w, tread_h, forward, right)
                    pygame.draw.polygon(self.screen, (25, 28, 34), pts)
                    pygame.draw.polygon(self.screen, RETRO_BOARD_BORDER, pts, 1)

                h_pts = self._rect_points(center, hull_w, hull_h, forward, right)
                pygame.draw.polygon(self.screen, (40, 42, 48), h_pts)
                pygame.draw.polygon(self.screen, RETRO_BOARD_BORDER, h_pts, 1)
                pygame.draw.circle(self.screen, (20, 22, 28), (int(center.x), int(center.y)), int(scale * 0.35))
            else:
                # 1. Left & Right Pixel Treads (Bánh xích)
                for sign in (-1, 1):
                    t_c = center + right * (sign * tread_offset)
                    pts = self._rect_points(t_c, tread_w, tread_h, forward, right)
                    pygame.draw.polygon(self.screen, (22, 25, 32), pts)
                    pygame.draw.polygon(self.screen, RETRO_BOARD_BORDER, pts, 2)

                    # Pixel tread teeth
                    num_teeth = 5
                    for t in range(num_teeth):
                        fac = (t / (num_teeth - 1) - 0.5) * (tread_w * 0.75)
                        tc = t_c + forward * fac
                        p1 = tc + right * (tread_h * 0.45)
                        p2 = tc - right * (tread_h * 0.45)
                        pygame.draw.line(self.screen, (85, 95, 115), (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), 2)

                # 2. Main Chassis Hull (Thân xe pixel)
                h_pts = self._rect_points(center, hull_w, hull_h, forward, right)
                pygame.draw.polygon(self.screen, player_color, h_pts)
                pygame.draw.polygon(self.screen, RETRO_BOARD_BORDER, h_pts, 2)

                # Highlight stripe on hull top
                stripe_c = center + forward * (hull_w * 0.15)
                s_pts = self._rect_points(stripe_c, hull_w * 0.6, hull_h * 0.6, forward, right)
                pygame.draw.polygon(self.screen, hi_color, s_pts)

                # 3. Turret Box (Tháp pháo pixel)
                turret_w = scale * 0.85
                turret_h = scale * 0.85
                turret_pts = self._rect_points(center, turret_w, turret_h, forward, right)
                pygame.draw.polygon(self.screen, (24, 28, 40), turret_pts)
                pygame.draw.polygon(self.screen, RETRO_BOARD_BORDER, turret_pts, 2)
                pygame.draw.circle(self.screen, player_color, (int(center.x), int(center.y)), max(2, int(scale * 0.24)))

                # 4. Pixel Cannon Barrel with Recoil
                recoil = scale * 0.28 * math.sin(self.tank_recoil[player] * math.pi)
                barrel_len = max(scale * 0.4, scale * 1.05 - recoil)
                barrel_start = center + forward * (scale * 0.22)
                barrel_end = barrel_start + forward * barrel_len
                b_width = max(3, int(scale * 0.22))

                pygame.draw.line(
                    self.screen,
                    RETRO_BOARD_BORDER,
                    (int(barrel_start.x), int(barrel_start.y)),
                    (int(barrel_end.x), int(barrel_end.y)),
                    b_width + 2,
                )
                pygame.draw.line(
                    self.screen,
                    (75, 88, 110),
                    (int(barrel_start.x), int(barrel_start.y)),
                    (int(barrel_end.x), int(barrel_end.y)),
                    b_width,
                )

                # Muzzle Box at barrel tip
                muzzle_p1 = barrel_end + right * (scale * 0.18)
                muzzle_p2 = barrel_end - right * (scale * 0.18)
                pygame.draw.line(
                    self.screen,
                    player_color,
                    (int(muzzle_p1.x), int(muzzle_p1.y)),
                    (int(muzzle_p2.x), int(muzzle_p2.y)),
                    max(2, int(scale * 0.18)),
                )

            # Per-Entity Health Bar for Tank (Positioned right above the tank)
            bar_y = int(center.y - scale * 1.15)
            self._draw_entity_hp_bar(
                center_x=int(center.x),
                y=bar_y,
                hp=tank.hp,
                max_hp=config.TANK_INITIAL_HP,
                width=int(scale * 1.8),
                label="TANK",
                player_color=player_color,
            )

    def _rect_points(self, c: Vector2, w: float, h: float, fwd: Vector2, rgt: Vector2) -> list[tuple[int, int]]:
        """Compute 4 rotated corner coordinates for pixel-art polygon rectangles."""
        hw = w * 0.5
        hh = h * 0.5
        p1 = c + fwd * hw + rgt * hh
        p2 = c - fwd * hw + rgt * hh
        p3 = c - fwd * hw - rgt * hh
        p4 = c + fwd * hw - rgt * hh
        return [(int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), (int(p3.x), int(p3.y)), (int(p4.x), int(p4.y))]

    def _draw_entity_hp_bar(
        self,
        center_x: int,
        y: int,
        hp: int,
        max_hp: int,
        width: int,
        label: str,
        player_color: tuple[int, int, int],
    ) -> None:
        """Render segmented pixel health bar with dark border and dynamic color."""
        bar_h = 5
        bar_x = center_x - width // 2

        # 1. Outer Dark Box
        pygame.draw.rect(self.screen, (10, 12, 16), (bar_x - 1, y - 1, width + 2, bar_h + 2))

        # 2. Segmented Blocks
        curr_hp = max(0, min(hp, max_hp))
        num_blocks = max_hp
        gap = 1
        block_w = max(1, (width - (num_blocks - 1) * gap) // num_blocks)

        for i in range(num_blocks):
            bx = bar_x + i * (block_w + gap)
            block_rect = pygame.Rect(bx, y, block_w, bar_h)
            if i < curr_hp:
                # Color code health: Green -> Yellow -> Red
                if curr_hp > max_hp * 0.55:
                    c = RETRO_HP_GREEN
                elif curr_hp > max_hp * 0.28:
                    c = RETRO_HP_YELLOW
                else:
                    c = RETRO_HP_RED
                pygame.draw.rect(self.screen, c, block_rect)
            else:
                # Depleted slot
                pygame.draw.rect(self.screen, (32, 36, 46), block_rect)

        # 3. Mini HP Text badge
        hp_str = f"{curr_hp}"
        txt = self.tiny_font.render(hp_str, False, (240, 244, 252))
        shadow = self.tiny_font.render(hp_str, False, (0, 0, 0))
        tx = bar_x + width + 3
        ty = y - 3
        self.screen.blit(shadow, (tx + 1, ty + 1))
        self.screen.blit(txt, (tx, ty))

    def _draw_pixel_bullets(self, state: GameState, offset: Vector2, now_ms: int) -> None:
        """Render retro projectile diamond bullets with pixel smoke trail."""
        elapsed_tick = now_ms - self.last_tick_time
        bullet_t = elapsed_tick / max(60.0, self.turn_ms * 0.8)
        if bullet_t >= 1.0:
            return

        for flight in state.bullet_flights:
            if flight.start == flight.end:
                continue
            start_pos = self._tile_center_vec(flight.start)
            target_pos = self._tile_center_vec(flight.end)

            # Continuous motion
            center = start_pos.lerp(target_pos, bullet_t) + offset
            forward = (target_pos - start_pos).normalize() if (target_pos - start_pos).length_squared() > 0.001 else Vector2(1, 0)

            # Diamond Pixel Dart
            sz = 6
            bx = int(center.x - sz // 2)
            by = int(center.y - sz // 2)

            # Outer black pixel outline
            pygame.draw.rect(self.screen, RETRO_BOARD_BORDER, (bx - 1, by - 1, sz + 2, sz + 2))
            # Golden Core
            pygame.draw.rect(self.screen, (255, 235, 60), (bx, by, sz, sz))
            # Center white sparkle
            pygame.draw.rect(self.screen, (255, 255, 255), (bx + 1, by + 1, sz - 2, sz - 2))

            # Backward pixel exhaust spark
            tail = center - forward * 5.0
            from .effects import Particle
            import random
            self.particle_mgr.particles.append(
                Particle(
                    pos=tail,
                    vel=-forward * random.uniform(1.0, 2.0) + Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)),
                    color=(255, 140, 40),
                    size=2.0,
                    life_seconds=0.14,
                    pixel_block=True,
                )
            )
