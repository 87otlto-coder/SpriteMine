"""Generate a native-size, original regression scene using local PNG inputs."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def create_fixture(directory):
    directory.mkdir(parents=True, exist_ok=True)
    atlas = Image.new("P", (8, 4))
    atlas.putdata([1, 1, 1, 1, 0, 2, 2, 0] + [3, 3, 3, 3, 2, 2, 2, 2] * 3)
    atlas.putpalette([0, 0, 0, 85, 85, 85, 170, 170, 170, 255, 255, 255])
    atlas.save(directory / "atlas.png", bits=2)

    actors = Image.new("RGBA", (16, 4))
    draw = ImageDraw.Draw(actors)
    draw.rectangle((0, 1, 3, 3), fill="#c96e54")
    draw.point((3, 1), fill="#f9e7ca")
    draw.rectangle((4, 0, 7, 3), fill="#4caaa1")
    draw.point((4, 1), fill="#f9e7ca")
    draw.rectangle((8, 1, 11, 3), fill="#e7b45e")
    draw.rectangle((12, 0, 15, 3), fill="#e8f2b0")
    actors.save(directory / "actors.png")

    palette = [[0, 0, 0, 0], [136, 166, 153, 255], [151, 96, 155, 255], [55, 76, 105, 255]]
    assets = {
        "floor": {"file": "atlas.png", "crop": [0, 0, 4, 4], "palette": palette},
        "sleeve": {"file": "atlas.png", "crop": [4, 0, 4, 4], "palette": palette},
    }
    for column, name in enumerate(("right", "left", "dim", "lit")):
        assets[name] = {"file": "actors.png", "crop": [column * 4, 0, 4, 4]}
    for asset in assets.values():
        asset["provenance"] = {"kind": "synthetic", "generator": "make_scene_fixture.py"}

    columns = 45
    solid = [[False] * columns for _ in range(27)]
    for row, start, end in ((3, 29, 40), (11, 13, 25), (22, 3, 9), (24, 31, 45), (26, 29, 45)):
        solid[row][start:end] = [True] * (end - start)
    tilemap = [["floor" if cell else None for cell in row] for row in solid]

    def mover(x, edge=False, jump=0):
        return {
            "at": [x, 84],
            "motion": {
                "bounds": [4, 4], "period": 42, "hide_y": 108,
                "direction": -1 if edge else 1,
                "left": ["left"], "right": ["right"],
                "turn_at_edge": edge, "jump": jump,
            },
        }

    recipe = {
        "version": 1, "size": [180, 108], "tile_size": [4, 4],
        "background": [23, 33, 59], "ticks": 84, "tick_ms": 40,
        "assets": assets,
        "terrain": {"tile_size": [4, 4], "rows": solid},
        "layers": [
            {"tiles": tilemap},
            {"tracks": [
                mover(12, edge=True), mover(28), mover(32, jump=3),
                {"at": [140, 16], "phase": 4, "cels": [
                    {"asset": "dim", "ticks": 3}, {"asset": "lit", "ticks": 4},
                ]},
                {"at": [70, 40], "cels": [
                    {"asset": "lit", "ticks": 2},
                    {"asset": "dim", "offset": [0, -4], "ticks": 3},
                    {"asset": "lit", "ticks": 2},
                    {"ticks": 5},
                ]},
            ]},
            {"stamps": [{"asset": "sleeve", "at": [70, 40]}]},
        ],
    }
    path = directory / "recipe.json"
    path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(create_fixture(parser.parse_args().directory))
