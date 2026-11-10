"""Analyze captured RGB screen at endFrame against ROM-verified sprite indices.

This is a *diagnostic*, not an authoritative pixel-perfect renderer. RGB color
values are inferred from a rendered screen, not assumed from an NES palette.
The 256x240 screen geometry, PPU bank stability and frame-phase relationship
are checked explicitly. OAM/CHR visibility, priority and authenticity of the
video filter remain independent unverified questions.

No input graphics or ROM bytes are exported; JSON reports statistics only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from .sprite_components import decode_component
    from .verify_phase_capture import verify_phase_session
except ImportError:
    from sprite_components import decode_component
    from verify_phase_capture import verify_phase_session


def index_layer(components: list[Any]) -> dict[tuple[int, int], tuple[int, int]]:
    """Map candidate visible positions to (sprite palette slot, pixel index).

    Transparent pixel index 0 never overwrites anything. Lower OAM entries
    are given higher priority only *within this simple group*, without actual
    NES scanline evaluation, background pixel priority, or clipping behavior.
    """
    result: dict[tuple[int, int], tuple[int, int]] = {}
    for component in sorted(components, key=lambda c: c.oam_index, reverse=True):
        for y in range(16):
            for x in range(8):
                index = component.pixels[y * 8 + x]
                pos = (component.x + x, component.y + y)
                if index:
                    result[pos] = (component.sprite_palette_slot, index)
    return result


def compare_color_groups(
    rgb: bytes, width: int, height: int,
    indexed: dict[tuple[int, int], tuple[int, int]],
    *, dx: int = 0, dy: int = 0,
) -> dict[str, Any]:
    """Count how consistently each expected sprite palette index maps to RGB.

    The color lookup is fitted to the same screen pixels; therefore a high
    number alone does not independently prove source sprite pixel accuracy.
    """
    if len(rgb) != width * height * 3:
        raise ValueError("RGB24 screen buffer does not match its dimensions")
    groups: dict[tuple[int, int], Counter[bytes]] = {}
    out_of_bounds = 0
    for (x, y), source in indexed.items():
        px, py = x + dx, y + dy
        if not (0 <= px < width and 0 <= py < height):
            out_of_bounds += 1
            continue
        offset = (py * width + px) * 3
        groups.setdefault(source, Counter())[rgb[offset:offset + 3]] += 1

    per_class = []
    matched = total = 0
    for (palette_slot, index), counts in sorted(groups.items()):
        dominant_rgb, count = counts.most_common(1)[0]
        class_total = sum(counts.values())
        matched += count
        total += class_total
        per_class.append({
            "palette_slot": palette_slot,
            "palette_index": index,
            "sample_count": class_total,
            "inferred_modal_rgb": "#" + dominant_rgb.hex().upper(),
            "modal_count": count,
            "modal_fraction": round(count / class_total, 6),
            "distinct_rendered_rgb_values": len(counts),
        })
    return {
        "dx": dx, "dy": dy,
        "opaque_predicted_pixels": len(indexed),
        "pixels_sampled": total,
        "out_of_bounds": out_of_bounds,
        "modal_agreement_pixels": matched,
        "modal_agreement_fraction": round(matched / total, 6) if total else None,
        "inferred_color_classes": per_class,
    }



# Only the *three* default MesenCE 2C02 codes observed in the existing SMB3
# small-Mario experiment. Do not copy the full GPLv3 emulator palette table.
# Source: MesenCE Core/NES/NesDefaultVideoFilter.cpp, revision:
# 4b8a196e299b3de297b204fd1208d2981562c89b
# These are reference RGBs for unmodified default color settings only.
MESEN_2C02_DEFAULT_MARIO_REFERENCE = {
    0x0F: bytes.fromhex("000000"),
    0x16: bytes.fromhex("B53120"),
    0x36: bytes.fromhex("FECCC5"),
}
MESEN_REFERENCE_URL = (
    "https://github.com/nesdev-org/MesenCE/blob/"
    "4b8a196e299b3de297b204fd1208d2981562c89b/"
    "Core/NES/NesDefaultVideoFilter.cpp"
)


def compare_independent_reference_palette(
    rgb: bytes, width: int, height: int,
    indexed: dict[tuple[int, int], tuple[int, int]],
    palette_ram: bytes,
) -> dict[str, Any]:
    """Compare pixels to fixed upstream default palette, never fitted RGB.

    This comparison does not independently prove background transparency,
    mapper fetch phase, or emulator color configuration. Codes outside the
    three previously researched SMB3 colors are explicitly unsupported.
    """
    if len(rgb) != width * height * 3:
        raise ValueError("RGB24 buffer does not match screen dimensions")
    if len(palette_ram) != 32:
        raise ValueError("NES palette RAM must be exactly 32 bytes")

    classes = sorted(set(indexed.values()))
    looked_up = []
    unknown = []
    for slot, index in classes:
        if not 0 <= slot <= 3 or not 1 <= index <= 3:
            raise ValueError("Invalid sprite palette slot/index")
        address = 0x10 + slot * 4 + index
        code = palette_ram[address] & 0x3F
        entry = {
            "sprite_palette_slot": slot,
            "pixel_index": index,
            "palette_ram_offset": address,
            "nes_color_code": f"0x{code:02X}",
            "reference_rgb": (
                "#" + MESEN_2C02_DEFAULT_MARIO_REFERENCE[code].hex().upper()
                if code in MESEN_2C02_DEFAULT_MARIO_REFERENCE else None
            ),
        }
        looked_up.append(entry)
        if code not in MESEN_2C02_DEFAULT_MARIO_REFERENCE:
            unknown.append(f"0x{code:02X}")

    result: dict[str, Any] = {
        "reference": "MesenCE 2C02 default palette, 3 researched SMB3 codes only",
        "source_url": MESEN_REFERENCE_URL,
        "assumptions": [
            "PPU model 2C02; default palette with no custom/user colors",
            "no grayscale, color-emphasis or video hue/brightness/contrast changes",
            "256x240 native-size video with no spatial or blending filter",
            "OAM entry visibility, clipping and background priority not emulated",
        ],
        "sprite_palette_entries": looked_up,
        "unrecognized_codes": sorted(set(unknown)),
        "pixels_expected": len(indexed),
        "pixels_compared": 0,
        "pixels_exact": 0,
        "pixels_mismatched": 0,
        "pixels_out_of_bounds": 0,
        "exact_fraction": None,
        "sample_mismatch_positions": [],
        "status": None,
    }
    if unknown:
        result["status"] = "unsupported_palette_codes_for_restricted_reference"
        return result

    by_class = {
        (entry["sprite_palette_slot"], entry["pixel_index"]):
        MESEN_2C02_DEFAULT_MARIO_REFERENCE[int(entry["nes_color_code"], 16)]
        for entry in looked_up
    }
    for (x, y), group in indexed.items():
        if not (0 <= x < width and 0 <= y < height):
            result["pixels_out_of_bounds"] += 1
            continue
        offset = (y * width + x) * 3
        result["pixels_compared"] += 1
        if rgb[offset:offset + 3] == by_class[group]:
            result["pixels_exact"] += 1
        else:
            result["pixels_mismatched"] += 1
            if len(result["sample_mismatch_positions"]) < 8:
                result["sample_mismatch_positions"].append({"x": x, "y": y})
    if result["pixels_compared"]:
        result["exact_fraction"] = round(
            result["pixels_exact"] / result["pixels_compared"], 6
        )
    result["status"] = (
        "reference_opaque_pixels_exact"
        if result["pixels_exact"] == result["pixels_expected"]
        and result["pixels_out_of_bounds"] == 0
        else "reference_opaque_pixels_mismatch"
    )
    return result


def _early_chr_changes(manifest: dict[str, Any], start: dict[str, Any],
                       end: dict[str, Any], max_sprite_y: int) -> list[dict[str, int]]:
    """Flag pre-write CHR register updates in the sample's visible sprite span."""
    selected = None
    current_chr_mode = None
    changes = []
    for event in manifest["writes"]:
        clock, addr, value = event["master_clock"], event["address"], event["value"]
        if clock <= start["master_clock"]:
            if addr % 2 == 0:
                selected = value & 7
                current_chr_mode = value & 0x80
            continue
        if clock >= end["master_clock"]:
            break
        scanline = event["ppu_scanline"]
        if addr % 2 == 0:
            select_mode = value & 0x80
            if (current_chr_mode is not None and select_mode != current_chr_mode
                    and scanline < max_sprite_y):
                changes.append({"scanline": scanline, "cycle": event["ppu_cycle"],
                                "register": -1, "value": value})
            selected = value & 7
            current_chr_mode = select_mode
        elif selected is not None and selected <= 5 and scanline < max_sprite_y:
            changes.append({"scanline": scanline, "cycle": event["ppu_cycle"],
                            "register": selected, "value": value})
    return changes


