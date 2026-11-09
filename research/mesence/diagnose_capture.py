"""Inspect captured OAM and end-of-frame PPU pattern consistency.

Reports derived metadata only: no ROM bytes, image pixels, or copyrighted art
are written. Successful structural capture verification must precede diagnosis.
A blank PPU pattern at endFrame is not proof of a faulty emulator; MMC3 mapping
may have changed since rendering the visible frame.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__:
    from .verify_capture import verify_directory
else:
    from verify_capture import verify_directory


def analyze_frame(oam: bytes, pattern: bytes, sprite_height: int) -> dict[str, object]:
    """Analyze potentially on-screen hardware entries, not semantic characters."""
    if len(oam) != 256 or len(pattern) != 8192 or sprite_height not in (8, 16):
        raise ValueError("Expected 256 OAM bytes, 8192 PPU bytes, and 8/16 pixel sprites")
    entries: list[dict[str, int | bool | str | None]] = []
    for index in range(64):
        y, tile, attributes, x = oam[index * 4:index * 4 + 4]
        screen_y = y + 1  # NES sprite Y is one scanline above its first visible row.
        if screen_y >= 240:
            continue
        result: dict[str, int | bool | str | None] = {
            "oam_index": index,
            "x": x,
            "y": screen_y,
            "tile": tile,
            "attributes": attributes,
            "flip_horizontal": bool(attributes & 0x40),
            "flip_vertical": bool(attributes & 0x80),
            "behind_background": bool(attributes & 0x20),
            "palette_slot": attributes & 3,
        }
        if sprite_height == 16:
            table = tile & 1
            start = (table << 12) | ((tile & 0xFE) << 4)
            result["ppu_pattern_base"] = start
            result["ppu_pattern_table"] = table
            result["nonzero_pattern_bytes_at_capture"] = sum(
                value != 0 for value in pattern[start:start + 32]
            )
            result["blank_pattern_at_capture"] = not any(pattern[start:start + 32])
        else:
            result["ppu_pattern_base"] = None
            result["ppu_pattern_table"] = None
            result["nonzero_pattern_bytes_at_capture"] = None
            result["blank_pattern_at_capture"] = None
        entries.append(result)

    blank = sum(entry["blank_pattern_at_capture"] is True for entry in entries)
    return {
        "possible_on_screen_oam_entries": entries,
        "possible_on_screen_oam_count": len(entries),
        "blank_pattern_entry_count": blank,
        "pattern_bytes_nonzero_lower_4k": sum(v != 0 for v in pattern[:4096]),
        "pattern_bytes_nonzero_upper_4k": sum(v != 0 for v in pattern[4096:]),
        "warning": (
            "Visible-position OAM entries reference blank patterns in the endFrame "
            "snapshot; verify mapper state at the rendering scanline."
            if blank else None
        ),
    }


def diagnose_directory(folder: Path) -> dict[str, object]:
    verified = verify_directory(folder)
    manifests = sorted(folder.glob("frame_??????????.json"))
    frames: list[dict[str, object]] = []
    screens: list[tuple[int, int, bytes]] = []
    for manifest in manifests:
        meta = json.loads(manifest.read_text(encoding="utf-8"))
        names = meta["files"]
        oam = (folder / names["oam"]).read_bytes()
        pattern = (folder / names["ppu_pattern"]).read_bytes()
        screen = (folder / names["screen_rgb"]).read_bytes()
        summary = analyze_frame(oam, pattern, meta["sprite_height"])
        frames.append({"frame_count": meta["frame_count"], **summary})
        screens.append((meta["screen_width"], meta["screen_height"], screen))
    differences: list[dict[str, int | None]] = []
    for i in range(1, len(screens)):
        w0, h0, a = screens[i - 1]
        w1, h1, b = screens[i]
        if (w0, h0) != (w1, h1):
            differences.append({"from_frame": frames[i-1]["frame_count"],
                                "to_frame": frames[i]["frame_count"],
                                "changed_pixels": None})
        else:
            changed = sum(a[j:j + 3] != b[j:j + 3] for j in range(0, len(a), 3))
            differences.append({"from_frame": frames[i-1]["frame_count"],
                                "to_frame": frames[i]["frame_count"],
                                "changed_pixels": changed})
    return {
        "result": "derived_pattern_diagnostics_only",
        "structural_validation": verified["result"],
        "frames": frames,
        "screen_pixel_differences": differences,
        "not_proven": [
            "sprite patterns in snapshot were the ones used during visible scanlines",
            "actual sprite visibility after priority and scanline limits",
            "physical ROM bank mapping or semantic character identification",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect MesenCE OAM/pattern consistency")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        result = diagnose_directory(args.directory)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Capture diagnosis unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
