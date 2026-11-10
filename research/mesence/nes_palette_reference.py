"""Narrow upstream MesenCE default 2C02 palette reference for SMB3 research.

Only three documented small-Mario colors are supported; other palette codes
raise explicit errors rather than silently assuming arbitrary RGB values.

Derived as factual color values from MesenCE Core/NES/NesDefaultVideoFilter.cpp,
source revision 4b8a196e299b3de297b204fd1208d2981562c89b.
No emulator palette table or implementation code is copied.

These colors apply only to the default 2C02 palette with no custom palette,
grayscale/emphasis, color adjustments, or spatial video filter.
"""

from __future__ import annotations

MESEN_REFERENCE_URL = (
    "https://github.com/nesdev-org/MesenCE/blob/"
    "4b8a196e299b3de297b204fd1208d2981562c89b/"
    "Core/NES/NesDefaultVideoFilter.cpp"
)

MESEN_2C02_DEFAULT_MARIO_REFERENCE = {
    0x0F: bytes.fromhex("000000"),
    0x16: bytes.fromhex("B53120"),
    0x36: bytes.fromhex("FECCC5"),
}


def sprite_rgba_from_default_reference(
    palette_ram: bytes, sprite_palette_slot: int, pixel_index: int
) -> tuple[int, int, int, int]:
    """Map 2bpp sprite index to default MesenCE color with alpha.

    For index zero, transparency takes precedence over palette universal
    background entries. Out-of-scope codes raise rather than invent colors.
    """
    if len(palette_ram) != 32:
        raise ValueError("NES palette RAM must have 32 bytes")
    if not 0 <= sprite_palette_slot <= 3:
        raise ValueError("NES sprite palette slot must be 0 through 3")
    if not 0 <= pixel_index <= 3:
        raise ValueError("2bpp pixel index must be 0 through 3")
    if pixel_index == 0:
        return (0, 0, 0, 0)
    code = palette_ram[0x10 + sprite_palette_slot * 4 + pixel_index] & 0x3F
    rgb = MESEN_2C02_DEFAULT_MARIO_REFERENCE.get(code)
    if rgb is None:
        raise ValueError(
            f"NES color code 0x{code:02X} unsupported by the narrow "
            "MesenCE default SMB3 reference palette"
        )
    return (*rgb, 255)
