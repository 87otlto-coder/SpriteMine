"""Read-only SMB3 PRG1 Plains logical tile -> PPU staging interpretation.

This is a deterministic *source/ROM-derived* model, not a claim that a
nametable/attribute/screenshot was observed on a particular emulator frame.
See docs/research/SMB3_BACKGROUND_PPU_RENDERING_SPELUNKING_20261118.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .chr import decode_tile
from .player import ROM_SHA256
from .rom import Rom

LOGICAL_ROWS = 27
LOGICAL_COLS_PER_SCREEN = 16
BONUS_SCREENS = 2
BONUS_BYTES = LOGICAL_ROWS * LOGICAL_COLS_PER_SCREEN * BONUS_SCREENS
PLAIN_LAYOUT_OFFSET = 0x1E010
PLAIN_LAYOUT_LENGTH = 4 * 256
PLAIN_LAYOUT_SHA256 = "c19dfefb08bfdebaa2be3bce01abc590865da46f804ccd36f4b9d96db1bf9362"


@dataclass(frozen=True, slots=True)
class PlainsQuadrants:
    """Four 256-byte tables in the original PRG15 order: UL, LL, UR, LR."""

    data: bytes

    def __post_init__(self) -> None:
        if len(self.data) != PLAIN_LAYOUT_LENGTH:
            raise ValueError("Plains layout must hold exactly four 256-entry tables")

    def patterns(self, logical_tile: int) -> tuple[int, int, int, int]:
        if not 0 <= logical_tile <= 255:
            raise ValueError("Logical tile ID must be one byte")
        return tuple(self.data[256 * i + logical_tile] for i in range(4))


def plains_quadrants(rom: Rom) -> PlainsQuadrants:
    """Load verified Plains table bytes from the exact accepted SMB3 PRG1 ROM."""
    if rom.metadata.rom_sha256 != ROM_SHA256:
        raise ValueError("Plains quadrant decoder requires verified SMB3 USA PRG1")
    data = rom.image[PLAIN_LAYOUT_OFFSET:PLAIN_LAYOUT_OFFSET + PLAIN_LAYOUT_LENGTH]
    if sha256(data).hexdigest() != PLAIN_LAYOUT_SHA256:
        raise ValueError("Unexpected PRG1 Plains tile-layout fingerprint")
    return PlainsQuadrants(data)


def _bonus_tile(tiles: bytes, col: int, row: int) -> int:
    if len(tiles) != BONUS_BYTES:
        raise ValueError("Expected the verified two-screen 864-byte bonus logical map")
    if not 0 <= col < BONUS_SCREENS * LOGICAL_COLS_PER_SCREEN:
        raise ValueError("Bonus logical column outside 0..31")
    if not 0 <= row < LOGICAL_ROWS:
        raise ValueError("Bonus logical row outside 0..26")
    screen, local_col = divmod(col, LOGICAL_COLS_PER_SCREEN)
    return tiles[screen * LOGICAL_COLS_PER_SCREEN * LOGICAL_ROWS
                 + row * LOGICAL_COLS_PER_SCREEN + local_col]


def logical_palette_group(tile_id: int) -> int:
    """The palette pair selector comes from the logical ID, NOT its CHR."""
    if not 0 <= tile_id <= 255:
        raise ValueError("Logical tile ID must be one byte")
    return tile_id >> 6


def pattern_strip(tiles: bytes, layout: PlainsQuadrants, col: int, half: int) -> bytes:
    """54 8x8 patterns for one 8-pixel column, in game staging order.

    `half=0` selects quadrant tables UL/LL; `half=1` selects UR/LR.
    Not a 256x240 visible-frame snapshot: 30+24 rows are staged separately.
    """
    if half not in (0, 1):
        raise ValueError("Expected 0 (left) or 1 (right) 8-pixel half")
    out = bytearray()
    for row in range(LOGICAL_ROWS):
        quadrants = layout.patterns(_bonus_tile(tiles, col, row))
        out.extend(quadrants[2 * half:2 * half + 2])
    return bytes(out)


def _packed_attribute(tl: int, tr: int, bl: int, br: int) -> int:
    return (tl | (tr << 2) | (bl << 4) | (br << 6))


def attribute_strip(tiles: bytes, left_col: int) -> bytes:
    """14 PPU attributes for a pair of 16-pixel columns in World 1-1.

    PRG030 creates eight entries for first nametable and six for second.
    Entry 7 (logical rows 14/15) masks off the *lower* half because
    row 15 belongs to the second nametable's first attribute quartet.
    Source logic then restarts at row 15: entries 8..13 cover rows 15..26.
    """
    if not 0 <= left_col <= 30 or left_col & 1:
        raise ValueError("Expected even left logical column 0..30")
    rows = tuple(range(0, 15, 2)) + tuple(range(15, 26, 2))
    if len(rows) != 14:
        raise AssertionError("Wrong PRG030 attribute split")
    out = bytearray()
    for i, row in enumerate(rows):
        tl = logical_palette_group(_bonus_tile(tiles, left_col, row))
        tr = logical_palette_group(_bonus_tile(tiles, left_col + 1, row))
        bl = logical_palette_group(_bonus_tile(tiles, left_col, row + 1))
        br = logical_palette_group(_bonus_tile(tiles, left_col + 1, row + 1))
        attr = _packed_attribute(tl, tr, bl, br)
        out.append(attr & 0x0F if i == 7 else attr)
    return bytes(out)


def pattern_write_addresses(ppu_column: int) -> tuple[int, ...]:
    """Source PPU write targets for a staged 54-byte vertical pattern strip.

    CPU/NMI code selects vertical PPU increments: first 30 entries at $20xx,
    the remaining 24 at $28xx. Physical CIRAM mirroring is separate.
    """
    if not 0 <= ppu_column < 32:
        raise ValueError("PPU 8-pixel column outside 0..31")
    return (tuple(0x2000 + 32 * row + ppu_column for row in range(30))
            + tuple(0x2800 + 32 * row + ppu_column for row in range(24)))


def attribute_write_addresses(ppu_attribute_col: int) -> tuple[int, ...]:
    """Source 14-byte attribute writes, first 8 $23C0 rows then 6 $2BC0."""
    if not 0 <= ppu_attribute_col < 8:
        raise ValueError("PPU attribute column outside 0..7")
    return (tuple(0x23C0 + 8 * row + ppu_attribute_col for row in range(8))
            + tuple(0x2BC0 + 8 * row + ppu_attribute_col for row in range(6)))


def ciram_offset(ppu_address: int, *, mirroring: str) -> int:
    """Resolve PPU nametable address to physical 2-KiB CIRAM offset.

    MMC3 $A000 bit 0 = 1 gives conventional horizontal (A A / B B).
    This represents PPU $2000-$2FFF only, not the PPU palette area.
    """
    if not 0x2000 <= ppu_address < 0x3000:
        raise ValueError("Expected $2000-$2FFF PPU nametable address")
    if mirroring not in ("horizontal", "vertical"):
        raise ValueError("Expected horizontal or vertical CIRAM mirroring")
    relative = ppu_address - 0x2000
    table, within = divmod(relative, 1024)
    physical = table // 2 if mirroring == "horizontal" else table % 2
    return physical * 1024 + within


def background_pattern_pixels(rom: Rom, pattern: int, pages: tuple[int, ...]) -> bytes:
    """Decode a mapped PPU $0000-$0FFF background tile (64 *indexed* values).

    `pages` must describe all eight 1-KiB physical CHR pages at the PPU
    *fetch time*, not post-IRQ registers. The second BG 2-KiB window rotates.
    """
    if not 0 <= pattern <= 255 or len(pages) != 8:
        raise ValueError("Expected 8-bit background pattern and eight PPU pages")
    total_pages = len(rom.chr) // 1024
    if any(not isinstance(page, int) or not 0 <= page < total_pages for page in pages):
        raise ValueError("PPU CHR mapping has invalid physical 1-KiB page")
    address = pattern * 16
    physical = pages[address // 1024] * 1024 + address % 1024
    return decode_tile(rom.chr[physical:physical + 16])


def logical_tile_pixels(
    rom: Rom, layout: PlainsQuadrants, tile_id: int, pages: tuple[int, ...]
) -> tuple[bytes, int]:
    """Return 16x16 BG indexed pattern values and separate palette group.

    Background pattern value 0 is a PPU backdrop-selector, NOT sprite alpha.
    This function does not apply scrolling, palette RAM, PPUMASK, or RGB LUTs.
    """
    ul, ll, ur, lr = (background_pattern_pixels(rom, pat, pages)
                      for pat in layout.patterns(tile_id))
    out = bytearray()
    for y in range(8):
        out.extend(ul[y * 8:y * 8 + 8])
        out.extend(ur[y * 8:y * 8 + 8])
    for y in range(8):
        out.extend(ll[y * 8:y * 8 + 8])
        out.extend(lr[y * 8:y * 8 + 8])
    return bytes(out), logical_palette_group(tile_id)


def bonus_background_summary(rom: Rom, tiles: bytes, col: int, half: int) -> dict:
    """Private-safe fingerprints of a deterministic first-generation PPU strip."""
    layout = plains_quadrants(rom)
    patterns = pattern_strip(tiles, layout, col, half)
    attributes = attribute_strip(tiles, col & ~1)
    ppu_col = (col % LOGICAL_COLS_PER_SCREEN) * 2 + half
    return {
        "decoder": "spritemine.background.plains/1",
        "area": "world-1-1-bonus",
        "evidence": "rom_and_native_logical_map_source_model",
        "native_pattern_attribute_verified": False,
        "rom_sha256": rom.metadata.rom_sha256,
        "layout_table_rom_offset": PLAIN_LAYOUT_OFFSET,
        "layout_table_sha256": PLAIN_LAYOUT_SHA256,
        "logical_column": col,
        "half": half,
        "pattern_strip_length": len(patterns),
        "pattern_strip_sha256": sha256(patterns).hexdigest(),
        "attribute_left_column": col & ~1,
        "attribute_strip_length": len(attributes),
        "attribute_strip_sha256": sha256(attributes).hexdigest(),
        "pattern_ppu_targets": {
            "first": hex(pattern_write_addresses(ppu_col)[0]),
            "last": hex(pattern_write_addresses(ppu_col)[-1]),
        },
        "attribute_ppu_targets": {
            "first": hex(attribute_write_addresses((col % 16) // 2)[0]),
            "last": hex(attribute_write_addresses((col % 16) // 2)[-1]),
        },
    }


def compare_background_staging(
    expected_patterns: bytes,
    expected_attributes: bytes,
    observed_patterns: bytes,
    observed_attributes: bytes,
) -> dict:
    """Compare private captured game staging buffers without assuming their origin.

    A matching snapshot does not independently prove the buffer was captured
    after the corresponding producer routine or before its PPU commit.
    """
    if len(expected_patterns) != 54 or len(observed_patterns) != 54:
        raise ValueError("Pattern staging buffers must contain exactly 54 bytes")
    if len(expected_attributes) != 14 or len(observed_attributes) != 14:
        raise ValueError("Attribute staging buffers must contain exactly 14 bytes")

    def comparison(expected: bytes, observed: bytes) -> dict:
        differences = [index for index, (a, b) in enumerate(zip(expected, observed))
                       if a != b]
        return {
            "matches": not differences,
            "length": len(expected),
            "expected_sha256": sha256(expected).hexdigest(),
            "observed_sha256": sha256(observed).hexdigest(),
            "mismatch_count": len(differences),
            "first_difference": differences[0] if differences else None,
            "differences": [
                {"index": i, "expected": expected[i], "observed": observed[i]}
                for i in differences
            ],
        }

    patterns = comparison(expected_patterns, observed_patterns)
    attributes = comparison(expected_attributes, observed_attributes)
    return {
        "matches": patterns["matches"] and attributes["matches"],
        "capture_provenance_verified": False,
        "patterns": patterns,
        "attributes": attributes,
    }
