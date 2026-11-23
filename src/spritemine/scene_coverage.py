"""Report two-dimensional tile occupancy and evidence from viewport comparisons."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

from .scene import Scene, integers
from .scene_input import compare_viewports, load_json


def coverage(recipe, references=None):
    config = load_json(recipe)
    scene = Scene.load(recipe)
    width, height = scene.size
    tw, th = integers(config.get("tile_size", [16, 16]), 2, "tile size")
    matches = {}
    differences = {}
    samples = compare_viewports(recipe, references) if references else []
    for sample in samples:
        tick = sample["tick"]
        x, y, w, h = sample["world_rect"]
        if sample["mismatched_pixels"]:
            target = differences
            left, top, right, bottom = sample["mismatch_bounds_in_crop"]
            bounds = (x + left, y + top, x + right - 1, y + bottom - 1)
        else:
            target = matches
            bounds = (x, y, x + w - 1, y + h - 1)
        if tick not in target:
            target[tick] = Image.new("1", scene.size)
        ImageDraw.Draw(target[tick]).rectangle(bounds, fill=1)

    cells = {}
    resolved = Image.new("1", scene.size)
    resolution = ImageDraw.Draw(resolved)
    for layer_index, layer in enumerate(config["layers"]):
        ox, oy = integers(layer.get("tile_origin", [0, 0]), 2, "tile origin")
        for row, tiles in enumerate(layer.get("tiles", [])):
            for col, name in enumerate(tiles):
                if name is None:
                    continue
                x, y = ox + col * tw, oy + row * th
                if x + tw <= 0 or y + th <= 0 or x >= width or y >= height:
                    continue
                resolution.rectangle((x, y, x + tw - 1, y + th - 1), fill=1)
                for grid_y in range(max(0, y) // th, (min(height, y + th) + th - 1) // th):
                    for grid_x in range(max(0, x) // tw, (min(width, x + tw) + tw - 1) // tw):
                        cells.setdefault((grid_x, grid_y), []).append(
                            {"layer": layer_index, "asset": name, "at": [x, y]}
                        )

    rows = []
    for y in range(0, height, th):
        row = []
        for x in range(0, width, tw):
            index = x // tw, y // th
            rect = x, y, min(x + tw, width), min(y + th, height)
            fully_resolved = resolved.crop(rect).getextrema() == (1, 1)
            suspect = [tick for tick, mask in sorted(differences.items())
                       if mask.crop(rect).getbbox()]
            verified = [tick for tick, mask in sorted(matches.items())
                        if fully_resolved and tick not in suspect
                        and mask.crop(rect).getextrema() == (1, 1)]
            row.append({"tiles": cells.get(index, []), "fully_resolved": fully_resolved,
                        "matched_ticks": verified, "mismatch_bounds_ticks": suspect})
        rows.append(row)
    return {
        "size": [width, height], "cell_size": [tw, th], "rows": rows,
        "recipe_sha256": scene.recipe_sha256, "samples": samples,
        "resolved_assets": scene.sources, "staging_provenance": config.get("staging_provenance"),
    }


def acceptance(report, required_ticks):
    """Count unresolved and unverified cells for explicitly requested scene ticks."""
    cells = [cell for row in report["rows"] for cell in row]
    unresolved = sum(not cell["fully_resolved"] for cell in cells)
    unverified = {
        tick: sum(tick not in cell["matched_ticks"] for cell in cells)
        for tick in sorted(set(required_ticks))
    }
    return {
        "cells": len(cells), "unresolved_cells": unresolved,
        "unverified_cells_by_tick": unverified,
        "passed": bool(unverified) and not unresolved and not any(unverified.values()),
    }


def inspection(report):
    lines = ["? missing tile coverage | . resolved | + matched | ! overlaps mismatch bounds",
             "Matches are for the listed ticks only. Stamps and tracks are excluded from tile occupancy."]
    if "acceptance" in report:
        gate = report["acceptance"]
        lines.append(f"Unresolved tile cells: {gate['unresolved_cells']} / {gate['cells']}")
        for tick, count in gate["unverified_cells_by_tick"].items():
            lines.append(f"Tick {tick} unverified cells: {count} / {gate['cells']}")
    for index, row in enumerate(report["rows"]):
        symbols = []
        for cell in row:
            if cell["mismatch_bounds_ticks"]:
                symbol = "!"
            elif cell["matched_ticks"]:
                symbol = "+"
            elif cell["fully_resolved"]:
                symbol = "."
            else:
                symbol = "?"
            symbols.append(symbol)
        lines.append(f"{index:03d} {''.join(symbols)}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--references", type=Path)
    parser.add_argument("--require-complete-tick", type=int, action="append", default=[])
    args = parser.parse_args()
    try:
        report = coverage(args.recipe, args.references)
        if args.require_complete_tick:
            report["acceptance"] = acceptance(report, args.require_complete_tick)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "coverage.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        (args.output / "coverage.txt").write_text(inspection(report), encoding="utf-8")
        return int(any(s["mismatched_pixels"] for s in report["samples"])
                   or ("acceptance" in report and not report["acceptance"]["passed"]))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(2, f"scene coverage: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
