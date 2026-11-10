"""Check one SMB3 sprite composition against a separate background-only render.

The reference must be captured from an independently replayed emulator state
with MesenCE's NES Video > Disable Sprites display option enabled. This script
cannot detect that GUI option, so the result is explicitly *conditional* on the
owner having used it. Never mutates ROMs/capture data or exports pixels.

Hard proof gates: same verified SMB3 ROM, frame, CPU/PPU boundary clocks,
startFrame PPU pattern/OAM/palette SHA-256, 256x240 RGB dimensions, known MMC3
mapping, and unchanged local 8px background ring. These checks are strong but
do NOT establish identical underlying nametable/scroll state by themselves.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .nes_palette_reference import sprite_rgba_from_default_reference
    from .sprite_components import decode_component
    from .analyze_render_capture import index_layer
    from .verify_phase_capture import verify_phase_session
except ImportError:
    from nes_palette_reference import sprite_rgba_from_default_reference
    from sprite_components import decode_component
    from analyze_render_capture import index_layer
    from verify_phase_capture import verify_phase_session


def _rgb(rgb: bytes, width: int, x: int, y: int) -> bytes:
    i = (y * width + x) * 3
    return rgb[i:i + 3]


def compare_sprite_background_region(
    foreground: bytes,
    background_only: bytes,
    width: int,
    height: int,
    indexed: dict[tuple[int, int], tuple[int, int]],
    palette_ram: bytes,
    *,
    margin: int = 8,
) -> dict[str, Any]:
    """Match expected sprite RGB and transparency against a separate BG render.

    For opaque sprite indices: normal screen must equal upstream default RGB.
    For zero indices: normal screen must equal the separately captured background.
    An 8px surrounding background ring is used as a same-scene control.
    """
    if not indexed:
        raise ValueError("No opaque candidate sprite pixels")
    if len(palette_ram) != 32:
        raise ValueError("NES palette RAM must contain 32 bytes")
    if width != 256 or height != 240:
        raise ValueError("Native 256x240 capture is required")
    if len(foreground) != width * height * 3 or len(background_only) != len(foreground):
        raise ValueError("RGB24 buffers do not match the declared dimensions")
    if type(margin) is not int or margin < 1 or margin > 32:
        raise ValueError("Ring margin must be 1 through 32 pixels")

    xs = [p[0] for p in indexed]
    ys = [p[1] for p in indexed]
    # Caller-selected 8x16 hardware sprites are permitted to be transparent
    # at the extremes; require explicit union bounds separately in the CLI.
    bbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    return compare_region_with_bounds(
        foreground, background_only, width, height,
        indexed, palette_ram, bbox=bbox, margin=margin,
    )


def compare_region_with_bounds(
    foreground: bytes,
    background_only: bytes,
    width: int,
    height: int,
    indexed: dict[tuple[int, int], tuple[int, int]],
    palette_ram: bytes,
    *,
    bbox: tuple[int, int, int, int],
    margin: int = 8,
) -> dict[str, Any]:
    """Compare full OAM bounding rectangle, including source-transparent holes."""
    if len(palette_ram) != 32:
        raise ValueError("NES palette RAM must contain 32 bytes")
    if width != 256 or height != 240:
        raise ValueError("Native 256x240 buffer required")
    if len(foreground) != width * height * 3 or len(background_only) != len(foreground):
        raise ValueError("RGB24 buffers do not match their dimensions")
    if type(margin) is not int or not 1 <= margin <= 32:
        raise ValueError("Ring margin must be 1..32")
    x0, y0, x1, y1 = bbox
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError("OAM rectangle is out of bounds")
    if not indexed or any(
        not (x0 <= x < x1 and y0 <= y < y1) for x, y in indexed
    ):
        raise ValueError("Candidate indexed pixels outside the rectangle or empty")

    expected_rgb: dict[tuple[int, int], bytes] = {}
    for point, (slot, index) in indexed.items():
        if index == 0:
            raise ValueError("The indexed opaque map must not contain index zero")
        rgba = sprite_rgba_from_default_reference(palette_ram, slot, index)
        expected_rgb[point] = bytes(rgba[:3])

    opaque_exact = opaque_mismatch = 0
    sprite_suppressed_diff = 0
    transparency_exact = transparency_mismatch = 0
    mismatch_samples = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            pos = (x, y)
            rendered = _rgb(foreground, width, x, y)
            bg = _rgb(background_only, width, x, y)
            if pos in expected_rgb:
                if rendered == expected_rgb[pos]:
                    opaque_exact += 1
                else:
                    opaque_mismatch += 1
                    if len(mismatch_samples) < 8:
                        mismatch_samples.append({"x": x, "y": y, "class": "opaque"})
                if bg != rendered:
                    sprite_suppressed_diff += 1
            else:
                if rendered == bg:
                    transparency_exact += 1
                else:
                    transparency_mismatch += 1
                    if len(mismatch_samples) < 8:
                        mismatch_samples.append({"x": x, "y": y, "class": "transparent"})

    ring_exact = ring_mismatch = 0
    ring = (
        max(0, x0 - margin), max(0, y0 - margin),
        min(width, x1 + margin), min(height, y1 + margin)
    )
    for y in range(ring[1], ring[3]):
        for x in range(ring[0], ring[2]):
            if x0 <= x < x1 and y0 <= y < y1:
                continue
            if _rgb(foreground, width, x, y) == _rgb(background_only, width, x, y):
                ring_exact += 1
            else:
                ring_mismatch += 1

    expected_opaque = len(expected_rgb)
    expected_transparent = (x1 - x0) * (y1 - y0) - expected_opaque
    if ring_mismatch:
        status = "unverified_different_background_context"
    elif opaque_mismatch or transparency_mismatch:
        status = "composited_region_mismatch"
    elif sprite_suppressed_diff == 0:
        status = "ambiguous_no_evidence_sprite_display_was_disabled"
    else:
        status = "region_exact_conditional_on_sprites_disabled_reference"
    return {
        "status": status,
        "bounds_xyxy_exclusive": list(bbox),
        "opaque_expected": expected_opaque,
        "opaque_reference_rgb_exact": opaque_exact,
        "opaque_reference_rgb_mismatches": opaque_mismatch,
        "sprite_visible_rgb_diff_from_reference": sprite_suppressed_diff,
        "transparent_expected": expected_transparent,
        "transparent_screen_equals_background": transparency_exact,
        "transparent_screen_mismatches": transparency_mismatch,
        "control_ring_margin": margin,
        "control_ring_exact": ring_exact,
        "control_ring_mismatches": ring_mismatch,
        "first_mismatch_positions": mismatch_samples,
        "limitation": (
            "Conditional on same saved state/inputs, identical background context, "
            "and an independently confirmed MesenCE NES Disable Sprites option; "
            "the GUI option is not recorded in the capture manifests"
        ),
    }


def analyze_two_renders(
    foreground_manifest: Path,
    background_manifest: Path,
    rom_path: Path,
    *,
    oam_indices: tuple[int, ...] = (10, 11),
    allow_synthetic_rom: bool = False,
) -> dict[str, Any]:
    """Strict paired-state verifier; output hashes/derived counts, never pixels."""
    if not oam_indices or len(set(oam_indices)) != len(oam_indices):
        raise ValueError("Specify distinct OAM indices")
    if any(type(x) is not int or not 0 <= x < 64 for x in oam_indices):
        raise ValueError("OAM indices must be 0..63")
    if Path(foreground_manifest).resolve() == Path(background_manifest).resolve():
        raise ValueError("Need two independent capture sessions, not the same manifest")

    files = [Path(foreground_manifest), Path(background_manifest)]
    reports = [
        verify_phase_session(m, rom_path, allow_synthetic_rom=allow_synthetic_rom)
        for m in files
    ]
    for report in reports:
        if report["capture_tool"] != "spritemine-mesence-render-capture-v1":
            raise ValueError("Both captures must be rendered RGB sessions")
        if report["mapper_model_status"] != "matches_known_boundaries":
            raise ValueError("Both PPU mappings must independently pass ROM verification")
    normal, background = reports
    if normal["rom_sha256"] != background["rom_sha256"]:
        raise ValueError("Different source ROM identities")
    for index in (2, 3):
        a, b = normal["snapshots"][index], background["snapshots"][index]
        for field in ("event", "frame_count", "master_clock", "ppu_scanline", "ppu_cycle"):
            if a[field] != b[field]:
                raise ValueError(f"Two sessions are not frame/clock-aligned at {field}")
        for part in ("oam", "palette", "ppu_pattern"):
            if a["sha256"][part] != b["sha256"][part]:
                raise ValueError(f"Captured {part} differs between render sessions")
    start = normal["snapshots"][2]
    if start["sprite_height"] != 16:
        raise ValueError("Only 8x16 SMB3 sprite components currently supported")
    a_end, b_end = normal["snapshots"][3], background["snapshots"][3]
    if (
        a_end["screen_width"] != 256 or a_end["screen_height"] != 240
        or b_end["screen_width"] != 256 or b_end["screen_height"] != 240
    ):
        raise ValueError("Both captures must use unfiltered native 256x240 RGB")

    manifests = [json.loads(m.read_text(encoding="utf-8")) for m in files]
    folder = files[0].parent
    parts = manifests[0]["phase_captures"][2]["files"]
    oam = (folder / parts["oam"]).read_bytes()
    ppu = (folder / parts["ppu_pattern"]).read_bytes()
    palette = (folder / parts["palette"]).read_bytes()
    rom_banks = start["model"]["source_rom_offsets_per_ppu_slot"]
    components = [
        decode_component(oam, ppu, palette, i, physical_rom_offsets=rom_banks)
        for i in oam_indices
    ]
    if any(c.behind_background for c in components):
        raise ValueError("Behind-background sprite priority needs a separate model")

    layer = index_layer(components)
    bounds = (
        min(c.x for c in components),
        min(c.y for c in components),
        max(c.x + 8 for c in components),
        max(c.y + 16 for c in components),
    )
    screens = []
    for i, manifest in enumerate(manifests):
        name = manifest["phase_captures"][3]["files"]["screen_rgb"]
        screens.append((files[i].parent / name).read_bytes())
    result = compare_region_with_bounds(
        screens[0], screens[1], 256, 240,
        layer, palette, bbox=bounds,
    )
    return {
        "schema_version": 1,
        "result": "conditional_background_reference_comparison",
        "foreground_session_id": normal["session_id"],
        "background_reference_session_id": background["session_id"],
        "verified_rom_sha256": normal["rom_sha256"],
        "frame_count": start["frame_count"],
        "frame_clock": start["master_clock"],
        "oam_indices": sorted(oam_indices),
        "matched_source_ppu_oam_palette_and_frame_clock": True,
        "foreground_rgb_sha256": a_end["sha256"]["screen_rgb"],
        "background_reference_rgb_sha256": b_end["sha256"]["screen_rgb"],
        "comparison": result,
        "not_proven": [
            "The saved capture does not record emulator GUI Disable Sprites toggle",
            "Same frame/clock/PPU/OAM/palette checks and a ring do not prove full nametable/scroll state",
            "Sprite priority, scanline sprite limit, and all other poses are not validated",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare one sprite-enabled capture to a replayed sprites-disabled reference"
    )
    parser.add_argument("foreground_manifest", type=Path)
    parser.add_argument("background_manifest", type=Path)
    parser.add_argument("--rom", type=Path, required=True, help="Verified SMB3 PRG1 ROM")
    parser.add_argument("--group-oam", default="10,11")
    args = parser.parse_args(argv)
    try:
        indices = tuple(int(s.strip()) for s in args.group_oam.split(","))
        report = analyze_two_renders(
            args.foreground_manifest, args.background_manifest, args.rom,
            oam_indices=indices,
        )
    except (OSError, ValueError, IndexError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"SpriteMine background verification unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["comparison"]["status"] == (
        "region_exact_conditional_on_sprites_disabled_reference"
    ) else 3


if __name__ == "__main__":
    raise SystemExit(main())
