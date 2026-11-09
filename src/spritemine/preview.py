"""Pure, explicitly synthetic CHR preview rendering.

Raw CHR contains two-bit pixel indices, not NES palette assignments. All
presets below are visualization choices, not claimed original SMB3 colors.
"""

from __future__ import annotations

from PIL import Image

from .chr import ATLAS_COLUMNS, TILES_PER_BANK, tile_pixels
from .rom import Rom, RomFormatError

# Ordered presets: labels intentionally disclose their synthetic nature.
PALETTES: dict[str, tuple[str, tuple[tuple[int, int, int], ...]]] = {
    "grayscale": (
        "Grayscale (synthetic)",
        ((0, 0, 0), (85, 85, 85), (170, 170, 170), (255, 255, 255)),
    ),
    "green": (
        "Green-toned (synthetic)",
        ((11, 32, 21), (40, 94, 53), (112, 174, 102), (216, 247, 197)),
    ),
    "amber": (
        "Amber-toned (synthetic)",
        ((33, 22, 16), (103, 54, 26), (203, 123, 43), (252, 223, 149)),
    ),
}


def _colors(palette: str) -> tuple[tuple[int, int, int], ...]:
    try:
        return PALETTES[palette][1]
    except KeyError as exc:
        raise ValueError(f"Unknown synthetic palette: {palette}") from exc


def preview_tile(rom: Rom, tile_index: int, palette: str = "grayscale") -> Image.Image:
    """RGB preview of a tile; index 0 is intentionally opaque for raw CHR."""
    colors = _colors(palette)
    image = Image.new("RGB", (8, 8))
    image.putdata([colors[value] for value in tile_pixels(rom, tile_index)])
    return image


def preview_bank(rom: Rom, bank_index: int, palette: str = "grayscale") -> Image.Image:
    """RGB 16-column atlas; each bank has 512 8x8 tiles."""
    _colors(palette)
    if not rom.chr:
        raise RomFormatError("CHR-RAM ROM has no static CHR-ROM atlas")
    if not 0 <= bank_index < rom.metadata.chr_banks_8k:
        raise IndexError(f"CHR bank {bank_index} outside 0..{rom.metadata.chr_banks_8k - 1}")
    rows = TILES_PER_BANK // ATLAS_COLUMNS
    result = Image.new("RGB", (ATLAS_COLUMNS * 8, rows * 8))
    start = bank_index * TILES_PER_BANK
    for local in range(TILES_PER_BANK):
        result.paste(
            preview_tile(rom, start + local, palette),
            ((local % ATLAS_COLUMNS) * 8, (local // ATLAS_COLUMNS) * 8),
        )
    return result
