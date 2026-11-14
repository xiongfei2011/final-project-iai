"""Visual particle systems, floating combat numbers, and pixel dynamics.

Utilizes pygame.math.Vector2, clamp, and lerp for retro pixel physics,
radial dispersion, parabolic projectile damage text, and sparks.
"""

import math
import random
import pygame
from pygame.math import Vector2, clamp, lerp


class FloatingText:
    """Retro floating damage indicator that pops and arcs like classic arcade games."""

    def __init__(
        self,
        pos: Vector2,
        text: str = "-1",
        color: tuple[int, int, int] = (255, 68, 68),
        font_size: int = 18,
    ) -> None:
        self.pos = Vector2(pos.x, pos.y - 6.0)
        self.vel = Vector2(random.uniform(-0.8, 0.8), -2.6)
        self.text = text
        self.color = color
        self.life = 0.60
        self.max_life = 0.60
        self.font = pygame.font.Font(None, font_size)

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float) -> None:
        if not self.is_alive:
            return
        self.life -= dt
        self.vel.y += 6.5 * dt  # Gravity
        self.pos += self.vel * (dt * 60.0)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_alive:
            return
        progress = clamp(1.0 - (self.life / self.max_life), 0.0, 1.0)
        alpha = int(clamp(lerp(255.0, 0.0, progress * progress), 0.0, 255.0))

        # Pixel style text with dark outline/shadow
        shadow_surf = self.font.render(self.text, False, (10, 10, 15))
        txt_surf = self.font.render(self.text, False, self.color)

        if alpha < 255:
            shadow_surf.set_alpha(alpha)
            txt_surf.set_alpha(alpha)

        cx, cy = int(self.pos.x), int(self.pos.y)
        w, h = txt_surf.get_width(), txt_surf.get_height()
        # 1px offset drop shadow for 8-bit arcade look
        surface.blit(shadow_surf, (cx - w // 2 + 1, cy - h // 2 + 1))
        surface.blit(txt_surf, (cx - w // 2, cy - h // 2))


class Particle:
    """Pixelated debris and sparks driven by 2D vector physics."""

    def __init__(
        self,
        pos: Vector2,
        vel: Vector2,
        color: tuple[int, int, int],
        size: float,
        life_seconds: float,
        friction: float = 0.90,
        gravity: Vector2 | None = None,
        spark: bool = False,
        pixel_block: bool = True,
    ) -> None:
        self.pos = Vector2(pos)
        self.vel = Vector2(vel)
        self.color = color
        self.start_size = size
        self.life = life_seconds
        self.max_life = life_seconds
        self.friction = friction
        self.gravity = Vector2(gravity) if gravity else Vector2(0, 0)
        self.spark = spark
        self.pixel_block = pixel_block

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float) -> None:
        if not self.is_alive:
            return
        self.life -= dt
        self.vel *= math.pow(self.friction, dt * 60.0)
        self.vel += self.gravity * dt
        self.pos += self.vel * (dt * 60.0)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_alive:
            return

        progress = clamp(1.0 - (self.life / self.max_life), 0.0, 1.0)
        current_size = max(1, int(lerp(self.start_size, 1.0, progress)))
        alpha = int(clamp(lerp(255.0, 0.0, progress), 0.0, 255.0))

        if self.spark:
            # Directional pixel spark segment
            length = max(2.0, self.vel.length() * 1.2)
            direction = self.vel.normalize() if self.vel.length_squared() > 0.001 else Vector2(1, 0)
            end_pos = self.pos + direction * length
            spark_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.line(
                spark_surf,
                (*self.color, alpha),
                (int(self.pos.x), int(self.pos.y)),
                (int(end_pos.x), int(end_pos.y)),
                max(1, current_size),
            )
            surface.blit(spark_surf, (0, 0))
        elif self.pixel_block:
            # Crisp square pixel chunk
            sz = max(2, current_size)
            chunk_surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
            chunk_surf.fill((*self.color, alpha))
            surface.blit(chunk_surf, (int(self.pos.x - sz // 2), int(self.pos.y - sz // 2)))
        else:
            r = int(current_size)
            if r <= 0:
                return
            surf_size = r * 2 + 2
            dot_surf = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
            pygame.draw.circle(
                dot_surf,
                (*self.color, alpha),
                (surf_size // 2, surf_size // 2),
                r,
            )
            surface.blit(dot_surf, (int(self.pos.x - r), int(self.pos.y - r)))


class ShockwaveRing:
    """Expanding pixel blast ring."""

    def __init__(
        self,
        center: Vector2,
        max_radius: float,
        color: tuple[int, int, int],
        duration: float = 0.28,
    ) -> None:
        self.center = Vector2(center)
        self.max_radius = max_radius
        self.color = color
        self.life = duration
        self.max_life = duration

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float) -> None:
        self.life -= dt

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_alive:
            return
        t = clamp(1.0 - (self.life / self.max_life), 0.0, 1.0)
        radius = int(lerp(2.0, self.max_radius, t))
        alpha = int(clamp(lerp(240.0, 0.0, t), 0.0, 255.0))
        width = max(1, int(lerp(3.0, 1.0, t)))

        if radius <= 0 or alpha <= 0:
            return

        box_size = radius * 2 + width * 2 + 4
        ring_surf = pygame.Surface((box_size, box_size), pygame.SRCALPHA)
        # Pixelated stepped diamond or circle
        pygame.draw.circle(
            ring_surf,
            (*self.color, alpha),
            (box_size // 2, box_size // 2),
            radius,
            width,
        )
        surface.blit(ring_surf, (int(self.center.x - box_size // 2), int(self.center.y - box_size // 2)))


class ParticleManager:
    """Orchestrates pixel explosions, floating texts, and muzzle sparks."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.shockwaves: list[ShockwaveRing] = []
        self.floating_texts: list[FloatingText] = []

    def spawn_floating_damage(
        self, center: Vector2, text: str = "-1", color: tuple[int, int, int] = (255, 68, 68)
    ) -> None:
        """Spawn a bouncing arcade damage number popping off the entity."""
        self.floating_texts.append(FloatingText(center, text=text, color=color))

    def spawn_explosion(
        self,
        center: Vector2,
        primary_color: tuple[int, int, int] = (255, 180, 50),
        count: int = 18,
    ) -> None:
        """Create pixel debris blast."""
        self.shockwaves.append(
            ShockwaveRing(center, max_radius=26.0, color=(255, 220, 120), duration=0.25)
        )

        for _ in range(count):
            angle = random.uniform(0.0, 360.0)
            speed = random.uniform(1.2, 4.5)
            vel = Vector2.from_polar((speed, angle))

            choice = random.random()
            if choice < 0.4:
                color = (255, 235, 100)
                size = random.uniform(2.5, 4.0)
                life = random.uniform(0.18, 0.32)
                spark = True
            elif choice < 0.8:
                color = primary_color
                size = random.uniform(3.0, 5.0)
                life = random.uniform(0.22, 0.40)
                spark = False
            else:
                color = (70, 75, 88)  # pixel smoke chunk
                size = random.uniform(3.0, 5.0)
                life = random.uniform(0.30, 0.50)
                spark = False

            self.particles.append(
                Particle(
                    pos=center,
                    vel=vel,
                    color=color,
                    size=size,
                    life_seconds=life,
                    friction=0.90,
                    gravity=Vector2(0, 3.5),
                    spark=spark,
                    pixel_block=True,
                )
            )

    def spawn_muzzle_flash(
        self,
        tip: Vector2,
        direction_deg: float,
        color: tuple[int, int, int] = (255, 220, 100),
        count: int = 8,
    ) -> None:
        """Forward-directed pixel muzzle sparks."""
        for _ in range(count):
            angle = direction_deg + random.uniform(-20.0, 20.0)
            speed = random.uniform(2.0, 5.0)
            vel = Vector2.from_polar((speed, angle))
            self.particles.append(
                Particle(
                    pos=tip,
                    vel=vel,
                    color=color,
                    size=random.uniform(2.0, 3.0),
                    life_seconds=random.uniform(0.1, 0.18),
                    friction=0.86,
                    spark=True,
                    pixel_block=True,
                )
            )

    def spawn_wall_debris(
        self,
        center: Vector2,
        color: tuple[int, int, int] = (180, 85, 55),
        count: int = 14,
    ) -> None:
        """Spawn tumbling brick / stone pixel chunks when wall is hit."""
        for _ in range(count):
            angle = random.uniform(0.0, 360.0)
            speed = random.uniform(1.2, 3.8)
            vel = Vector2.from_polar((speed, angle))
            self.particles.append(
                Particle(
                    pos=center,
                    vel=vel,
                    color=color,
                    size=random.uniform(2.0, 4.0),
                    life_seconds=random.uniform(0.2, 0.38),
                    friction=0.91,
                    gravity=Vector2(0, 4.5),
                    spark=False,
                    pixel_block=True,
                )
            )

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.is_alive]

        for s in self.shockwaves:
            s.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.is_alive]

        for ft in self.floating_texts:
            ft.update(dt)
        self.floating_texts = [ft for ft in self.floating_texts if ft.is_alive]

    def draw(self, surface: pygame.Surface) -> None:
        for s in self.shockwaves:
            s.draw(surface)
        for p in self.particles:
            p.draw(surface)
        for ft in self.floating_texts:
            ft.draw(surface)
