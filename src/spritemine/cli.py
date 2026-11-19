"""Minimal command-line workbench; GUI is a later milestone."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .background import (
    attribute_strip,
    bonus_background_summary,
    compare_background_staging,
    pattern_strip,
    plains_quadrants,
)
from .chr import export_chr
from .player import inspect_recipes, reconstruct_player, validate_player
from .rom import RomFormatError, load_rom
from .world1_1 import compare_bonus, reconstruct_bonus


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spritemine", description="Read-only NES ROM explorer")
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect", help="Show validated iNES information as JSON")
    inspect.add_argument("rom", help="Path to .nes or single-ROM .zip")
    export = sub.add_parser("chr-export", help="Export grayscale CHR-ROM tiles with manifest")
    export.add_argument("rom")
    export.add_argument("--output", required=True, help="Destination directory")
    selector = export.add_mutually_exclusive_group()
    selector.add_argument("--bank", type=int, help="Single 8 KiB CHR bank (0-based)")
    selector.add_argument("--tile", type=int, help="Single global 8x8 tile index (0-based)")
    recipes = sub.add_parser("inspect-player-recipes", help="Inspect all 81 SMB3 PRG1 recipes")
    recipes.add_argument("rom")
    sprite = sub.add_parser("reconstruct-sprite", help="Decode a canonical small-Mario silhouette")
    sprite.add_argument("rom")
    sprite.add_argument("recipe", type=lambda value: int(value, 0), help="Recipe ID, e.g. 0x3E")
    sprite.add_argument("--include-pixels", action="store_true", help="Include private indexed pixels")
    validate = sub.add_parser("validate-sprite", help="Compare three canonical ROM-backed silhouettes")
    validate.add_argument("rom")
    level = sub.add_parser("reconstruct-level", help="Model World 1-1's two-screen bonus room")
    level.add_argument("rom")
    level.add_argument("--include-tiles", action="store_true", help="Include private logical tile bytes")
    compare = sub.add_parser("validate-level", help="Compare the model with a private 864-byte Tile_Mem dump")
    compare.add_argument("rom")
    compare.add_argument("tile_mem", type=Path)
    bg = sub.add_parser("reconstruct-background", help="Model bonus-room Plains PPU staging strips")
    bg.add_argument("rom")
    bg.add_argument("--column", type=int, default=0, help="Logical 16px column, 0..31")
    bg.add_argument("--half", type=int, choices=(0, 1), default=0, help="8px half: 0=left, 1=right")
    bg.add_argument("--include-strips", action="store_true", help="Print private source-derived pattern and attribute bytes")
    bgcheck = sub.add_parser("validate-background", help="Compare private 54/14-byte MesenCE staging dumps")
    bgcheck.add_argument("rom")
    bgcheck.add_argument("pattern_dump", type=Path)
    bgcheck.add_argument("attribute_dump", type=Path)
    bgcheck.add_argument("--column", type=int, default=0)
    bgcheck.add_argument("--half", type=int, choices=(0, 1), default=0)
    args = parser.parse_args(argv)
    try:
        rom = load_rom(args.rom)
        if args.command == "inspect":
            print(json.dumps(rom.metadata.to_dict(), indent=2, sort_keys=True))
        elif args.command == "chr-export":
            manifest = export_chr(rom, args.output, bank=args.bank, tile=args.tile)
            print(manifest)
        else:
            if args.command == "inspect-player-recipes":
                result = inspect_recipes(rom)
            elif args.command == "reconstruct-sprite":
                result, pixels = reconstruct_player(rom, args.recipe)
                if args.include_pixels:
                    result["indexed_pixels"] = list(pixels)
            elif args.command == "validate-sprite":
                result = validate_player(rom)
            else:
                result, tiles = reconstruct_bonus(rom)
                if args.command in ("reconstruct-background", "validate-background"):
                    layout = plains_quadrants(rom)
                    report = bonus_background_summary(rom, tiles, args.column, args.half)
                    report["logical_map_sha256"] = result["map_sha256"]
                    if args.command == "reconstruct-background" and args.include_strips:
                        report["pattern_strip"] = list(pattern_strip(tiles, layout, args.column, args.half))
                        report["attribute_strip"] = list(attribute_strip(tiles, args.column & ~1))
                    elif args.command == "validate-background":
                        report["comparison"] = compare_background_staging(
                            pattern_strip(tiles, layout, args.column, args.half),
                            attribute_strip(tiles, args.column & ~1),
                            args.pattern_dump.read_bytes(), args.attribute_dump.read_bytes(),
                        )
                    result = report
                elif args.command == "validate-level":
                    result["comparison"] = compare_bonus(tiles, args.tile_mem)
                elif args.include_tiles:
                    result["tiles"] = list(tiles)
            print(json.dumps(result, indent=2, sort_keys=True))
            if args.command == "validate-sprite" and not result["passed"]:
                return 1
            if args.command in ("validate-level", "validate-background") and not result["comparison"]["matches"]:
                return 1
        return 0
    except (RomFormatError, OSError, ValueError) as exc:
        print(f"SpriteMine: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
