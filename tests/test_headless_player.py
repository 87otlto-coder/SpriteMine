import json
import os

import pytest

from spritemine.cli import main
from spritemine.player import OFFSETS, PAGES, PATTERNS, _decode_recipe, inspect_recipes
from spritemine.rom import load_rom, parse_nes
from spritemine.sprite import compose_scanline, mmc3_pages, sprite_pixels, sprite_tiles


def test_recipe_lookup_uses_bias_and_swaps_oam_rows():
    image = bytearray(PAGES + 81)
    image[OFFSETS] = 5
    image[PATTERNS + 6:PATTERNS + 12] = bytes([1, 2, 3, 0xF1, 5, 6])
    image[PAGES] = 7
    recipe = _decode_recipe(image, 0)
    assert recipe["chr_page_offset"] == 7
    assert [c["relative_oam_slot"] for c in recipe["components"]] == [3, 4, 5, 0, 1, 2]
    assert recipe["components"][3]["software_hidden"]
    with pytest.raises(ValueError):
        _decode_recipe(image, 1)
    with pytest.raises(ValueError):
        _decode_recipe(image, 81)


@pytest.fixture
def synthetic_rom():
    header = b"NES\x1a" + bytes([1, 16, 0x40]) + bytes(9)
    chr_rom = bytearray(131072)
    chr_rom[0] = 0x80
    chr_rom[1] = 0x40
    chr_rom[16 + 8 + 7] = 0x01
    return parse_nes(header + bytes(16384) + chr_rom)


def test_mapper_modes_and_tile_pair():
    assert mmc3_pages((131, 5, 6, 7, 8, 9), False) == (2, 3, 4, 5, 6, 7, 8, 9)
    assert mmc3_pages((131, 5, 6, 7, 8, 9), True) == (6, 7, 8, 9, 2, 3, 4, 5)
    assert sprite_tiles(0x41, tuple(range(8))) == (320, 321)
    assert sprite_tiles(0x40, tuple(range(8))) == (64, 65)
    with pytest.raises(ValueError):
        sprite_tiles(256, tuple(range(8)))


def test_whole_sprite_flips(synthetic_rom):
    for attrs, first, last in [(0, 0, 127), (64, 7, 120), (128, 120, 7), (192, 127, 0)]:
        pixels = sprite_pixels(synthetic_rom, 0, (0,) * 8, attrs)
        assert (pixels[first], pixels[last], sum(map(bool, pixels))) == (1, 2, 3)
    with pytest.raises(ValueError, match="exact SMB3"):
        inspect_recipes(synthetic_rom)


def test_behind_background_winner_never_reveals_later_sprite(synthetic_rom):
    oam = bytes([9, 0, 32, 8, 9, 0, 3, 8]) + bytes([248, 0, 0, 0]) * 62
    bg = bytes([1]) * 256
    line = compose_scanline(synthetic_rom, oam, (0,) * 8, 10, bg)
    assert (line.winning_oam_slots[8], line.background_wins[8], line.sprite_palette_offsets[8]) == (0, 1, 0)
    line = compose_scanline(synthetic_rom, oam, (0,) * 8, 10, bytes(256))
    assert (line.winning_oam_slots[8], line.sprite_palette_offsets[8:10]) == (0, b"\x01\x00")
    line = compose_scanline(synthetic_rom, oam, (0,) * 8, 9, bg)
    assert line.winning_oam_slots[8] is None


def test_scanline_limit_and_clipping(synthetic_rom):
    oam = bytes([9, 2, 0, 0]) * 8 + bytes([9, 0, 3, 255]) + bytes([248, 0, 0, 0]) * 55
    line = compose_scanline(synthetic_rom, oam, (0,) * 8, 10, bytes(256))
    assert line.winning_oam_slots[255] is None
    line = compose_scanline(synthetic_rom, oam[4:] + bytes([248, 0, 0, 0]), (0,) * 8, 10, bytes(256))
    assert line.sprite_palette_offsets[255] == 13
    left = bytes([9, 0, 0, 0]) + bytes([248, 0, 0, 0]) * 63
    line = compose_scanline(synthetic_rom, left, (0,) * 8, 10, bytes(256), sprites_left_enabled=False)
    assert line.winning_oam_slots[0] is None


@pytest.mark.skipif(not os.getenv("SPRITEMINE_TEST_ROM"), reason="Local SMB3 ROM not configured")
def test_private_original_cli(capsys):
    path = os.environ["SPRITEMINE_TEST_ROM"]
    assert len(inspect_recipes(load_rom(path))["recipes"]) == 81
    outputs = []
    for _ in range(2):
        assert main(["validate-sprite", path]) == 0
        outputs.append(capsys.readouterr().out)
    assert outputs[0] == outputs[1]
    reports = json.loads(outputs[0])["frames"]
    assert [r["transparent_pixels"] for r in reports] == [118, 82, 62]
    assert all(r["matches_reference"] for r in reports)
