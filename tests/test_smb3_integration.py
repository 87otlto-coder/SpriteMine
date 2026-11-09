"""Optional proprietary ROM validation; ROM bytes never enter source control."""

import os

import pytest

from spritemine.chr import TILES_PER_BANK, bank_image, tile_pixels
from spritemine.rom import load_rom


@pytest.mark.skipif(not os.getenv("SPRITEMINE_TEST_ROM"), reason="Local SMB3 ROM not configured")
def test_user_supplied_smb3_prg1():
    rom = load_rom(os.environ["SPRITEMINE_TEST_ROM"])
    meta = rom.metadata
    assert meta.rom_sha256 == "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"
    assert meta.prg_crc32 == "A0ED7D20"
    assert meta.chr_crc32 == "C2928C49"
    assert meta.prg_chr_crc32 == "2E6301ED"
    assert meta.mapper == 4
    assert (meta.prg_bytes, meta.chr_bytes) == (262144, 131072)
    assert meta.chr_banks_8k == 16
    assert len(rom.chr) // 16 == 8192
    assert len(tile_pixels(rom, 8191)) == 64
    assert bank_image(rom, 15).size == (128, 256)
    assert TILES_PER_BANK == 512
