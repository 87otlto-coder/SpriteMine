"""Headless source-model tests; all except the opt-in private ROM test are synthetic."""

from hashlib import sha256
import os
from types import SimpleNamespace

import pytest

from spritemine.background import (
    BONUS_BYTES,
    PLAIN_LAYOUT_SHA256,
    PlainsQuadrants,
    attribute_strip,
    attribute_write_addresses,
    background_pattern_pixels,
    bonus_background_summary,
    ciram_offset,
    compare_background_staging,
    logical_palette_group,
    logical_tile_pixels,
    pattern_strip,
    pattern_write_addresses,
    plains_quadrants,
)
from spritemine.rom import load_rom
from spritemine.world1_1 import MODEL_SHA256, reconstruct_bonus


def _tiles(fill=0x80):
    return bytearray([fill] * BONUS_BYTES)


def _set(tiles, x, y, value):
    tiles[(x // 16) * 432 + y * 16 + x % 16] = value


def test_four_plains_tables_and_exact_quadrant_order():
    data = b"".join(bytes((i + n * 10) & 255 for i in range(256)) for n in range(4))
    layout = PlainsQuadrants(data)
    assert layout.patterns(1) == (1, 11, 21, 31)  # UL, LL, UR, LR
    assert layout.patterns(0xFF) == (255, 9, 19, 29)
    assert logical_palette_group(0x3F) == 0
    assert logical_palette_group(0x40) == 1
    assert logical_palette_group(0x80) == 2
    assert logical_palette_group(0xC0) == 3
    with pytest.raises(ValueError, match="four 256-entry"):
        PlainsQuadrants(b"short")
    with pytest.raises(ValueError, match="one byte"):
        layout.patterns(256)


def test_54_byte_pattern_strip_half_selection_and_second_screen():
    data = b"".join(bytes((i + n * 10) & 255 for i in range(256)) for n in range(4))
    layout = PlainsQuadrants(data)
    tiles = _tiles(0x80)
    _set(tiles, 0, 0, 1)
    _set(tiles, 16, 26, 2)
    left = pattern_strip(bytes(tiles), layout, 0, 0)
    right = pattern_strip(bytes(tiles), layout, 0, 1)
    second = pattern_strip(bytes(tiles), layout, 16, 0)
    assert len(left) == len(right) == len(second) == 54
    assert left[:2] == b"\x01\x0B"
    assert right[:2] == b"\x15\x1F"
    assert second[-2:] == b"\x02\x0C"
    with pytest.raises(ValueError, match="half"):
        pattern_strip(bytes(tiles), layout, 0, 2)
    with pytest.raises(ValueError, match="864-byte"):
        pattern_strip(bytes(tiles[:-1]), layout, 0, 0)


def test_14_attribute_bytes_preserve_quadrants_and_split_nibble():
    tiles = _tiles(0x80)
    _set(tiles, 0, 14, 0x00)
    _set(tiles, 1, 14, 0x40)
    _set(tiles, 0, 15, 0x80)
    _set(tiles, 1, 15, 0xC0)
    _set(tiles, 0, 16, 0x40)
    _set(tiles, 1, 16, 0x00)
    attrs = attribute_strip(bytes(tiles), 0)
    assert len(attrs) == 14
    assert attrs[0] == 0xAA  # Four tiles in palette group 2
    assert attrs[7] == 0x04  # Row 14 TL=0, TR=1; row 15 lower bits masked
    assert attrs[8] == 0x1E  # Restart at row 15: groups (2,3)/(1,0)
    assert attrs[9:] == bytes([0xAA] * 5)
    with pytest.raises(ValueError, match="even"):
        attribute_strip(bytes(tiles), 1)
    with pytest.raises(ValueError, match="even"):
        attribute_strip(bytes(tiles), 32)


def test_ppu_column_addresses_and_ciram_mirroring():
    pattern = pattern_write_addresses(3)
    assert len(pattern) == 54
    assert pattern[0] == 0x2003
    assert pattern[29] == 0x23A3
    assert pattern[30] == 0x2803
    assert pattern[53] == 0x2AE3
    attrs = attribute_write_addresses(2)
    assert len(attrs) == 14
    assert attrs[0] == 0x23C2
    assert attrs[7] == 0x23FA
    assert attrs[8] == 0x2BC2
    assert attrs[-1] == 0x2BEA
    # Horizontal MMC3 ($A000 bit 0 = 1): A A / B B
    assert ciram_offset(0x2000, mirroring="horizontal") == 0
    assert ciram_offset(0x2400, mirroring="horizontal") == 0
    assert ciram_offset(0x2800, mirroring="horizontal") == 1024
    # Vertical ($A000 bit 0 = 0): A B / A B
    assert ciram_offset(0x2400, mirroring="vertical") == 1024
    assert ciram_offset(0x2800, mirroring="vertical") == 0
    with pytest.raises(ValueError, match="nametable"):
        ciram_offset(0x3F00, mirroring="horizontal")


def _fill_2bpp(tile_buffer, physical_tile, value):
    offset = physical_tile * 16
    for row in range(8):
        tile_buffer[offset + row] = 255 if value & 1 else 0
        tile_buffer[offset + row + 8] = 255 if value & 2 else 0


def test_background_chr_pages_and_16x16_order_are_independent_from_alpha():
    chr_rom = bytearray(8 * 1024)
    for pattern, value in ((0, 1), (64, 2), (128, 3), (192, 0)):
        _fill_2bpp(chr_rom, pattern, value)
    rom = SimpleNamespace(chr=bytes(chr_rom))
    pages = tuple(range(8))
    assert background_pattern_pixels(rom, 0, pages) == bytes([1] * 64)
    assert background_pattern_pixels(rom, 64, pages) == bytes([2] * 64)
    assert background_pattern_pixels(rom, 128, pages) == bytes([3] * 64)
    assert background_pattern_pixels(rom, 192, pages) == bytes([0] * 64)
    data = bytearray(1024)
    for q, p in enumerate((0, 64, 128, 192)):
        data[256 * q + 0xC1] = p
    image, palette_group = logical_tile_pixels(rom, PlainsQuadrants(bytes(data)), 0xC1, pages)
    assert len(image) == 256 and palette_group == 3
    assert image[0:8] == bytes([1] * 8)
    assert image[8:16] == bytes([3] * 8)
    assert image[8 * 16:8 * 16 + 8] == bytes([2] * 8)
    assert image[8 * 16 + 8:9 * 16] == bytes([0] * 8)
    # Pattern 0 still returns a BG indexed value: zero is not sprite alpha.
    shifted_pages = (4, 1, 2, 3, 4, 5, 6, 7)
    assert background_pattern_pixels(rom, 0, shifted_pages) == bytes([0] * 64)
    with pytest.raises(ValueError, match="physical"):
        background_pattern_pixels(rom, 0, tuple([999] * 8))


def test_private_dump_comparison_is_source_agnostic():
    patterns = bytes(range(54))
    attrs = bytes(range(14))
    ok = compare_background_staging(patterns, attrs, patterns, attrs)
    assert ok["matches"]
    assert ok["capture_provenance_verified"] is False
    assert ok["patterns"]["mismatch_count"] == 0
    altered = bytearray(patterns)
    altered[32] ^= 0x01
    broken = compare_background_staging(patterns, attrs, bytes(altered), attrs[::-1])
    assert not broken["matches"]
    assert broken["patterns"]["first_difference"] == 32
    assert broken["patterns"]["mismatch_count"] == 1
    assert broken["attributes"]["mismatch_count"] == 14
    with pytest.raises(ValueError, match="54 bytes"):
        compare_background_staging(b"", attrs, patterns, attrs)
    with pytest.raises(ValueError, match="14 bytes"):
        compare_background_staging(patterns, attrs, patterns, b"")


@pytest.mark.skipif(not os.getenv("SPRITEMINE_TEST_ROM"), reason="Private SMB3 ROM not configured")
def test_private_plains_fingerprint_and_bonus_staging():
    rom = load_rom(os.environ["SPRITEMINE_TEST_ROM"])
    layout = plains_quadrants(rom)
    assert sha256(layout.data).hexdigest() == PLAIN_LAYOUT_SHA256
    report, tiles = reconstruct_bonus(rom)
    assert report["map_sha256"] == MODEL_SHA256
    assert len(tiles) == BONUS_BYTES
    # Independently recomputed from the read-only original ROM and bonus stream,
    # not copied from the decoder output. Preserve only these SHA-256 values.
    expected = {
        (0, 0): ("7cf1d7eb4d234aa4f5e9152bc6b76147b7cb16b2c5d3674519acbfaeeac95bf9",
                 "7724fed24cee2826840a1934f930cc2e3501ce4f77cdf9c67f5bfd8f14e28e10"),
        (8, 0): ("15a406545bcdd93afd2e0f14c1ba49d5aae7cbbb2fc9f2be0cb9aaf18588e507",
                 "db109de9de3cdbfae29f1d665a51fb3d45957818f513fe8677e1de759972eb1c"),
        (16, 1): ("c0f2eec6558f1cc2867fa9354a4d1a1131a88aeb58a2c5f37e82af378ea3eb0d",
                  "e337dd9a1999e10e9d1640396d83df5bf78ccd16fa63bac4b51b1c29015b3a1d"),
    }
    for (col, half), fingerprints in expected.items():
        actual = bonus_background_summary(rom, tiles, col, half)
        assert (actual["pattern_strip_sha256"], actual["attribute_strip_sha256"]) == fingerprints
    for x in (0, 1, 8, 15, 16, 22, 31):
        for half in (0, 1):
            staging = bonus_background_summary(rom, tiles, x, half)
            assert staging["pattern_strip_length"] == 54
            assert staging["attribute_strip_length"] == 14
            assert staging["native_pattern_attribute_verified"] is False
            assert len(pattern_strip(tiles, layout, x, half)) == 54
