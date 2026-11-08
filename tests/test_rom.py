import hashlib
import zipfile

import pytest

from spritemine.rom import RomFormatError, load_rom, parse_nes


def make_rom(*, trainer=False, chr_banks=1, mapper=4):
    flags6 = (mapper & 0x0F) << 4 | (0x04 if trainer else 0)
    header = b"NES\x1a" + bytes((1, chr_banks, flags6, mapper & 0xF0)) + bytes(8)
    return header + (bytes(512) if trainer else b"") + bytes(16384) + bytes(8192 * chr_banks)


def test_parse_ines_offsets_hash_and_mapper():
    data = make_rom(trainer=True)
    rom = parse_nes(data)
    assert rom.metadata.mapper == 4
    assert rom.metadata.prg_rom_offset == 528
    assert rom.metadata.chr_rom_offset == 528 + 16384
    assert rom.metadata.trainer_present
    assert rom.metadata.chr_banks_8k == 1
    assert rom.metadata.rom_sha256 == hashlib.sha256(data).hexdigest()
    assert rom.metadata.prg_chr_crc32 == "6EBED2EE"


def test_reject_bad_headers_and_truncation():
    with pytest.raises(RomFormatError, match="header"):
        parse_nes(b"not a rom")
    with pytest.raises(RomFormatError, match="Truncated"):
        parse_nes(make_rom()[:-1])
    with pytest.raises(RomFormatError, match="NES 2.0"):
        data = bytearray(make_rom())
        data[7] |= 0x08
        parse_nes(bytes(data))


def test_chr_ram_is_identified_without_fake_chr_bytes():
    rom = parse_nes(make_rom(chr_banks=0))
    assert rom.chr == b""
    assert rom.metadata.chr_banks_8k == 0


def test_zip_requires_exactly_one_nes_and_does_not_extract(tmp_path):
    zpath = tmp_path / "game.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("nested/sample.nes", make_rom())
    assert load_rom(zpath).metadata.mapper == 4
    assert not (tmp_path / "nested").exists()
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("a.nes", make_rom())
        z.writestr("b.nes", make_rom())
    with pytest.raises(RomFormatError, match="exactly one"):
        load_rom(zpath)


def test_invalid_zip_fails_explicitly(tmp_path):
    path = tmp_path / "bad.zip"
    path.write_bytes(b"zip?")
    with pytest.raises(RomFormatError, match="Invalid ZIP"):
        load_rom(path)
