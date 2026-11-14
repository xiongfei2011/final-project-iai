"""Interpolation helpers for Pygame animations."""

from pygame.math import clamp


def shortest_angle_diff(source_deg: float, target_deg: float) -> float:
    """Calculate the shortest angular difference in degrees (-180 to 180)."""
    return (target_deg - source_deg + 180.0) % 360.0 - 180.0


def smootherstep(t: float) -> float:
    """Ease motion in and out with zero acceleration at both endpoints."""
    f = clamp(t, 0.0, 1.0)
    return f * f * f * (f * (f * 6.0 - 15.0) + 10.0)


def lerp_angle(source_deg: float, target_deg: float, t: float) -> float:
    """Interpolate smoothly between two angles along the shortest arc."""
    factor = clamp(t, 0.0, 1.0)
    return source_deg + shortest_angle_diff(source_deg, target_deg) * factor
