"""SMB3 PRG1 NES background reconstruction from original CHR and physical CIRAM.

The caller supplies observed MMC3 mapping, nametable RAM, scroll state, palette
RAM, and display profile explicitly. Nothing is inferred from screenshots.
This intentionally does not compose OAM sprites, the IRQ-driven HUD, or
mid-scanline changes. A validated 256x192 World 1-1 bonus viewport is the gate.
"""

from __future__ import annotations

import re

from .background import ciram_offset


class Mmc3ChrRegisters:
    """Replay mapper $8000/$8001 writes into eight physical 1-KiB PPU CHR pages."""

    def __init__(self) -> None:
        self.selection: int | None = None
        self.inverted: bool | None = None
        self.registers: list[int | None] = [None] * 8

    def write(self, address: int, value: int) -> None:
        if address not in (0x8000, 0x8001) or not 0 <= value <= 255:
            raise ValueError("Expected an MMC3 $8000/$8001 8-bit register write")
        if address == 0x8000:
            self.selection = value & 7
            self.inverted = bool(value & 0x80)
        else:
            if self.selection is None:
                raise ValueError("MMC3 bank write preceded the register selector")
            self.registers[self.selection] = value

    def pages(self) -> tuple[int, ...]:
        if self.inverted is None or any(self.registers[i] is None for i in range(6)):
            raise ValueError("Incomplete MMC3 CHR register history at fetch time")
        a, b, c, d, e, f = (int(self.registers[i]) for i in range(6))
        paired = (a & 0xFE, a | 1, b & 0xFE, b | 1)
        singles = (c, d, e, f)
        return singles + paired if self.inverted else paired + singles


def read_2c02_rgb_profile(mesen_source: str) -> bytes:
    """Parse 64 default 2C02 RGB values from a separately supplied MesenCE source.

    Source is a GPLv3 file held separately from the SpriteMine codebase;
    its color table is NOT vendored or distributed by this project.
    The parser does not execute the source or assume current video settings.
    """
    match = re.search(r"/\*\s*2C02\s*\*/\s*\{([^}]*)\}", mesen_source)
    if match is None:
        raise ValueError("MesenCE source has no explicit default 2C02 palette")
    tokens = re.findall(r"\b0x([0-9a-fA-F]{8})\b", match.group(1))
    if len(tokens) != 64:
        raise ValueError("Expected exactly 64 default 2C02 ARGB values")
    out = bytearray()
    for token in tokens:
        value = int(token, 16)
        if value >> 24 != 0xFF:
            raise ValueError("Unexpected default 2C02 color alpha")
        out.extend(((value >> 16) & 255, (value >> 8) & 255, value & 255))
    return bytes(out)


def render_background_codes(
    *,
    chr_rom: bytes,
    ciram: bytes,
    palette_ram: bytes,
    chr_pages: tuple[int, ...],
    mirroring_bit: int,
    scroll_t: int,
    fine_x: int,
    pattern_base: int,
    background_enabled: bool,
    left_edge_enabled: bool,
    width: int = 256,
    height: int = 192,
) -> bytes:
    """Return NES palette indices for an independently rendered gameplay viewport.

    PPU horizontal/vertical tile wrapping and the four attribute quadrants
    follow NESdev's PPU scrolling/nametable interpretation. The upper limit of
    192 rows deliberately excludes SMB3's separately IRQ-switched status bar.
    This model is valid only if fetch-time CHR and palette state are stable
    throughout the sampled viewport; the caller must establish that.
    """
    if len(chr_rom) == 0 or len(chr_rom) % 1024:
        raise ValueError("Expected whole 1-KiB pages of CHR ROM")
    if len(ciram) != 2048 or len(palette_ram) != 32:
        raise ValueError("Expected 2-KiB physical CIRAM and 32 palette bytes")
    if any(value > 63 for value in palette_ram):
        raise ValueError("NES palette RAM value outside 0..63")
    if len(chr_pages) != 8 or any(
        not isinstance(p, int) or not 0 <= p < len(chr_rom) // 1024 for p in chr_pages
    ):
        raise ValueError("Invalid fetch-time eight-page MMC3 CHR mapping")
    if mirroring_bit not in (0, 1):
        raise ValueError("Expected observed MMC3 mirroring bit 0 or 1")
    if not 0 <= scroll_t <= 0x7FFF or not 0 <= fine_x <= 7:
        raise ValueError("Invalid PPU temporary VRAM or fine X scroll")
    if (scroll_t >> 5) & 0x1F > 29:
        raise ValueError("Unmodeled PPU coarse-Y 30/31 scroll behavior")
    if pattern_base not in (0, 0x1000):
        raise ValueError("Expected 8x8 NES BG pattern table base")
    if not 0 < width <= 256 or not 0 < height <= 192:
        raise ValueError("This gate covers a bounded 256x192 gameplay viewport only")
    if not background_enabled:
        raise ValueError("Rendering-disabled frames are not accepted as background proof")

    mirror = "horizontal" if mirroring_bit else "vertical"
    start_x = (scroll_t & 31) * 8 + fine_x
    start_y = ((scroll_t >> 5) & 31) * 8 + ((scroll_t >> 12) & 7)
    base_nt = (scroll_t >> 10) & 3
    output = bytearray(width * height)
    for y in range(height):
        world_y = start_y + y
        nty = ((base_nt >> 1) + world_y // 240) & 1
        tile_y = (world_y % 240) // 8
        row_y = world_y % 8
        for x in range(width):
            offset = y * width + x
            if x < 8 and not left_edge_enabled:
                output[offset] = palette_ram[0]
                continue
            world_x = start_x + x
            ntx = ((base_nt & 1) + world_x // 256) & 1
            tile_x = (world_x % 256) // 8
            row_x = world_x % 8
            nametable = 0x2000 + 0x400 * (ntx + 2 * nty)
            tile_address = nametable + 32 * tile_y + tile_x
            attribute_address = nametable + 0x3C0 + 8 * (tile_y // 4) + tile_x // 4
            tile = ciram[ciram_offset(tile_address, mirroring=mirror)]
            attribute = ciram[ciram_offset(attribute_address, mirroring=mirror)]
            shift = 4 * ((tile_y >> 1) & 1) + 2 * ((tile_x >> 1) & 1)
            palette_group = (attribute >> shift) & 3

            pattern_address = pattern_base + tile * 16
            physical = chr_pages[pattern_address // 1024] * 1024
            physical += pattern_address % 1024 + row_y
            lo = chr_rom[physical]
            hi = chr_rom[physical + 8]
            color = ((lo >> (7 - row_x)) & 1) | (((hi >> (7 - row_x)) & 1) << 1)
            output[offset] = palette_ram[4 * palette_group + color] if color else palette_ram[0]
    return bytes(output)


def color_codes_to_rgb(codes: bytes, rgb_palette: bytes) -> bytes:
    """Map NES palette indices via an explicit 64-color RGB profile (192 bytes)."""
    if len(rgb_palette) != 64 * 3:
        raise ValueError("Expected a separately supplied 64-color RGB profile")
    if any(code >= 64 for code in codes):
        raise ValueError("NES color code outside 0..63")
    output = bytearray(len(codes) * 3)
    for i, code in enumerate(codes):
        output[3 * i:3 * i + 3] = rgb_palette[3 * code:3 * code + 3]
    return bytes(output)
