"""Static 2bpp CHR-ROM tiles and provenance-preserving PNG export.

Grayscale pixels are synthetic visualizations, not authentic game palettes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from .rom import CHR_BANK_BYTES, Rom, RomFormatError

TILE_BYTES = 16
TILES_PER_BANK = CHR_BANK_BYTES // TILE_BYTES
ATLAS_COLUMNS = 16
ATLAS_ROWS = TILES_PER_BANK // ATLAS_COLUMNS
GRAYSCALE = (0, 85, 170, 255)


def decode_tile(tile: bytes) -> bytes:
    """Return 64 row-major palette indices (0..3), not RGB colors."""
    if len(tile) != TILE_BYTES:
        raise ValueError("A 2bpp NES tile must have exactly 16 bytes")
    pixels = bytearray(64)
    for y in range(8):
        for x in range(8):
            bit = 7 - x
            pixels[y * 8 + x] = ((tile[y] >> bit) & 1) | (((tile[y + 8] >> bit) & 1) << 1)
    return bytes(pixels)


def tile_pixels(rom: Rom, tile_index: int) -> bytes:
    if not rom.chr:
        raise RomFormatError("CHR-RAM cartridge: no static CHR-ROM tiles to export")
    count = len(rom.chr) // TILE_BYTES
    if not 0 <= tile_index < count:
        raise IndexError(f"Tile index {tile_index} outside 0..{count - 1}")
    start = tile_index * TILE_BYTES
    return decode_tile(rom.chr[start:start + TILE_BYTES])


def tile_image(pixels: bytes) -> Image.Image:
    if len(pixels) != 64 or any(index > 3 for index in pixels):
        raise ValueError("Expected 64 NES palette indices (0..3)")
    return Image.frombytes("L", (8, 8), bytes(GRAYSCALE[p] for p in pixels))


def bank_image(rom: Rom, bank_index: int) -> Image.Image:
    if not rom.chr:
        raise RomFormatError("CHR-RAM cartridge: no static CHR-ROM bank atlas")
    count = len(rom.chr) // CHR_BANK_BYTES
    if not 0 <= bank_index < count:
        raise IndexError(f"CHR bank {bank_index} outside 0..{count - 1}")
    atlas = Image.new("L", (ATLAS_COLUMNS * 8, ATLAS_ROWS * 8))
    base = bank_index * TILES_PER_BANK
    for local_index in range(TILES_PER_BANK):
        tile = tile_image(tile_pixels(rom, base + local_index))
        x = (local_index % ATLAS_COLUMNS) * 8
        y = (local_index // ATLAS_COLUMNS) * 8
        atlas.paste(tile, (x, y))
    return atlas


def export_chr(
    rom: Rom, output_dir: str | Path, *, bank: int | None = None, tile: int | None = None
) -> Path:
    """Export selected bank(s) or tile with a deterministic source manifest.

    Outputs may be replaced on repeated runs; the input ROM is never changed.
    """
    if not rom.chr:
        raise RomFormatError("CHR-RAM ROM has no static CHR-ROM data")
    if bank is not None and tile is not None:
        raise ValueError("Choose either --bank or --tile")
    bank_count = len(rom.chr) // CHR_BANK_BYTES
    tiles_count = len(rom.chr) // TILE_BYTES
    if bank is not None and not 0 <= bank < bank_count:
        raise ValueError(f"Bank must be in 0..{bank_count - 1}")
    if tile is not None and not 0 <= tile < tiles_count:
        raise ValueError(f"Tile must be in 0..{tiles_count - 1}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, int | str]] = []
    if tile is not None:
        name = f"chr_tile_{tile:04d}.png"
        path = out / name
        tile_image(tile_pixels(rom, tile)).save(path)
        entries.append({
            "file": name, "tile_index": tile, "bank_index": tile // TILES_PER_BANK,
            "tile_in_bank": tile % TILES_PER_BANK,
            "chr_offset": tile * TILE_BYTES,
            "rom_offset": rom.metadata.chr_rom_offset + tile * TILE_BYTES,
            "source_bytes": TILE_BYTES, "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    else:
        banks = range(bank_count) if bank is None else [bank]
        for index in banks:
            name = f"chr_bank_{index:02d}.png"
            path = out / name
            bank_image(rom, index).save(path)
            entries.append({
                "file": name, "bank_index": index,
                "chr_offset": index * CHR_BANK_BYTES,
                "rom_offset": rom.metadata.chr_rom_offset + index * CHR_BANK_BYTES,
                "source_bytes": CHR_BANK_BYTES, "tile_count": TILES_PER_BANK,
                "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    manifest = {
        "schema_version": 1,
        "provenance_type": "raw",
        "decoder": "spritemine.chr:nes_2bpp_v1",
        "rom_sha256": rom.metadata.rom_sha256,
        "mapper": rom.metadata.mapper,
        "chr_rom_offset": rom.metadata.chr_rom_offset,
        "palette": "synthetic_grayscale_not_authentic_nes_palette",
        "entries": entries,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path
