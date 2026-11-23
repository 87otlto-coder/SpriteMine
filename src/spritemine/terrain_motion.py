"""Compile terrain-aware actor motion into ordinary scene cels."""

from __future__ import annotations

from dataclasses import dataclass

from .scene import integers


@dataclass(frozen=True)
class Terrain:
    tile_size: tuple[int, int]
    origin: tuple[int, int]
    solid: frozenset[tuple[int, int]]

    @classmethod
    def from_recipe(cls, spec):
        tile_size = integers(spec["tile_size"], 2, "terrain tile size")
        if min(tile_size) < 1:
            raise ValueError("terrain tile size must be positive")
        return cls(
            tile_size,
            integers(spec.get("origin", [0, 0]), 2, "terrain origin"),
            frozenset(
                (column, row)
                for row, cells in enumerate(spec["rows"])
                for column, value in enumerate(cells)
                if value
            ),
        )

    def intersects(self, x, y, width, height):
        tw, th = self.tile_size
        ox, oy = self.origin
        return any(
            (column, row) in self.solid
            for row in range((y - oy) // th, (y - oy + height - 1) // th + 1)
            for column in range((x - ox) // tw, (x - ox + width - 1) // tw + 1)
        )


def motion_cels(at, spec, terrain):
    """Sample a small tile-collision model, with reset allowed offscreen below hide_y.

    Sprite PNGs share the same top-left anchor. Bounds describe collision, and
    left/right clips can use different animation assets.
    """
    width, height = integers(spec["bounds"], 2, "actor bounds")
    period, speed, max_fall, jump, frame_ticks, hide_y, direction = integers(
        [
            spec["period"], spec.get("speed", 1), spec.get("max_fall", 4),
            spec.get("jump", 0), spec.get("frame_ticks", 1), spec["hide_y"],
            spec.get("direction", 1),
        ], 7, "motion settings",
    )
    if min(width, height, period, speed, max_fall, frame_ticks) < 1 or jump < 0:
        raise ValueError("invalid actor bounds, timing or speed")
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1")
    clips = {-1: spec["left"], 1: spec["right"]}
    if not all(clips.values()):
        raise ValueError("both motion clips must contain frames")
    x, y = at
    if terrain.intersects(x, y, width, height):
        raise ValueError("actor spawn intersects terrain")
    vy = 0
    cels = []
    for tick in range(period):
        clip = clips[direction]
        asset = clip[(tick // frame_ticks) % len(clip)] if y < hide_y else None
        cels.append({"asset": asset, "offset": [x - at[0], y - at[1]], "ticks": 1})
        if asset is None:
            continue

        grounded = terrain.intersects(x, y + 1, width, height)
        for _ in range(speed):
            nx = x + direction
            hits_wall = terrain.intersects(nx, y, width, height)
            leading_x = nx + width - 1 if direction > 0 else nx
            unsupported = not terrain.intersects(leading_x, y + height, 1, 1)
            if hits_wall or (grounded and spec.get("turn_at_edge", False) and unsupported):
                direction *= -1
                break
            x = nx

        if grounded and jump:
            vy = -jump
        else:
            vy = min(vy + 1, max_fall)
        step = -1 if vy < 0 else 1
        for _ in range(abs(vy)):
            if terrain.intersects(x, y + step, width, height):
                vy = 0
                break
            y += step

    # A visible simulation must close. An offscreen tail permits a creative reset.
    if cels[-1]["asset"] is not None and (x, y) != at:
        raise ValueError("motion must return to its spawn or end with an offscreen hold")
    return cels
