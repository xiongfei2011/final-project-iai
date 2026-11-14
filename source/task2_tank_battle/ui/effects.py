"""Visual particle systems, floating combat numbers, and pixel dynamics.

Optimised: avoids per-frame Surface allocation by drawing directly
onto the target using opaque primitives; uses pooled lists and
in-place math to minimise GC pressure.
"""

import math
import random
import pygame
from pygame.math import Vector2, clamp, lerp


# ---------------------------------------------------------------------------
# Floating Damage Text
# ---------------------------------------------------------------------------

class FloatingText:
    """Retro floating damage indicator that pops and arcs like classic arcade."""

    __slots__ = ("pos", "vel", "life", "max_life", "_shadow", "_text")

    def __init__(
        self,
        pos: Vector2,
        text: str = "-1",
        color: tuple[int, int, int] = (255, 68, 68),
        font_size: int = 18,
    ) -> None:
        self.pos = Vector2(pos.x, pos.y - 6.0)
        self.vel = Vector2(random.uniform(-0.8, 0.8), -2.6)
        self.life = 0.60
        self.max_life = 0.60
        font = pygame.font.Font(None, font_size)
        self._shadow = font.render(text, False, (10, 10, 15)).convert_alpha()
        self._text = font.render(text, False, color).convert_alpha()

    @property
    def is_alive(self) -> bool:
        return self.life > 0.0

    def update(self, dt: float) -> None:
        if not self.is_alive:
            return
        self.life -= dt
        self.vel.y += 6.5 * dt
        self.pos += self.vel * (dt * 60.0)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_alive:
            return
        progress = clamp(1.0 - (self.life / self.max_life), 0.0, 1.0)
        alpha = int(clamp(lerp(255.0, 0.0, progress * progress), 0.0, 255.0))
        self._shadow.set_alpha(alpha)
        self._text.set_alpha(alpha)
        x = int(self.pos.x) - self._text.get_width() // 2
        y = int(self.pos.y) - self._text.get_height() // 2
        surface.blit(self._shadow, (x + 1, y + 1))
        surface.blit(self._text, (x, y))


# ---------------------------------------------------------------------------
# Particle (optimised – draws directly, no per-frame Surface alloc)
# ---------------------------------------------------------------------------

