"""Local scene export. Run with python -m spritemine.scene_export."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, __version__ as pillow_version

from .scene import Scene


def encode_gif(scene, destination):
    # One global palette preserves colors across frames. Reject lossy exports.
    if scene.tick_ms % 10 or scene.ticks * scene.tick_ms > 655350:
        raise ValueError("GIF needs 10 ms ticks and a total duration at most 655350 ms")
    colors = set()
    for tick in range(scene.ticks):
        entries = scene.render(tick).getcolors(256)
        if entries is None:
            raise ValueError("GIF exceeds the 256-color limit")
        colors.update(color for _, color in entries)
        if len(colors) > 256:
            raise ValueError("GIF exceeds the 256-color limit across frames")
    palette = Image.new("P", (1, 1))
    palette.putpalette(bytes(channel for color in sorted(colors) for channel in color))

    def indexed(tick):
        return scene.render(tick).quantize(palette=palette, dither=Image.Dither.NONE)

    indexed(0).save(
        destination, format="GIF", save_all=True,
        append_images=(indexed(tick) for tick in range(1, scene.ticks)),
        duration=scene.tick_ms, loop=0, optimize=False, disposal=1,
    )


def export(recipe, directory):
    scene = Scene.load(recipe)
    # A fresh directory protects local inputs and previous exports.
    directory.mkdir(parents=True, exist_ok=False)
    gif = directory / "scene.gif"
    try:
        encode_gif(scene, gif)
        scene.render(animated=False).save(directory / "static.png")
    except (ValueError, OSError):
        gif.unlink(missing_ok=True)
        (directory / "static.png").unlink(missing_ok=True)
        directory.rmdir()
        raise
    manifest = {
        "recipe_sha256": scene.recipe_sha256,
        "pillow": pillow_version,
        "size": scene.size,
        "ticks": scene.ticks,
        "tick_ms": scene.tick_ms,
        "assets": scene.sources,
        "outputs": {
            name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("static.png", "scene.gif")
        },
    }
    if scene.staging_provenance is not None:
        manifest["staging_provenance"] = scene.staging_provenance
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        export(args.recipe, args.output)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(2, f"scene export: {exc}\n")


if __name__ == "__main__":
    main()
