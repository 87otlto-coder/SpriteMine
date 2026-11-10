"""Inspect captured NES 8x16 OAM *hardware components*, not characters.

Uses the 8 KiB captured PPU address space at a verified startFrame boundary.
Transparent pixel index 0 is never converted into an opaque background. Sprite
palette slots, flips, priority and source ROM offsets are preserved as metadata.

This does not emulate sprite evaluation, the eight-sprites-per-scanline limit,
background priority, clipping or the final visible frame. RGB previews use
explicitly synthetic grayscale, not the NES/MesenCE output palette.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from spritemine.chr import decode_tile

try:
    from .verify_phase_capture import verify_phase_session
except ImportError:
    from verify_phase_capture import verify_phase_session


DIAGNOSTIC_COLORS = (
    (0, 0, 0, 0),
    (85, 85, 85, 255),
    (170, 170, 170, 255),
    (255, 255, 255, 255),
)


@dataclass(frozen=True)
class SpriteComponent:
    """One OAM hardware component and its 8x16 decoded palette index pixels."""

    oam_index: int
    x: int
    y: int
    tile_id: int
    attributes: int
    sprite_palette_slot: int
    sprite_palette_ram_bytes: tuple[int, int, int]
    behind_background: bool
    flip_horizontal: bool
    flip_vertical: bool
    ppu_tile_addresses: tuple[int, int]
    source_rom_tile_offsets: tuple[int, int] | None
    pixels: bytes

    def metadata(self) -> dict[str, Any]:
        return {
            "evidence": "captured_hardware_sprite_component_not_character",
            "oam_index": self.oam_index, "x": self.x, "y": self.y,
            "width": 8, "height": 16, "tile_id": self.tile_id,
            "attributes": self.attributes,
            "sprite_palette_slot": self.sprite_palette_slot,
            "sprite_palette_ram_bytes_for_indices_1_to_3": list(
                self.sprite_palette_ram_bytes
            ),
            "behind_background": self.behind_background,
            "flip_horizontal": self.flip_horizontal,
            "flip_vertical": self.flip_vertical,
            "ppu_tile_addresses": list(self.ppu_tile_addresses),
            "source_rom_tile_offsets": (
                list(self.source_rom_tile_offsets)
                if self.source_rom_tile_offsets is not None else None
            ),
            "palette_index_pixel_counts": [
                self.pixels.count(index) for index in range(4)
            ],
        }


def decode_component(
    oam: bytes, ppu: bytes, palette_ram: bytes, index: int,
    *, physical_rom_offsets: list[int] | None = None,
) -> SpriteComponent:
    """Decode one NES 8x16 sprite using the tile-id bit-0 table select rule.

    physical_rom_offsets: known absolute source-ROM base offsets for the eight
    1 KiB PPU slots. If unknown, no offsets are guessed.
    """
    if len(oam) != 256 or len(ppu) != 8192 or len(palette_ram) != 32:
        raise ValueError("Expected 256 OAM, 8192 mapped PPU, and 32 palette bytes")
    if not 0 <= index < 64:
        raise IndexError("OAM index must be in 0..63")
    if physical_rom_offsets is not None and (
        len(physical_rom_offsets) != 8
        or any(type(v) is not int or v < 0 for v in physical_rom_offsets)
    ):
        raise ValueError("Expected eight nonnegative absolute source-ROM offsets")

    y_raw, tile, attrs, x = oam[index * 4:index * 4 + 4]
    # For 8x16, tile LSB chooses $0000/$1000 pattern table, while the other
    # seven bits choose the even-aligned top tile and the immediately next tile.
    top = (0x1000 if tile & 1 else 0) + ((tile & 0xFE) * 16)
    bottom = top + 16
    if bottom + 16 > len(ppu):
        raise ValueError("Tile address unexpectedly outside PPU pattern range")

    top_indices = decode_tile(ppu[top:top + 16])
    bottom_indices = decode_tile(ppu[bottom:bottom + 16])
    pixels = top_indices + bottom_indices  # 16 rows of eight indices
    horizontal, vertical = bool(attrs & 0x40), bool(attrs & 0x80)
    rows = [pixels[row * 8:(row + 1) * 8] for row in range(16)]
    if vertical:
        rows.reverse()
    if horizontal:
        rows = [row[::-1] for row in rows]
    pixels = b"".join(rows)

    slot = attrs & 3
    palette_address = 0x10 + slot * 4
    colors = tuple(palette_ram[palette_address + i] for i in (1, 2, 3))
    offsets = None
    if physical_rom_offsets is not None:
        offsets = tuple(
            physical_rom_offsets[addr // 1024] + (addr % 1024)
            for addr in (top, bottom)
        )
    return SpriteComponent(
        oam_index=index, x=x, y=y_raw + 1, tile_id=tile,
        attributes=attrs, sprite_palette_slot=slot,
        sprite_palette_ram_bytes=colors,
        behind_background=bool(attrs & 0x20),
        flip_horizontal=horizontal, flip_vertical=vertical,
        ppu_tile_addresses=(top, bottom),
        source_rom_tile_offsets=offsets,
        pixels=pixels,
    )


def collect_components(
    oam: bytes, ppu: bytes, palette_ram: bytes,
    *, physical_rom_offsets: list[int] | None = None,
    potentially_on_screen_only: bool = True,
) -> list[SpriteComponent]:
    """Y-position test is only a candidate filter, not rendered visibility."""
    results = []
    for index in range(64):
        comp = decode_component(
            oam, ppu, palette_ram, index, physical_rom_offsets=physical_rom_offsets
        )
        if potentially_on_screen_only and comp.y >= 240:
            continue
        results.append(comp)
    return results


def preview_image(component: SpriteComponent) -> Image.Image:
    """Small 8x16 RGBA diagnostic; colors are never asserted authentic."""
    image = Image.new("RGBA", (8, 16))
    image.putdata([DIAGNOSTIC_COLORS[value] for value in component.pixels])
    return image


def inspect_session(
    manifest_path: Path, rom_path: Path, *,
    sample_number: int = 3,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Read one verified startFrame capture; optionally export local PNG previews."""
    verified = verify_phase_session(manifest_path, rom_path)
    if verified["mapper_model_status"] != "matches_known_boundaries":
        raise ValueError(
            "The ROM-backed captured PPU mapping was not independently validated"
        )
    if sample_number not in (1, 3):
        raise ValueError("Only startFrame samples 1 or 3 support this experiment")
    sample = verified["snapshots"][sample_number - 1]
    model = sample["model"]
    if model is None or not model["matches_full_8k_ppu"]:
        raise ValueError("Chosen startFrame lacks a verified physical ROM mapping")
    if sample["sprite_height"] != 16:
        raise ValueError("This research decoder currently supports 8x16 OAM only")

    raw_manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    names = raw_manifest["phase_captures"][sample_number - 1]["files"]
    folder = Path(manifest_path).parent
    oam = (folder / names["oam"]).read_bytes()
    ppu = (folder / names["ppu_pattern"]).read_bytes()
    palette = (folder / names["palette"]).read_bytes()
    components = collect_components(
        oam, ppu, palette,
        physical_rom_offsets=model["source_rom_offsets_per_ppu_slot"],
    )

    report: dict[str, Any] = {
        "schema_version": 1,
        "result": "captured_8x16_hardware_components_only",
        "session_id": verified["session_id"],
        "frame_count": sample["frame_count"],
        "event": sample["event"],
        "sample_number": sample_number,
        "rom_sha256": verified["rom_sha256"],
        "ppu_sha256": sample["sha256"]["ppu_pattern"],
        "oam_sha256": sample["sha256"]["oam"],
        "palette_sha256": sample["sha256"]["palette"],
        "mapping_verified_at_boundary": True,
        "palette": "synthetic_grayscale_rgba_index0_transparent_not_original_NES_RGB",
        "potentially_on_screen_count": len(components),
        "components": [component.metadata() for component in components],
        "not_proven": [
            "these hardware entries form complete characters or identify Mario",
            "these sprites were actually visible in final composited pixels",
            "correct hardware color RGB, priority, clipping, sprite scanline limits",
            "boundary mapping used by visible PPU sprite fetches on every scanline",
        ],
    }

    if output_dir is not None:
        target = Path(output_dir)
        if target.resolve() == folder.resolve():
            raise ValueError("Export to a separate FIXTURE output directory")
        target.mkdir(parents=True, exist_ok=True)
        exports = []
        for component in components:
            name = (
                f"hardware_oam_{component.oam_index:02d}"
                f"_frame_{sample['frame_count']}.png"
            )
            dest = target / name
            if dest.exists():
                raise FileExistsError(f"Refusing to overwrite existing preview: {dest}")
            preview_image(component).save(dest)
            exports.append({
                "file": name, "oam_index": component.oam_index,
                "png_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            })
        report["local_preview_exports"] = exports
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect local 8x16 SMB3 OAM hardware components; no character claims"
    )
    parser.add_argument("manifest", type=Path, help="Exact phase_*.json manifest")
    parser.add_argument("--rom", type=Path, required=True, help="Local verified SMB3 NES/ZIP")
    parser.add_argument("--sample", type=int, default=3, help="1-based startFrame sample; default 3")
    parser.add_argument("--output-dir", type=Path, help="Optional local FIXTURE preview output")
    args = parser.parse_args(argv)
    try:
        report = inspect_session(
            args.manifest, args.rom, sample_number=args.sample,
            output_dir=args.output_dir,
        )
    except (OSError, ValueError, KeyError, TypeError, IndexError, json.JSONDecodeError) as exc:
        print(f"Sprite component inspection failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