def analyze_render_capture(
    manifest_path: Path,
    rom_path: Path,
    *,
    oam_indices: tuple[int, ...] = (10, 11),
    allow_synthetic_rom: bool = False,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    # Test-only override never exposed on the CLI; actual runs require SMB3 PRG1.
    verified = verify_phase_session(
        manifest_path, rom_path, allow_synthetic_rom=allow_synthetic_rom
    )
    if verified["capture_tool"] != "spritemine-mesence-render-capture-v1":
        raise ValueError("A rendered RGB capture is required, not a phase-only capture")
    if verified["mapper_model_status"] != "matches_known_boundaries":
        raise ValueError(
            "The ROM-backed PPU pattern mapping must pass before RGB comparison"
        )
    if not oam_indices or len(set(oam_indices)) != len(oam_indices):
        raise ValueError("Specify distinct OAM indices for an explicit group")
    if any(not 0 <= index < 64 for index in oam_indices):
        raise ValueError("OAM indices must be 0 through 63")
    source = json.loads(manifest_path.read_text(encoding="utf-8"))
    start, end = verified["snapshots"][2:4]
    if start["frame_count"] != end["frame_count"]:
        raise ValueError("Rendered screen does not share a frame identifier")
    mapping = start["model"]
    if mapping is None or not mapping["matches_full_8k_ppu"]:
        raise ValueError("Second pre-render CHR snapshot is not independently mapped")
    if start["sprite_height"] != 16:
        raise ValueError("This targeted diagnostic requires NES 8x16 sprite mode")
    files = source["phase_captures"][2]["files"]
    folder = manifest_path.parent
    oam = (folder / files["oam"]).read_bytes()
    ppu = (folder / files["ppu_pattern"]).read_bytes()
    palette = (folder / files["palette"]).read_bytes()
    comps = [
        decode_component(
            oam, ppu, palette, index,
            physical_rom_offsets=mapping["source_rom_offsets_per_ppu_slot"],
        )
        for index in oam_indices
    ]
    max_sprite_y = max(component.y + 16 for component in comps)
    events = _early_chr_changes(source, start, end, max_sprite_y)
    indexed = index_layer(comps)
    image_file = source["phase_captures"][3]["files"]["screen_rgb"]
    screen = (folder / image_file).read_bytes()
    width, height = end["screen_width"], end["screen_height"]
    if width is None or height is None:
        raise ValueError("Rendered RGB buffer geometry missing")

    result = {
        "schema_version": 1,
        "result": "rendered_screen_sprite_color_consistency_diagnostic",
        "session_id": verified["session_id"],
        "frame_count": start["frame_count"],
        "rom_sha256": verified["rom_sha256"],
        "start_ppu_sha256": start["sha256"]["ppu_pattern"],
        "start_oam_sha256": start["sha256"]["oam"],
        "start_palette_sha256": start["sha256"]["palette"],
        "rendered_rgb_sha256": end["sha256"]["screen_rgb"],
        "rendered_rgb_size": [width, height],
        "source": "MesenCE endFrame getScreenBuffer() after visible scanlines",
        "oam_indices": sorted(oam_indices),
        "sprite_positions": [
            {"oam_index": c.oam_index, "x": c.x, "y": c.y,
             "tile_id": c.tile_id, "palette_slot": c.sprite_palette_slot,
             "physical_rom_tile_offsets": list(c.source_rom_tile_offsets or ())}
            for c in comps
        ],
        "ppu_mapping_verified": True,
        "oam_unchanged_between_start_and_end": (
            start["sha256"]["oam"] == end["sha256"]["oam"]
        ),
        "palette_ram_unchanged_between_start_and_end": (
            start["sha256"]["palette"] == end["sha256"]["palette"]
        ),
        "chr_bank_changes_before_object_bottom": events,
        "geometry_supported": width == 256 and height == 240,
        "rgb_color_comparison": None,
        "independent_default_palette_check": None,
        "sprite_group_region": {
            "left": min(component.x for component in comps),
            "top": min(component.y for component in comps),
            "right_exclusive": max(component.x + 8 for component in comps),
            "bottom_exclusive": max(component.y + 16 for component in comps),
            "opaque_sprite_pixels": len(indexed),
            "transparent_background_pixels_not_verified": (
                (
                    max(component.x + 8 for component in comps)
                    - min(component.x for component in comps)
                ) * (
                    max(component.y + 16 for component in comps)
                    - min(component.y for component in comps)
                ) - len(indexed)
            ),
            "background_reference_status": (
                "unavailable_no_independent_background_or_sprite_disabled_capture"
            ),
        },
        "not_proven": [
            "legacy modal RGB statistics are fitted to the screen itself",
            "independent default 2C02 palette applies only if emulator options match",
            "NES sprite scanline limits, background priority, clipping and edge masking",
            "screen-frame/PPU sprite fetch timing independent of the event callback",
            "a recognized 16x16 shape is a complete or universally correct Mario pose",
        ],
    }
    if width == 256 and height == 240:
        result["independent_default_palette_check"] = compare_independent_reference_palette(
            screen, width, height, indexed, palette
        )
        result["rgb_color_comparison"] = {
            "registered_oam_coordinates": compare_color_groups(
                screen, width, height, indexed
            ),
            "neighbor_diagnostics_not_alignment_correction": [
                compare_color_groups(screen, width, height, indexed, dx=dx, dy=dy)
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
            ],
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare authentic MesenCE screen RGB with an explicit OAM group"
    )
    parser.add_argument("manifest", type=Path, help="render_*.json manifest")
    parser.add_argument("--rom", type=Path, required=True, help="Verified local SMB3 PRG1 ROM ZIP")
    parser.add_argument("--group-oam", default="10,11", help="Explicit OAM indices, e.g. 10,11")
    args = parser.parse_args(argv)
    try:
        indices = tuple(int(part.strip()) for part in args.group_oam.split(","))
        report = analyze_render_capture(args.manifest, args.rom, oam_indices=indices)
    except (OSError, ValueError, KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
        print(f"SpriteMine render comparison unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
