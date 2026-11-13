"""High-tech tactical Pygame view for Tank Battle.

Completely redesigned using mathematical and geometric routines from
pygame.math (Vector2, clamp, lerp) along with procedural trigonometry,
directional lighting, smooth motion interpolation,
particle systems, and camera shake.
"""

import math
from collections import deque
import pygame
from pygame.math import Vector2, clamp, lerp

from .. import config
from ..game.actions import Direction
from ..game.entities import Position
from ..game.state import GameState
from .control_panel import ControlPanel, PanelState
from .effects import ParticleManager, ScreenShake
from .geometry import (
    calculate_bevel_lighting,
    create_chamfered_box,
    create_cracks,
    create_regular_polygon,
    lerp_angle,
    lerp_color,
    smootherstep,
    smoothstep,
)

# Refined tactical cyber palette
CYBER_BG = (12, 16, 24)
CYBER_BOARD_BG = (16, 22, 32)
CYBER_CELL_A = (22, 30, 42)
CYBER_CELL_B = (27, 36, 50)
CYBER_GRID_LINE = (36, 48, 66)
CYBER_BORDER = (45, 60, 82)
CYBER_ACCENT_A = (34, 211, 238)   # Cyan neon for Player A
CYBER_ACCENT_B = (251, 146, 60)   # Orange neon for Player B
CYBER_PANEL = (20, 26, 38)
CYBER_PANEL_BORDER = (42, 54, 76)
CYBER_TEXT_MAIN = (241, 245, 249)
CYBER_WALL_BASE = (100, 112, 128)
CYBER_BULLET_CORE = (254, 240, 138)
CYBER_BULLET_GLOW = (245, 158, 11)


