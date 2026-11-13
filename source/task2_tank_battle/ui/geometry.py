"""Mathematical and geometric utilities for Pygame UI rendering.

Built on top of pygame.math (Vector2, clamp, lerp) to provide procedural
shapes, lighting calculations, rotation matrices, and smooth interpolation.
"""

import math
import pygame
from pygame.math import Vector2, clamp, lerp


def shortest_angle_diff(source_deg: float, target_deg: float) -> float:
    """Calculate the shortest angular difference in degrees (-180 to 180)."""
    return (target_deg - source_deg + 180.0) % 360.0 - 180.0


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """Hermite interpolation between edge0 and edge1 with zero 1st derivatives."""
    if edge1 == edge0:
        return 0.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smootherstep(t: float) -> float:
    """Ken Perlin's quintic smootherstep with zero 1st and 2nd derivatives.

    Ensures zero acceleration at start and stop for buttery-smooth animation:
    6*t^5 - 15*t^4 + 10*t^3
    """
    f = clamp(t, 0.0, 1.0)
    return f * f * f * (f * (f * 6.0 - 15.0) + 10.0)


def cosine_ease_in_out(t: float) -> float:
    """Smooth cosine ease-in-out S-curve."""
    f = clamp(t, 0.0, 1.0)
    return 0.5 * (1.0 - math.cos(f * math.pi))


def lerp_angle(source_deg: float, target_deg: float, t: float) -> float:
    """Interpolate smoothly between two angles along the shortest arc."""
    factor = clamp(t, 0.0, 1.0)
    return source_deg + shortest_angle_diff(source_deg, target_deg) * factor


def lerp_color(
    color_a: tuple[int, int, int] | tuple[int, int, int, int],
    color_b: tuple[int, int, int] | tuple[int, int, int, int],
    t: float,
) -> tuple[int, ...]:
    """Linearly interpolate each channel between two RGB or RGBA colors."""
    factor = clamp(t, 0.0, 1.0)
    return tuple(
        int(clamp(lerp(float(ca), float(cb), factor), 0.0, 255.0))
        for ca, cb in zip(color_a, color_b)
    )


def create_regular_polygon(
    center: Vector2, radius: float, sides: int, start_angle: float = 0.0
) -> list[Vector2]:
    """Generate vertices of a regular polygon using polar coordinates."""
    if sides < 3:
        return [center]
    step = 360.0 / sides
    return [
        center + Vector2.from_polar((radius, start_angle + i * step))
        for i in range(sides)
    ]


def create_chamfered_box(
    center: Vector2,
    width: float,
    height: float,
    chamfer: float,
    angle_deg: float = 0.0,
) -> list[Vector2]:
    """Generate an 8-sided chamfered (beveled) rectangle rotated by angle_deg.

    Uses 2D vector transformations to bevel each of the four corners.
    """
    half_w = width * 0.5
    half_h = height * 0.5
    c = clamp(chamfer, 0.0, min(half_w, half_h))

    # Vertices in clockwise order relative to center
    raw_points = [
        Vector2(half_w - c, -half_h),
        Vector2(half_w, -half_h + c),
        Vector2(half_w, half_h - c),
        Vector2(half_w - c, half_h),
        Vector2(-half_w + c, half_h),
        Vector2(-half_w, half_h - c),
        Vector2(-half_w, -half_h + c),
        Vector2(-half_w + c, -half_h),
    ]

    if abs(angle_deg) > 0.001:
        return [center + pt.rotate(angle_deg) for pt in raw_points]
    return [center + pt for pt in raw_points]


def calculate_bevel_lighting(
    normal: Vector2,
    light_dir: Vector2,
    base_color: tuple[int, int, int],
    intensity: float = 0.35,
) -> tuple[int, int, int]:
    """Compute directional Lambertian shading on a polygon face.

    Uses Vector2 dot product between surface normal and incident light vector.
    """
    if normal.length_squared() < 0.0001 or light_dir.length_squared() < 0.0001:
        return base_color

    dot = normal.normalize().dot(light_dir.normalize())
    if dot > 0:
        # Highlight: blend toward white
        return lerp_color(base_color, (255, 255, 255), dot * intensity)
    # Shadow: blend toward black
    return lerp_color(base_color, (0, 0, 0), -dot * intensity)


def create_cracks(
    center: Vector2,
    radius: float,
    seed: int,
    num_branches: int = 4,
) -> list[list[Vector2]]:
    """Procedurally generate fracture crack lines using radial vector offsets."""
    cracks: list[list[Vector2]] = []
    base_angle = (seed * 73.0) % 360.0
    for i in range(num_branches):
        angle = base_angle + (i * 360.0 / num_branches) + ((seed + i * 37) % 30 - 15)
        path = [center]
        curr = Vector2(center)
        seg_count = 2 + (seed + i) % 2
        for seg in range(seg_count):
            reach = (radius / seg_count) * (0.8 + ((seed + seg * 13) % 40) / 100.0)
            jitter_angle = angle + ((seed * 19 + seg * 43) % 40 - 20)
            curr = curr + Vector2.from_polar((reach, jitter_angle))
            path.append(Vector2(curr))
        cracks.append(path)
    return cracks