class Particle:
    """Pixelated debris and sparks driven by 2D vector physics."""

    __slots__ = (
        "pos", "vel", "color", "start_size", "life", "max_life",
        "friction", "gravity", "spark", "pixel_block",
    )

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

        # Draw directly with opaque colour – skip alpha-surface allocation.
        # Fading is approximated by darkening the colour toward background.
        fade = 1.0 - progress  # 1 → 0
        r = int(self.color[0] * fade)
        g = int(self.color[1] * fade)
        b = int(self.color[2] * fade)
        col = (r, g, b)

        if self.spark:
            length = max(2.0, self.vel.length() * 1.2)
            lsq = self.vel.length_squared()
            direction = self.vel.normalize() if lsq > 0.001 else Vector2(1, 0)
            end_pos = self.pos + direction * length
            pygame.draw.line(
                surface, col,
                (int(self.pos.x), int(self.pos.y)),
                (int(end_pos.x), int(end_pos.y)),
                current_size,
            )
        elif self.pixel_block:
            sz = max(2, current_size)
            pygame.draw.rect(
                surface, col,
                (int(self.pos.x - sz // 2), int(self.pos.y - sz // 2), sz, sz),
            )
        else:
            r_sz = max(1, current_size)
            pygame.draw.circle(
                surface, col,
                (int(self.pos.x), int(self.pos.y)),
                r_sz,
            )


# ---------------------------------------------------------------------------
# Shockwave Ring (optimised – draws directly)
# ---------------------------------------------------------------------------

class ShockwaveRing:
    """Expanding pixel blast ring."""

    __slots__ = ("center", "max_radius", "color", "life", "max_life")

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
        width = max(1, int(lerp(3.0, 1.0, t)))
        if radius <= 0:
            return

        # Fade by darkening colour
        fade = 1.0 - t
        col = (
            int(self.color[0] * fade),
            int(self.color[1] * fade),
            int(self.color[2] * fade),
        )
        pygame.draw.circle(
            surface, col,
            (int(self.center.x), int(self.center.y)),
            radius, width,
        )


# ---------------------------------------------------------------------------
# Particle Manager
# ---------------------------------------------------------------------------

class ParticleManager:
    """Orchestrates pixel explosions, floating texts, and muzzle sparks."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.shockwaves: list[ShockwaveRing] = []
        self.floating_texts: list[FloatingText] = []

    def spawn_floating_damage(
        self, center: Vector2, text: str = "-1", color: tuple[int, int, int] = (255, 68, 68)
    ) -> None:
        self.floating_texts.append(FloatingText(center, text=text, color=color))

    def spawn_explosion(
        self,
        center: Vector2,
        primary_color: tuple[int, int, int] = (255, 180, 50),
        count: int = 12,
    ) -> None:
        self.shockwaves.append(
            ShockwaveRing(center, max_radius=22.0, color=(255, 220, 120), duration=0.22)
        )
        for _ in range(count):
            angle = random.uniform(0.0, 360.0)
            speed = random.uniform(1.2, 4.0)
            vel = Vector2.from_polar((speed, angle))
            choice = random.random()
            if choice < 0.4:
                color = (255, 235, 100)
                size = random.uniform(2.5, 3.5)
                life = random.uniform(0.15, 0.28)
                spark = True
            elif choice < 0.8:
                color = primary_color
                size = random.uniform(2.5, 4.0)
                life = random.uniform(0.18, 0.32)
                spark = False
            else:
                color = (70, 75, 88)
                size = random.uniform(2.5, 4.0)
                life = random.uniform(0.22, 0.38)
                spark = False

            self.particles.append(
                Particle(
                    pos=center, vel=vel, color=color, size=size,
                    life_seconds=life, friction=0.90,
                    gravity=Vector2(0, 3.5), spark=spark, pixel_block=True,
                )
            )

    def spawn_muzzle_flash(
        self,
        tip: Vector2,
        direction_deg: float,
        color: tuple[int, int, int] = (255, 220, 100),
        count: int = 6,
    ) -> None:
        for _ in range(count):
            angle = direction_deg + random.uniform(-20.0, 20.0)
            speed = random.uniform(2.0, 4.5)
            vel = Vector2.from_polar((speed, angle))
            self.particles.append(
                Particle(
                    pos=tip, vel=vel, color=color,
                    size=random.uniform(2.0, 3.0),
                    life_seconds=random.uniform(0.08, 0.14),
                    friction=0.86, spark=True, pixel_block=True,
                )
            )

    def spawn_wall_debris(
        self,
        center: Vector2,
        color: tuple[int, int, int] = (180, 85, 55),
        count: int = 8,
    ) -> None:
        for _ in range(count):
            angle = random.uniform(0.0, 360.0)
            speed = random.uniform(1.2, 3.5)
            vel = Vector2.from_polar((speed, angle))
            self.particles.append(
                Particle(
                    pos=center, vel=vel, color=color,
                    size=random.uniform(2.0, 3.5),
                    life_seconds=random.uniform(0.16, 0.30),
                    friction=0.91, gravity=Vector2(0, 4.0),
                    spark=False, pixel_block=True,
                )
            )

    # ------------------------------------------------------------------
    # Batch update / draw with in-place list compaction
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        # In-place compaction avoids building a new list every frame
        particles = self.particles
        write = 0
        for i in range(len(particles)):
            p = particles[i]
            p.update(dt)
            if p.is_alive:
                particles[write] = p
                write += 1
        del particles[write:]

        shockwaves = self.shockwaves
        write = 0
        for i in range(len(shockwaves)):
            s = shockwaves[i]
            s.update(dt)
            if s.is_alive:
                shockwaves[write] = s
                write += 1
        del shockwaves[write:]

        texts = self.floating_texts
        write = 0
        for i in range(len(texts)):
            ft = texts[i]
            ft.update(dt)
            if ft.is_alive:
                texts[write] = ft
                write += 1
        del texts[write:]

    def draw(self, surface: pygame.Surface) -> None:
        for s in self.shockwaves:
            s.draw(surface)
        for p in self.particles:
            p.draw(surface)
        for ft in self.floating_texts:
            ft.draw(surface)