class PygameView:
    """Renders the battlefield, cyber armor units, and combat dynamics."""

    def __init__(self, state: GameState) -> None:
        self.rows = state.game_map.height
        self.columns = state.game_map.width
        padding = config.UI_PADDING
        panel_width = config.UI_CONTROL_PANEL_WIDTH
        desktop_width = pygame.display.get_desktop_sizes()[0][0]

        # Dynamically scale cell size while keeping tactical proportion
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
        window_height = max(board_height + 96, config.UI_CONTROL_PANEL_HEIGHT + 2 * padding)
        panel_x = window_width - padding - panel_width
        self.board_x = (panel_x - board_width) // 2
        self.board_y = (window_height + 46 - board_height) // 2

        self.screen = pygame.display.set_mode((window_width, window_height))
        pygame.display.set_caption(f"{config.WINDOW_TITLE} - Tactical Cyber Armor")
        panel_rect = pygame.Rect(panel_x, padding, panel_width, window_height - 2 * padding)
        self.controls = ControlPanel(self.screen, panel_rect)

        # Fonts
        self.title_font = pygame.font.Font(None, config.UI_TITLE_FONT_SIZE + 2)
        self.small_font = pygame.font.Font(None, max(14, min(20, self.cell_size // 4)))
        self.tiny_font = pygame.font.Font(None, 14)
        self.light_dir = Vector2(-1.0, -1.0).normalize()
        self.turn_ms = config.DEFAULT_TURN_MS
        self._last_step = 0
        self._reset_dynamics(state)

    def _reset_dynamics(self, state: GameState) -> None:
        """Clear effects and snap pieces to the selected board when rewinding."""
        # Simulation & FX engines
        self.particle_mgr = ParticleManager()
        self.screen_shake = ScreenShake(max_offset=0.0)

        # Vector dynamics state
        now_ms = pygame.time.get_ticks()
        self.last_update_ms = now_ms

        # Timing and synchronized tick engine
        self.last_tick_time = now_ms
        self.last_state_signature: tuple | None = None

        # Smooth position and angle interpolators for tanks
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

        # Damage & explosion detection memory
        self.prev_tank_hp = {p: t.hp for p, t in state.tanks.items()}
        self.prev_base_hp = {p: b.hp for p, b in state.bases.items()}
        self.prev_wall_hp = {
            pos: w.hp for pos, w in state.game_map.walls.items() if not w.is_destroyed
        }
        self.prev_bullet_positions: set[Position] = set()

    def set_turn_ms(self, turn_ms: int) -> None:
        """Configure turn period for precise temporal interpolation."""
        if turn_ms > 0:
            self.turn_ms = turn_ms

    def _direction_to_angle(self, direction: Direction) -> float:
        """Convert directional delta (row, col) to degrees using math.atan2."""
        dr, dc = direction.delta
        return math.degrees(math.atan2(dr, dc))

    def _tile_center_vec(self, position: Position) -> Vector2:
        """Return the exact center of a grid tile as a Vector2."""
        row, col = position
        cx = self.board_x + (col - 0.5) * self.cell_size
        cy = self.board_y + (row - 0.5) * self.cell_size
        return Vector2(cx, cy)

    def _tile(self, position: Position) -> pygame.Rect:
        """Backward compatibility for rect tile bounding box."""
        row, col = position
        return pygame.Rect(
            self.board_x + (col - 1) * self.cell_size,
            self.board_y + (row - 1) * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def _piece_rect(self, position: Position) -> pygame.Rect:
        inset = max(2, self.cell_size // 5)
        return self._tile(position).inflate(-inset, -inset)

    def draw(
        self,
        state: GameState,
        message: str | None = None,
        *,
        show_turn: bool = True,
        turn_label: str | None = None,
        panel: PanelState | None = None,
    ) -> None:
        """Render the complete game frame at 60 FPS."""
        if panel is None:
            panel = PanelState(message=message or (turn_label if show_turn else None) or "")
        if panel.step < self._last_step:
            self._reset_dynamics(state)
        self._last_step = panel.step

        now_ms = pygame.time.get_ticks()
        dt = clamp((now_ms - self.last_update_ms) / 1000.0, 0.001, 0.08)
        self.last_update_ms = now_ms

        # 1. Update physics, animations, and detect combat impacts
        self._update_dynamics(state, dt, now_ms)

        # 2. Render background and ambient grid
        self.screen.fill(CYBER_BG)
        self._draw_ambient_decorations(now_ms)

        title = self.title_font.render(config.WINDOW_TITLE.upper(), True, CYBER_TEXT_MAIN)
        self.screen.blit(title, (config.UI_PADDING, 20))

        # 4. Draw Board with stable positioning (no screen shake)
        shake_offset = Vector2(0.0, 0.0)
        self._draw_board(shake_offset)

        # 5. Draw Tactical Entities (Walls, Bases, Tanks, Bullets)
        self._draw_walls(state, shake_offset)
        self._draw_bases(state, shake_offset, now_ms)
        self._draw_tanks(state, shake_offset, dt)
        self._draw_bullets(state, shake_offset, now_ms)

        # 6. Draw dynamic particle systems & shockwaves on top of the board
        self.particle_mgr.draw(self.screen)

        self.controls.draw(state, panel)

        pygame.display.flip()

    def _update_dynamics(self, state: GameState, dt: float, now_ms: int) -> None:
        """Update particle physics and interpolate positions."""
        self.particle_mgr.update(dt)

        # Detect tick advance to synchronize animation clocks
        state_sig = (
            state.current_turn,
            tuple(t.position for t in state.tanks.values()),
            tuple(t.direction for t in state.tanks.values()),
            tuple(b.position for b in state.bullets),
        )
        if state_sig != self.last_state_signature:
            if self.last_state_signature is not None:
                interval = now_ms - self.last_tick_time
                if 80 <= interval <= 2500:
                    self.turn_ms = interval
            self.last_tick_time = now_ms
            self.last_state_signature = state_sig

        # A. Detect Tank Movements & Rotations with Smootherstep
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

            # Quintic smootherstep translation (continuous 1st & 2nd derivatives)
            elapsed_move = now_ms - self.tank_move_start.get(player, 0)
            move_duration = max(70.0, self.turn_ms * 0.78)
            move_t = clamp(elapsed_move / move_duration, 0.0, 1.0)
            smooth_move_t = smootherstep(move_t)
            self.tank_visual_pos[player] = self.tank_move_from[player].lerp(
                self.tank_move_to[player], smooth_move_t
            )
            self.tank_is_moving[player] = (move_t < 1.0)
            self.tank_move_progress[player] = smooth_move_t

            # Shortest-arc smooth rotation
            elapsed_rot = now_ms - self.tank_rot_start.get(player, 0)
            rot_duration = max(50.0, self.turn_ms * 0.45)
            rot_t = clamp(elapsed_rot / rot_duration, 0.0, 1.0)
            smooth_rot_t = smootherstep(rot_t)
            self.tank_visual_angle[player] = lerp_angle(
                self.tank_rot_from[player], self.tank_rot_to[player], smooth_rot_t
            )

            # Decay recoil
            self.tank_recoil[player] = clamp(
                self.tank_recoil[player] - dt * 5.0, 0.0, 1.0
            )

        # B. Detect Damage & Explosions
        # Wall damage
        for pos, wall in state.game_map.walls.items():
            old_hp = self.prev_wall_hp.get(pos, wall.hp)
            if wall.hp < old_hp:
                center = self._tile_center_vec(pos)
                self.particle_mgr.spawn_wall_debris(center, count=16)
            self.prev_wall_hp[pos] = wall.hp

        # Base damage
        for player, base in state.bases.items():
            old_hp = self.prev_base_hp.get(player, base.hp)
            if base.hp < old_hp:
                center = self._tile_center_vec(base.position)
                color = CYBER_ACCENT_A if player == 0 else CYBER_ACCENT_B
                self.particle_mgr.spawn_explosion(center, primary_color=color, count=30)
            self.prev_base_hp[player] = base.hp

        # Tank damage
        for player, tank in state.tanks.items():
            old_hp = self.prev_tank_hp.get(player, tank.hp)
            if tank.hp < old_hp:
                center = self._tile_center_vec(tank.position)
                color = CYBER_ACCENT_A if player == 0 else CYBER_ACCENT_B
                self.particle_mgr.spawn_explosion(center, primary_color=color, count=24)
            self.prev_tank_hp[player] = tank.hp

        # Bullet impacts & expiration explosions
        current_bullet_positions = {b.position for b in state.bullets}
        for pos in state.expired_bullet_positions:
            center = self._tile_center_vec(pos)
            self.particle_mgr.spawn_explosion(
                center, primary_color=CYBER_BULLET_GLOW, count=18
            )

        # Detect muzzle flash for newly fired bullets
        for bullet in state.bullets:
            if bullet.position not in self.prev_bullet_positions and bullet.steps_left >= config.BULLET_MAX_RANGE:
                # Spawn muzzle flash from the firing tank
                center = self._tile_center_vec(bullet.position)
                bullet_ang = self._direction_to_angle(bullet.direction)
                self.particle_mgr.spawn_muzzle_flash(center, bullet_ang, count=12)
                # Apply recoil to the firing tank
                for p, t in state.tanks.items():
                    if t.position.moved(t.direction) == bullet.position:
                        self.tank_recoil[p] = 1.0

        self.prev_bullet_positions = current_bullet_positions

    def _draw_ambient_decorations(self, now_ms: int) -> None:
        """Render high-tech background lines and corner tactical rivets."""
        w, h = self.screen.get_size()
        # Subtle horizontal circuit lines
        alpha_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(now_ms * 0.002)
        grid_alpha = int(clamp(lerp(18.0, 32.0, pulse), 0.0, 255.0))
        for y in range(0, h, 28):
            pygame.draw.line(alpha_surf, (50, 70, 95, grid_alpha), (0, y), (w, y), 1)
        self.screen.blit(alpha_surf, (0, 0))

    def _draw_board(self, offset: Vector2) -> None:
        """Draw the tactical board grid, beveled border, and coordinate crosshairs."""
        board_w = self.columns * self.cell_size
        board_h = self.rows * self.cell_size
        center = Vector2(
            self.board_x + board_w * 0.5 + offset.x,
            self.board_y + board_h * 0.5 + offset.y,
        )

        # 1. Beveled Board Outer Frame
        outer_poly = create_chamfered_box(
            center, board_w + 14, board_h + 14, chamfer=8.0
        )
        pygame.draw.polygon(self.screen, CYBER_PANEL_BORDER, [p for p in outer_poly])
        inner_frame = create_chamfered_box(
            center, board_w + 10, board_h + 10, chamfer=6.0
        )
        pygame.draw.polygon(self.screen, CYBER_BOARD_BG, [p for p in inner_frame])

        # 2. Draw Grid Tiles
        for row in range(1, self.rows + 1):
            for col in range(1, self.columns + 1):
                pos = Position(row, col)
                rect = self._tile(pos)
                rect.x += int(offset.x)
                rect.y += int(offset.y)

                tile_color = CYBER_CELL_A if (row + col) % 2 == 0 else CYBER_CELL_B
                pygame.draw.rect(self.screen, tile_color, rect)
                pygame.draw.rect(self.screen, CYBER_GRID_LINE, rect, width=1)

                # Tactical crosshair corner markers at grid intersections
                tl = Vector2(rect.topleft)
                crosshair_len = 3.0
                pygame.draw.line(self.screen, CYBER_BORDER, tl - Vector2(crosshair_len, 0), tl + Vector2(crosshair_len, 0))
                pygame.draw.line(self.screen, CYBER_BORDER, tl - Vector2(0, crosshair_len), tl + Vector2(0, crosshair_len))

        # 3. Outer Neon Accent Border
        pygame.draw.lines(self.screen, CYBER_BORDER, True, [p for p in inner_frame], width=1)

    def _draw_walls(self, state: GameState, offset: Vector2) -> None:
        """Render fortified defense barriers with 3D bevel lighting and cracks."""
        for pos, wall in state.game_map.walls.items():
            if wall.is_destroyed:
                continue

            center = self._tile_center_vec(pos) + offset
            box_size = self.cell_size * 0.76
            chamfer = box_size * 0.16

            # Generate 8-sided chamfered box
            outer_verts = create_chamfered_box(center, box_size, box_size, chamfer)

            # Draw 3D beveled facets using surface normals & vector dot product
            for i in range(len(outer_verts)):
                p1 = outer_verts[i]
                p2 = outer_verts[(i + 1) % len(outer_verts)]
                edge = p2 - p1
                normal = edge.rotate(-90.0)

                facet_color = calculate_bevel_lighting(
                    normal, self.light_dir, CYBER_WALL_BASE, intensity=0.4
                )
                facet_poly = [center, p1, p2]
                pygame.draw.polygon(self.screen, facet_color, facet_poly)

            # Draw central armor plate
            inner_verts = create_chamfered_box(
                center, box_size * 0.70, box_size * 0.70, chamfer * 0.6
            )
            pygame.draw.polygon(self.screen, (75, 85, 100), inner_verts)
            pygame.draw.polygon(self.screen, CYBER_PANEL_BORDER, inner_verts, width=1)

            # Corner Rivets using symmetric vectors
            rivet_dist = box_size * 0.24
            for rx in (-1, 1):
                for ry in (-1, 1):
                    r_pos = center + Vector2(rx * rivet_dist, ry * rivet_dist)
                    pygame.draw.circle(self.screen, (130, 145, 165), (int(r_pos.x), int(r_pos.y)), 1)

            # Procedural Fracture Cracks based on wall damage
            if wall.hp < config.WALL_INITIAL_HP:
                branches = 5 - wall.hp
                cracks = create_cracks(
                    center, box_size * 0.38, seed=pos.row * 17 + pos.column * 31, num_branches=branches
                )
                for crack in cracks:
                    pts = [(int(p.x), int(p.y)) for p in crack]
                    pygame.draw.lines(self.screen, (25, 30, 38), False, pts, 1)

            # HP Indicator
            hp_txt = self.tiny_font.render(str(wall.hp), True, CYBER_TEXT_MAIN)
            self.screen.blit(hp_txt, hp_txt.get_rect(center=(int(center.x), int(center.y))))

    def _draw_bases(self, state: GameState, offset: Vector2, now_ms: int) -> None:
        """Render high-tech octagonal command outposts with rotating radar sweep."""
        for player, base in state.bases.items():
            center = self._tile_center_vec(base.position) + offset
            radius = self.cell_size * 0.40
            player_color = CYBER_ACCENT_A if player == 0 else CYBER_ACCENT_B
            is_active = not base.is_destroyed
            base_col = player_color if is_active else config.UI_DESTROYED_COLOR

            # 1. Outer Octagonal Fortification (8 vertices using polar coordinates)
            octagon = create_regular_polygon(center, radius, sides=8, start_angle=22.5)

            # Beveled facets with directional lighting
            for i in range(8):
                p1 = octagon[i]
                p2 = octagon[(i + 1) % 8]
                normal = (p2 - p1).rotate(-90.0)
                facet_col = calculate_bevel_lighting(normal, self.light_dir, base_col, intensity=0.35)
                pygame.draw.polygon(self.screen, facet_col, [center, p1, p2])

            # 2. Inner Command Core
            inner_octagon = create_regular_polygon(center, radius * 0.72, sides=8, start_angle=22.5)
            pygame.draw.polygon(self.screen, CYBER_PANEL, inner_octagon)
            pygame.draw.polygon(self.screen, base_col, inner_octagon, width=2)

            if is_active:
                # 3. Rotating Radar Sweep Beam (Trigonometric angular sector)
                sweep_angle = (now_ms * 0.14) % 360.0
                radar_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                sector_steps = 7
                for s in range(sector_steps):
                    ang = sweep_angle - s * 3.5
                    alpha = int(clamp(lerp(160.0, 10.0, s / sector_steps), 0.0, 255.0))
                    ray_end = center + Vector2.from_polar((radius * 0.7, ang))
                    pygame.draw.line(
                        radar_surf,
                        (*base_col, alpha),
                        (int(center.x), int(center.y)),
                        (int(ray_end.x), int(ray_end.y)),
                        2,
                    )
                self.screen.blit(radar_surf, (0, 0))

                # Expanding Shield Ripple Wave
                shield_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
                wave_t = (now_ms * 0.0012 + player * 0.5) % 1.0
                wave_r = int(lerp(radius * 0.35, radius * 1.35, wave_t))
                wave_alpha = int(clamp(lerp(140.0, 0.0, wave_t), 0.0, 255.0))
                pygame.draw.circle(shield_surf, (*base_col, wave_alpha), (int(center.x), int(center.y)), wave_r, 1)
                self.screen.blit(shield_surf, (0, 0))

                # 4. Pulsing Reactor Core
                pulse = 0.5 + 0.5 * math.sin(now_ms * 0.007 + player * math.pi)
                core_r = max(2.0, radius * 0.22 * (0.8 + 0.3 * pulse))
                pygame.draw.circle(self.screen, base_col, (int(center.x), int(center.y)), int(core_r))
                pygame.draw.circle(self.screen, (255, 255, 255), (int(center.x), int(center.y)), max(1, int(core_r * 0.4)))
            else:
                # Destroyed marker
                pygame.draw.line(self.screen, (220, 50, 50), center - Vector2(6, 6), center + Vector2(6, 6), 2)
                pygame.draw.line(self.screen, (220, 50, 50), center - Vector2(6, -6), center + Vector2(6, -6), 2)

            # Base Label & HP
            label_text = f"B:{base.hp}"
            lbl = self.tiny_font.render(label_text, True, CYBER_TEXT_MAIN)
            lbl_bg = lbl.get_rect(center=(int(center.x), int(center.y + radius * 0.75)))
            pygame.draw.rect(self.screen, CYBER_BG, lbl_bg.inflate(4, 2), border_radius=3)
            self.screen.blit(lbl, lbl_bg)

    def _draw_tanks(self, state: GameState, offset: Vector2, dt: float) -> None:
        """Render tactical tanks with smooth position lerp, rotating turret, tracks, and recoil."""
        for player, tank in state.tanks.items():
            center = self.tank_visual_pos[player] + offset
            angle = self.tank_visual_angle[player]
            is_active = not tank.is_destroyed
            player_color = CYBER_ACCENT_A if player == 0 else CYBER_ACCENT_B
            color = player_color if is_active else config.UI_DESTROYED_COLOR

            scale = self.cell_size * 0.44

            # Forward and orthogonal Right vectors for geometric projection
            forward = Vector2(1.0, 0.0).rotate(angle)
            right = forward.rotate(90.0)

            # 1. Left and Right Treads (Bánh xích)
            tread_w = scale * 1.70
            tread_h = scale * 0.38
            tread_offset = scale * 0.60

            for sign in (-1, 1):
                tread_center = center + right * (sign * tread_offset)
                tread_poly = create_chamfered_box(
                    tread_center, tread_w, tread_h, chamfer=scale * 0.12, angle_deg=angle
                )
                pygame.draw.polygon(self.screen, (24, 28, 36), tread_poly)
                pygame.draw.polygon(self.screen, (45, 55, 70), tread_poly, width=1)

                # Tread Segment Ridges with dynamic scrolling when moving
                num_ridges = 6
                ridge_gap = (tread_w * 0.75) / (num_ridges - 1)
                scroll = (
                    (self.tank_move_progress.get(player, 0.0) * ridge_gap * 2.5) % ridge_gap
                    if self.tank_is_moving.get(player, False)
                    else 0.0
                )
                for r in range(num_ridges):
                    offset_factor = (r / (num_ridges - 1) - 0.5) * (tread_w * 0.75) + scroll
                    if abs(offset_factor) > tread_w * 0.42:
                        continue
                    ridge_c = tread_center + forward * offset_factor
                    p1 = ridge_c + right * (tread_h * 0.45)
                    p2 = ridge_c - right * (tread_h * 0.45)
                    pygame.draw.line(self.screen, (60, 72, 90), (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), 1)

            # 2. Chassis Main Hull (Thân xe vát góc)
            chassis_w = scale * 1.45
            chassis_h = scale * 1.15
            chassis_poly = create_chamfered_box(
                center, chassis_w, chassis_h, chamfer=scale * 0.28, angle_deg=angle
            )
            pygame.draw.polygon(self.screen, (32, 42, 56), chassis_poly)

            # Hull directional armor highlights
            for i in range(len(chassis_poly)):
                p1 = chassis_poly[i]
                p2 = chassis_poly[(i + 1) % len(chassis_poly)]
                normal = (p2 - p1).rotate(-90.0)
                facet_c = calculate_bevel_lighting(normal, self.light_dir, (40, 52, 70), intensity=0.3)
                pygame.draw.line(self.screen, facet_c, (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y)), 2)

            # Engine Deck Grill at the rear
            rear_c = center - forward * (chassis_w * 0.32)
            grill_poly = create_chamfered_box(
                rear_c, scale * 0.35, scale * 0.65, chamfer=scale * 0.08, angle_deg=angle
            )
            pygame.draw.polygon(self.screen, (20, 25, 34), grill_poly)

            # 3. Turret (Tháp pháo hình lục giác)
            turret_poly = create_regular_polygon(center, scale * 0.52, sides=6, start_angle=angle)
            pygame.draw.polygon(self.screen, (42, 56, 75), turret_poly)
            pygame.draw.polygon(self.screen, color, turret_poly, width=2)

            # 4. Main Cannon Barrel with Recoil Animation
            recoil_dist = scale * 0.32 * math.sin(self.tank_recoil[player] * math.pi)
            barrel_base_len = scale * 1.05
            effective_len = max(scale * 0.4, barrel_base_len - recoil_dist)

            barrel_start = center + forward * (scale * 0.25)
            barrel_end = barrel_start + forward * effective_len
            barrel_width = max(3, int(scale * 0.22))

            pygame.draw.line(
                self.screen,
                (28, 36, 48),
                (int(barrel_start.x), int(barrel_start.y)),
                (int(barrel_end.x), int(barrel_end.y)),
                barrel_width,
            )
            pygame.draw.line(
                self.screen,
                color,
                (int(barrel_start.x), int(barrel_start.y)),
                (int(barrel_end.x), int(barrel_end.y)),
                max(1, barrel_width - 2),
            )

            # Muzzle Brake at barrel tip
            muzzle_w = scale * 0.18
            muzzle_p1 = barrel_end + right * (muzzle_w * 0.9)
            muzzle_p2 = barrel_end - right * (muzzle_w * 0.9)
            pygame.draw.line(
                self.screen,
                (55, 70, 92),
                (int(muzzle_p1.x), int(muzzle_p1.y)),
                (int(muzzle_p2.x), int(muzzle_p2.y)),
                max(2, int(scale * 0.16)),
            )

            # Commander Hatch in turret center
            pygame.draw.circle(self.screen, (26, 34, 46), (int(center.x), int(center.y)), max(2, int(scale * 0.22)))
            pygame.draw.circle(self.screen, color, (int(center.x), int(center.y)), max(1, int(scale * 0.12)))

            # Tank HP Badge
            hp_bg = pygame.Rect(0, 0, 18, 14)
            hp_bg.center = (int(center.x), int(center.y + scale * 0.85))
            pygame.draw.rect(self.screen, CYBER_BG, hp_bg, border_radius=3)
            pygame.draw.rect(self.screen, color, hp_bg, width=1, border_radius=3)
            hp_lbl = self.tiny_font.render(str(tank.hp), True, CYBER_TEXT_MAIN)
            self.screen.blit(hp_lbl, hp_lbl.get_rect(center=hp_bg.center))

    def _draw_bullets(self, state: GameState, offset: Vector2, now_ms: int) -> None:
        """Render aerodynamic projectile darts with smooth continuous flight interpolation."""
        elapsed_tick = now_ms - self.last_tick_time
        bullet_t = clamp(elapsed_tick / max(60.0, float(self.turn_ms)), 0.0, 1.0)

        for bullet in state.bullets:
            dr, dc = bullet.direction.delta
            prev_pos = Position(bullet.position.row - dr, bullet.position.column - dc)
            start_pos = self._tile_center_vec(prev_pos)
            target_pos = self._tile_center_vec(bullet.position)

            # Continuous linear trajectory interpolation across the tile boundary
            center = start_pos.lerp(target_pos, bullet_t) + offset
            angle = self._direction_to_angle(bullet.direction)
            forward = Vector2(1.0, 0.0).rotate(angle)
            right = forward.rotate(90.0)

            dart_len = self.cell_size * 0.32
            dart_w = self.cell_size * 0.14

            # 1. Multi-layered Plasma Glow Halo (Transparent radial alpha disks)
            glow_surf = pygame.Surface((self.cell_size * 2, self.cell_size * 2), pygame.SRCALPHA)
            local_center = (self.cell_size, self.cell_size)
            for layer in range(3):
                r = int(self.cell_size * (0.35 - layer * 0.08))
                alpha = int(clamp(lerp(40.0, 150.0, layer / 2.0), 0.0, 255.0))
                pygame.draw.circle(glow_surf, (*CYBER_BULLET_GLOW, alpha), local_center, r)
            self.screen.blit(
                glow_surf,
                (int(center.x - self.cell_size), int(center.y - self.cell_size)),
            )

            # 2. Aerodynamic Dart Polygon
            tip = center + forward * (dart_len * 0.6)
            left_wing = center - forward * (dart_len * 0.4) + right * (dart_w * 0.6)
            tail = center - forward * (dart_len * 0.5)
            right_wing = center - forward * (dart_len * 0.4) - right * (dart_w * 0.6)

            dart_pts = [tip, left_wing, tail, right_wing]
            pygame.draw.polygon(self.screen, CYBER_BULLET_CORE, dart_pts)
            pygame.draw.polygon(self.screen, (255, 255, 255), dart_pts, width=1)

            # 3. Dynamic thruster exhaust sparks
            backward = -forward
            tail_pos = center + backward * (dart_len * 0.5)
            from .effects import Particle
            import random
            self.particle_mgr.particles.append(
                Particle(
                    pos=tail_pos,
                    vel=backward * random.uniform(1.2, 2.5) + Vector2(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)),
                    color=(255, 210, 80),
                    size=random.uniform(2.0, 3.2),
                    life_seconds=random.uniform(0.12, 0.20),
                    friction=0.88,
                )
            )
