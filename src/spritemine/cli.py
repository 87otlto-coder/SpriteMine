"""Minimal command-line workbench; GUI is a later milestone."""

from __future__ import annotations

import argparse
import json
import sys

from .chr import export_chr
from .rom import RomFormatError, load_rom


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
    args = parser.parse_args(argv)
    try:
        rom = load_rom(args.rom)
        if args.command == "inspect":
            print(json.dumps(rom.metadata.to_dict(), indent=2, sort_keys=True))
        else:
            manifest = export_chr(rom, args.output, bank=args.bank, tile=args.tile)
            print(manifest)
        return 0
    except (RomFormatError, OSError, ValueError) as exc:
        print(f"SpriteMine: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
