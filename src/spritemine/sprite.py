"""Indexed 8x16 sprite rendering from an explicitly supplied MMC3 state."""

from dataclasses import dataclass

from .chr import tile_pixels


def mmc3_pages(registers: tuple[int, ...], inverted: bool) -> tuple[int, ...]:
    """Return physical 1 KiB CHR pages for PPU windows 0 through 7."""
    if len(registers) != 6 or any(not 0 <= bank <= 255 for bank in registers):
        raise ValueError("Expected six MMC3 CHR register bytes")
    r0, r1, *single = registers
    pairs = (r0 & 126, (r0 & 126) + 1, r1 & 126, (r1 & 126) + 1)
    small = tuple(bank & 127 for bank in single)
    return small + pairs if inverted else pairs + small


def sprite_tiles(pattern: int, pages: tuple[int, ...]) -> tuple[int, int]:
    """Resolve the two global CHR tile indices in top-to-bottom order."""
    if not 0 <= pattern <= 255 or len(pages) != 8 or any(not 0 <= p < 128 for p in pages):
        raise ValueError("Expected an OAM tile byte and eight SMB3 CHR pages")
    address = (pattern & 1) * 4096 + (pattern & 254) * 16
    top = pages[address // 1024] * 64 + address % 1024 // 16
    return top, top + 1


def sprite_pixels(rom, pattern: int, pages: tuple[int, ...], attributes: int = 0) -> bytes:
    """Return 128 row-major pattern values with whole-sprite flips applied."""
    top, bottom = sprite_tiles(pattern, pages)
    pixels = tile_pixels(rom, top) + tile_pixels(rom, bottom)
    rows = [pixels[i:i + 8] for i in range(0, 128, 8)]
    if attributes & 128:
        rows.reverse()
    if attributes & 64:
        rows = [row[::-1] for row in rows]
    return b"".join(rows)


@dataclass(frozen=True)
class ScanlineSprites:
    background_wins: bytes
    sprite_palette_offsets: bytes
    winning_oam_slots: tuple[int | None, ...]


def compose_scanline(
    rom, oam: bytes, pages: tuple[int, ...], y: int, background: bytes, *,
    sprites_enabled: bool = True, sprites_left_enabled: bool = True,
    background_enabled: bool = True, background_left_enabled: bool = True,
) -> ScanlineSprites:
    """Resolve a visible scanline given fetch-time OAM, CHR pages and BG values.

    Palette offsets are in the $3F10 sprite palette range. Zero denotes no
    visible sprite. Winning slots are recorded even when background wins.
    """
    if len(oam) != 256 or not 0 <= y < 240 or len(background) != 256:
        raise ValueError("Expected 256 OAM bytes, visible Y and 256 background values")
    if any(value > 3 for value in background):
        raise ValueError("Background pattern values must be in 0..3")
    winners: list[int | None] = [None] * 256
    palette = bytearray(256)
    bg_wins = bytearray(
        bool(value and background_enabled and (x >= 8 or background_left_enabled))
        for x, value in enumerate(background)
    )
    selected = 0
    if sprites_enabled:
        for slot in range(64):
            stored_y, pattern, attrs, left = oam[4 * slot:4 * slot + 4]
            row = y - stored_y - 1
            if not 0 <= row < 16:
                continue
            selected += 1
            if selected > 8:
                break
            pixels = sprite_pixels(rom, pattern, pages, attrs)
            for x in range(max(left, 0 if sprites_left_enabled else 8), min(256, left + 8)):
                value = pixels[row * 8 + x - left]
                if value and winners[x] is None:
                    winners[x] = slot
                    if not (attrs & 32 and bg_wins[x]):
                        bg_wins[x] = 0
                        palette[x] = (attrs & 3) * 4 + value
    return ScanlineSprites(bytes(bg_wins), bytes(palette), tuple(winners))
