"""Visual particle systems, screen shake, and animation dynamics.

Utilizes pygame.math.Vector2, clamp, and lerp for physically plausible motion,
radial dispersion, velocity damping, and smooth fade transitions.
"""

import math
import random
import pygame
from pygame.math import Vector2, clamp, lerp

from .geometry import lerp_color


class ScreenShake:
    """Simulates camera trauma and decaying sinusoidal screen shake."""

    def __init__(self, max_offset: float = 7.0) -> None:
        self.max_offset = max_offset
        self.trauma: float = 0.0
        self.offset = Vector2(0.0, 0.0)

    def trigger(self, amount: float = 0.5) -> None:
        """Add trauma clamped to [0.0, 1.0]."""
        self.trauma = clamp(self.trauma + amount, 0.0, 1.0)

    def update(self, dt: float, now_ms: int) -> None:
        """Decay trauma and compute offset using non-linear power curve."""
        if self.trauma <= 0.001:
            self.trauma = 0.0
            self.offset = Vector2(0.0, 0.0)
            return

        # Quadratic trauma falloff gives natural tactile punch
        intensity = self.trauma * self.trauma
        self.trauma = clamp(self.trauma - dt * 2.2, 0.0, 1.0)

        # High frequency oscillations using trigonometric functions
        freq_x = now_ms * 0.045
        freq_y = now_ms * 0.055
        self.offset = Vector2(
            math.sin(freq_x) * self.max_offset * intensity,
            math.cos(freq_y) * self.max_offset * intensity,
        )


class Particle:
    """Individual particle driven by 2D vector physics."""

    def __init__(
        self,
        pos: Vector2,
        vel: Vector2,
        color: tuple[int, int, int],
        size: float,
        life_seconds: float,
        friction: float = 0.92,
        gravity: Vector2 | None = None,
        spark: bool = False,
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

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float) -> None:
        if not self.is_alive:
            return
        self.life -= dt
        # Damping & acceleration
        self.vel *= math.pow(self.friction, dt * 60.0)
        self.vel += self.gravity * dt
        self.pos += self.vel * (dt * 60.0)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_alive:
            return

        progress = clamp(1.0 - (self.life / self.max_life), 0.0, 1.0)
        current_size = max(1.0, lerp(self.start_size, 0.5, progress))
        alpha = int(clamp(lerp(255.0, 0.0, progress), 0.0, 255.0))

        if self.spark:
            # Draw directional spark line along velocity
            length = max(3.0, self.vel.length() * 1.5)
            direction = self.vel.normalize() if self.vel.length_squared() > 0.001 else Vector2(1, 0)
            end_pos = self.pos + direction * length
            spark_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            pygame.draw.line(
                spark_surf,
                (*self.color, alpha),
                (int(self.pos.x), int(self.pos.y)),
                (int(end_pos.x), int(end_pos.y)),
                max(1, int(current_size)),
            )
            surface.blit(spark_surf, (0, 0))
        else:
            # Soft radial dot
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
    """Expanding tactical shockwave ring."""

    def __init__(
        self,
        center: Vector2,
        max_radius: float,
        color: tuple[int, int, int],
        duration: float = 0.35,
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
        width = max(1, int(lerp(4.0, 1.0, t)))

        if radius <= 0 or alpha <= 0:
            return

        box_size = radius * 2 + width * 2 + 2
        ring_surf = pygame.Surface((box_size, box_size), pygame.SRCALPHA)
        pygame.draw.circle(
            ring_surf,
            (*self.color, alpha),
            (box_size // 2, box_size // 2),
            radius,
            width,
        )
        surface.blit(ring_surf, (int(self.center.x - box_size // 2), int(self.center.y - box_size // 2)))


class ParticleManager:
    """Orchestrates particle lifecycles, blasts, impacts, and muzzles."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.shockwaves: list[ShockwaveRing] = []

    def spawn_explosion(
        self,
        center: Vector2,
        primary_color: tuple[int, int, int] = (255, 180, 50),
        count: int = 24,
    ) -> None:
        """Create radial blast with flame particles, sparks, and shockwave."""
        self.shockwaves.append(
            ShockwaveRing(center, max_radius=32.0, color=(255, 230, 150), duration=0.32)
        )

        for _ in range(count):
            angle = random.uniform(0.0, 360.0)
            speed = random.uniform(1.2, 5.5)
            vel = Vector2.from_polar((speed, angle))

            # Alternate between orange flame, bright yellow core, and smoke
            choice = random.random()
            if choice < 0.4:
                color = (255, 230, 110)
                size = random.uniform(2.5, 4.5)
                life = random.uniform(0.18, 0.35)
                spark = True
            elif choice < 0.75:
                color = primary_color
                size = random.uniform(3.0, 6.0)
                life = random.uniform(0.25, 0.45)
                spark = False
            else:
                color = (90, 100, 115)  # smoke
                size = random.uniform(3.0, 5.0)
                life = random.uniform(0.35, 0.6)
                spark = False

            self.particles.append(
                Particle(
                    pos=center,
                    vel=vel,
                    color=color,
                    size=size,
                    life_seconds=life,
                    friction=0.91,
                    spark=spark,
                )
            )

    def spawn_muzzle_flash(
        self,
        tip: Vector2,
        direction_deg: float,
        color: tuple[int, int, int] = (255, 220, 100),
        count: int = 10,
    ) -> None:
        """Produce forward-directed conical muzzle sparks upon firing."""
        for _ in range(count):
            angle = direction_deg + random.uniform(-25.0, 25.0)
            speed = random.uniform(2.0, 6.0)
            vel = Vector2.from_polar((speed, angle))
            self.particles.append(
                Particle(
                    pos=tip,
                    vel=vel,
                    color=color,
                    size=random.uniform(2.0, 3.5),
                    life_seconds=random.uniform(0.1, 0.22),
                    friction=0.88,
                    spark=True,
                )
            )

    def spawn_wall_debris(
        self,
        center: Vector2,
        color: tuple[int, int, int] = (140, 150, 165),
        count: int = 12,
    ) -> None:
        """Produce concrete / armor debris upon wall hit."""
        for _ in range(count):
            angle = random.uniform(0.0, 360.0)
            speed = random.uniform(1.0, 3.5)
            vel = Vector2.from_polar((speed, angle))
            self.particles.append(
                Particle(
                    pos=center,
                    vel=vel,
                    color=color,
                    size=random.uniform(1.5, 3.0),
                    life_seconds=random.uniform(0.2, 0.4),
                    friction=0.92,
                    spark=False,
                )
            )

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.is_alive]

        for s in self.shockwaves:
            s.update(dt)
        self.shockwaves = [s for s in self.shockwaves if s.is_alive]

    def draw(self, surface: pygame.Surface) -> None:
        for s in self.shockwaves:
            s.draw(surface)
        for p in self.particles:
            p.draw(surface)
