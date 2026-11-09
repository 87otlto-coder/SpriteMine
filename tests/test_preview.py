import pytest

from spritemine.preview import PALETTES, preview_bank, preview_tile
from spritemine.rom import parse_nes


def make_rom():
    # First tile: index 1 at top-left and 2 at second pixel; rest is 0.
    tile = bytes((0x80,)) + bytes(7) + bytes((0x40,)) + bytes(7)
    header = b"NES\x1a" + bytes((1, 1, 0x40, 0)) + bytes(8)
    return parse_nes(header + bytes(16384) + tile + bytes(8192 - 16))


def test_synthetic_tile_pixel_mapping():
    rom = make_rom()
    img = preview_tile(rom, 0, "grayscale")
    assert img.mode == "RGB"
    assert img.size == (8, 8)
    assert img.getpixel((0, 0)) == (85, 85, 85)
    assert img.getpixel((1, 0)) == (170, 170, 170)
    assert img.getpixel((2, 0)) == (0, 0, 0)
    assert set(PALETTES) == {"grayscale", "green", "amber"}


def test_bank_map_positions_and_palette_variation():
    rom = make_rom()
    bank = preview_bank(rom, 0, "grayscale")
    assert bank.size == (128, 256)
    assert bank.getpixel((0, 0)) == (85, 85, 85)
    assert bank.getpixel((8, 0)) == (0, 0, 0)
    assert preview_tile(rom, 0, "green").getpixel((0, 0)) != (85, 85, 85)
    with pytest.raises(ValueError, match="Unknown"):
        preview_bank(rom, 0, "not-a-palette")


def test_bank_bounds():
    with pytest.raises(IndexError):
        preview_bank(make_rom(), 1)
