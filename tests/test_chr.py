import hashlib
import json

import pytest
from PIL import Image

from spritemine.chr import bank_image, decode_tile, export_chr, tile_pixels
from spritemine.rom import RomFormatError, parse_nes


def make_rom(chr_data=None):
    if chr_data is None:
        chr_data = bytes(8192)
    header = b"NES\x1a" + bytes((1, len(chr_data) // 8192, 0x40, 0)) + bytes(8)
    return parse_nes(header + bytes(16384) + chr_data)


def test_2bpp_bitplanes_and_bit_order():
    tile = bytes([0b10000001] + [0] * 7 + [0b01000001] + [0] * 7)
    pixels = decode_tile(tile)
    assert pixels[:8] == bytes([1, 2, 0, 0, 0, 0, 0, 3])
    assert pixels[8:] == bytes(56)
    with pytest.raises(ValueError):
        decode_tile(b"short")


def test_bank_atlas_dimensions_and_source_tile():
    chr_bytes = bytes([0x80] + [0] * 15) + bytes(8192 - 16)
    image = bank_image(make_rom(chr_bytes), 0)
    assert image.size == (128, 256)
    assert image.getpixel((0, 0)) == 85
    assert image.getpixel((1, 0)) == 0


def test_export_deterministic_manifest_and_png(tmp_path):
    rom = make_rom()
    manifest_path = export_chr(rom, tmp_path)
    data = json.loads(manifest_path.read_text())
    assert data["provenance_type"] == "raw"
    assert len(data["entries"]) == 1
    entry = data["entries"][0]
    assert entry["rom_offset"] == 16 + 16384
    assert entry["tile_count"] == 512
    with Image.open(tmp_path / entry["file"]) as image:
        assert image.size == (128, 256)
    checksum = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    export_chr(rom, tmp_path)
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == checksum
    assert entry["png_sha256"] == hashlib.sha256((tmp_path / entry["file"]).read_bytes()).hexdigest()


def test_export_single_tile_and_bounds(tmp_path):
    rom = make_rom()
    manifest = json.loads(export_chr(rom, tmp_path, tile=511).read_text())
    assert manifest["entries"][0]["rom_offset"] == 16 + 16384 + 511 * 16
    with pytest.raises(IndexError):
        tile_pixels(rom, 512)
    with pytest.raises(ValueError):
        export_chr(rom, tmp_path, bank=1)


def test_static_export_chr_ram_rejected(tmp_path):
    with pytest.raises(RomFormatError, match="CHR-RAM"):
        export_chr(make_rom(b""), tmp_path)
