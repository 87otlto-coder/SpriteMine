import os

import pytest

from spritemine.rom import load_rom
from spritemine.world1_1 import MODEL_SHA256, _build_bonus, compare_bonus, reconstruct_bonus


def test_screen_major_writes_and_junction():
    # Two coin cells straddle the horizontal screen boundary.
    tiles, commands = _build_bonus(bytes([0x21, 15, 0x81, 0xE2, 7, 9, 0xFF]))
    assert len(tiles) == 864
    assert tiles[31] == tiles[448] == 0x40
    assert tiles.count(0x40) == 2
    assert commands[1]["junction_slot"] == 2
    assert commands[1]["x_descriptor"] == 9
    with pytest.raises(ValueError, match="outside"):
        _build_bonus(bytes([0x21, 31, 0x81, 0xFF]))
    with pytest.raises(ValueError, match="terminal"):
        _build_bonus(bytes([0x21, 15, 0x81]))


def test_dump_comparison_does_not_assume_capture_origin(tmp_path):
    dump = tmp_path / "tiles.bin"
    dump.write_bytes(b"abcd")
    assert compare_bonus(b"abcd", dump)["matches"]
    observed = compare_bonus(b"axcy", dump)
    assert (observed["first_difference"], observed["mismatch_count"]) == (1, 2)
    with pytest.raises(ValueError, match="exactly"):
        compare_bonus(b"abc", dump)


@pytest.mark.skipif(not os.getenv("SPRITEMINE_TEST_ROM"), reason="Local SMB3 ROM not configured")
def test_private_bonus_model():
    report, tiles = reconstruct_bonus(load_rom(os.environ["SPRITEMINE_TEST_ROM"]))
    assert len(tiles) == 864
    assert report["map_sha256"] == MODEL_SHA256
    assert report["runtime_verified"] is False
    assert len(report["commands"]) == 22
    assert [item["screen_count"] for item in report["headers"]] == [11, 2]
