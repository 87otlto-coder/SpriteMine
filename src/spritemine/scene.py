"""Fixed-camera composition from local images and an editable JSON recipe."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


def integers(value, count, label):
    if not isinstance(value, (tuple, list)) or len(value) != count:
        raise ValueError(f"{label} must contain {count} integers")
    if any(type(item) is not int for item in value):
        raise ValueError(f"{label} must contain {count} integers")
    return tuple(value)


def viewport_to_world(point, scroll, viewport_origin=(0, 0)):
    """Map capture pixels using both scroll axes and the playfield's screen origin."""
    x, y = integers(point, 2, "point")
    sx, sy = integers(scroll, 2, "scroll")
    ox, oy = integers(viewport_origin, 2, "viewport origin")
    return x + sx - ox, y + sy - oy


@dataclass(frozen=True)
class Cel:
    asset: str | None
    offset: tuple[int, int]
    ticks: int


@dataclass(frozen=True)
class Track:
    position: tuple[int, int]
    cels: tuple[Cel, ...]
    period: int
    phase: int

    def cel_at(self, tick):
        local = (tick + self.phase) % self.period
        for cel in self.cels:
            if local < cel.ticks:
                return cel
            local -= cel.ticks
        raise AssertionError("track period differs from cel durations")


@dataclass(frozen=True)
class Layer:
    static: Image.Image
    tracks: tuple[Track, ...]


def load_assets(specs, directory):
    assets = {}
    sources = {}
    for name, spec in specs.items():
        path = (directory / spec["file"]).resolve()
        if not path.is_relative_to(directory):
            raise ValueError(f"asset {name}: path escapes the recipe directory")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if spec.get("sha256", digest) != digest:
            raise ValueError(f"asset {name}: SHA-256 mismatch")
        with Image.open(io.BytesIO(data), formats=["PNG"]) as source:
            if source.is_animated:
                raise ValueError(f"asset {name}: supply one PNG per frame")
            if "crop" in spec:
                x, y, width, height = integers(spec["crop"], 4, "crop")
                if min(x, y) < 0 or min(width, height) < 1 or (
                    x + width > source.width or y + height > source.height
                ):
                    raise ValueError(f"asset {name}: crop lies outside the PNG")
                image = source.crop((x, y, x + width, y + height))
            else:
                image = source.copy()
        if "palette" in spec:
            if image.mode != "P":
                raise ValueError(f"asset {name}: palette overrides require indexed PNG")
            palette = spec["palette"]
            if not 1 <= len(palette) <= 256:
                raise ValueError(f"asset {name}: palette must have 1 to 256 RGBA entries")
            colors = [integers(color, 4, "RGBA entry") for color in palette]
            if any(not 0 <= channel <= 255 for color in colors for channel in color):
                raise ValueError(f"asset {name}: palette channel outside 0 to 255")
            if image.getextrema()[1] >= len(colors):
                raise ValueError(f"asset {name}: palette does not cover all pixel indices")
            image.info.pop("transparency", None)
            image.putpalette(bytes(channel for color in colors for channel in color), "RGBA")
        assets[name] = image.convert("RGBA")
        sources[name] = {
            "file": spec["file"],
            "sha256": digest,
            "provenance": spec.get("provenance", {}),
        }
    return assets, sources


class Scene:
    """Compiled recipe. Layers are painted in declaration order, back to front."""

    def __init__(self, recipe, directory):
        if recipe["version"] != 1:
            raise ValueError("unsupported scene recipe version")
        self.staging_provenance = recipe.get("staging_provenance")
        self.size = integers(recipe["size"], 2, "world size")
        self.ticks, self.tick_ms = integers(
            [recipe["ticks"], recipe["tick_ms"]], 2, "timing"
        )
        if min(*self.size, self.ticks, self.tick_ms) < 1:
            raise ValueError("world size and timing must be positive")
        self.background = integers(recipe["background"], 3, "background RGB")
        if any(not 0 <= channel <= 255 for channel in self.background):
            raise ValueError("background channel outside 0 to 255")
        self.assets, self.sources = load_assets(recipe["assets"], directory.resolve())
        tile_size = integers(recipe.get("tile_size", [1, 1]), 2, "tile size")
        if min(tile_size) < 1:
            raise ValueError("tile size must be positive")
        from .terrain_motion import Terrain

        self.terrain = Terrain.from_recipe(recipe["terrain"]) if "terrain" in recipe else None
        self.layers = tuple(self._layer(layer, tile_size) for layer in recipe["layers"])

    @classmethod
    def load(cls, path: Path):
        data = path.read_bytes()
        scene = cls(json.loads(data.decode("utf-8-sig")), path.parent)
        scene.recipe_sha256 = hashlib.sha256(data).hexdigest()
        return scene

    def _layer(self, layer, tile_size):
        static = Image.new("RGBA", self.size)
        tw, th = tile_size
        ox, oy = integers(layer.get("tile_origin", [0, 0]), 2, "tile origin")
        for row, tiles in enumerate(layer.get("tiles", [])):
            for column, name in enumerate(tiles):
                if name is None:
                    continue
                tile = self.assets[name]
                if tile.size != tile_size:
                    raise ValueError(f"asset {name}: tile dimensions differ from tile size")
                static.alpha_composite(tile, (ox + column * tw, oy + row * th))
        for stamp in layer.get("stamps", []):
            position = integers(stamp["at"], 2, "stamp position")
            if "viewport" in stamp:
                viewport = stamp["viewport"]
                position = viewport_to_world(
                    position, viewport["scroll"], viewport.get("origin", [0, 0])
                )
            static.alpha_composite(self.assets[stamp["asset"]], position)
        return Layer(static, tuple(self._track(spec) for spec in layer.get("tracks", [])))

    def _track(self, spec):
        cels = []
        at = integers(spec["at"], 2, "track position")
        if "motion" in spec:
            from .terrain_motion import motion_cels

            if self.terrain is None or "cels" in spec:
                raise ValueError("motion requires terrain and cannot also specify cels")
            if spec["motion"]["hide_y"] < self.size[1]:
                raise ValueError("motion hide_y must be outside the canvas")
            entries = motion_cels(at, spec["motion"], self.terrain)
        else:
            entries = spec["cels"]
        for entry in entries:
            ticks, = integers([entry["ticks"]], 1, "cel duration")
            if ticks < 1:
                raise ValueError("cel duration must be positive")
            asset = entry.get("asset")
            if asset is not None and asset not in self.assets:
                raise ValueError(f"unknown animation asset: {asset}")
            cels.append(Cel(asset, integers(entry.get("offset", [0, 0]), 2, "offset"), ticks))
        period = sum(cel.ticks for cel in cels)
        if not period or self.ticks % period:
            raise ValueError("each track period must divide the scene period")
        phase, = integers([spec.get("phase", 0)], 1, "phase")
        return Track(at, tuple(cels), period, phase)

    def render(self, tick=0, *, animated=True):
        canvas = Image.new("RGBA", self.size, (*self.background, 255))
        for layer in self.layers:
            canvas.alpha_composite(layer.static)
            if animated:
                for track in layer.tracks:
                    cel = track.cel_at(tick)
                    if cel.asset is not None:
                        x, y = track.position
                        dx, dy = cel.offset
                        canvas.alpha_composite(self.assets[cel.asset], (x + dx, y + dy))
        return canvas.convert("RGB")
