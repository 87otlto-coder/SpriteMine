"""Fixture-free tests for SMB3 physical CIRAM -> ROM CHR -> indexed RGB."""

import pytest

from spritemine.ppu_background import (
    Mmc3ChrRegisters, color_codes_to_rgb, read_2c02_rgb_profile,
    render_background_codes,
)


def _observed_mmc3_registers():
    mapper = Mmc3ChrRegisters()
    for register, value in enumerate((8, 96, 0, 4, 34, 79, 6, 26)):
        mapper.write(0x8000, 0x40 | register)
        mapper.write(0x8001, value)
    return mapper


def test_mmc3_register_history_expands_2k_chr_pairs_and_inverts_windows():
    mapper = Mmc3ChrRegisters()
    with pytest.raises(ValueError, match="Incomplete"):
        mapper.pages()
    with pytest.raises(ValueError, match="preceded"):
        mapper.write(0x8001, 5)
    mapper = _observed_mmc3_registers()
    assert mapper.pages() == (8, 9, 96, 97, 0, 4, 34, 79)
    mapper.write(0x8000, 0x80)
    assert mapper.pages() == (0, 4, 34, 79, 8, 9, 96, 97)
    mapper.write(0x8001, 9)
    assert mapper.pages() == (0, 4, 34, 79, 8, 9, 96, 97)  # reg0 odd is rounded down
    mapper.write(0x8000, 0x00)
    assert mapper.pages() == (8, 9, 96, 97, 0, 4, 34, 79)
    with pytest.raises(ValueError, match="register write"):
        mapper.write(0xA000, 1)


def test_palette_is_loaded_from_external_reference_not_vendored():
    # Distinctive synthetic values, not copied third-party palette data.
    source = "static colors = { /* 2C02 */ { " + ", ".join(
        f"0xFF{n:02X}{(63-n):02X}{(n*3)%256:02X}" for n in range(64)
    ) + " } };"
    table = read_2c02_rgb_profile(source)
    assert len(table) == 192
    assert table[:3] == bytes((0, 63, 0))
    assert table[-3:] == bytes((63, 0, 189))
    with pytest.raises(ValueError, match="64"):
        read_2c02_rgb_profile("/* 2C02 */ { 0xFF123456 }")
    with pytest.raises(ValueError, match="no explicit"):
        read_2c02_rgb_profile("0xFF123456")


def _pattern(chr_rom, page, tile, color):
    base = page * 1024 + tile * 16
    for row in range(8):
        chr_rom[base + row] = 0xFF if color & 1 else 0
        chr_rom[base + row + 8] = 0xFF if color & 2 else 0


def _sample():
    rom = bytearray(10 * 1024)
    # For the synthetic sample, pattern window 0 maps to physical CHR page 2.
    _pattern(rom, 2, 1, 1)
    _pattern(rom, 2, 2, 2)
    physical = bytearray(2048)
    # Horizontal MMC3 mirroring: logical NT0/NT1 -> page0; NT2/NT3 -> page1.
    for col in range(32):
        physical[29 * 32 + col] = 1
        physical[1024 + col] = 2
    for i in range(64):
        physical[0x3C0 + i] = 0xFF  # all 4 quadrants use palette group 3
        physical[1024 + 0x3C0 + i] = 0xAA  # palette group 2
    palette = bytearray([0x0F] * 32)
    palette[13] = 0x23  # first row: group 3, pattern index 1
    palette[10] = 0x22  # second row: group 2, pattern index 2
    pages = (2, 3, 4, 5, 6, 7, 8, 9)
    # coarse X=1, coarse Y=29, fine Y=7, nametable0.
    t = 1 | (29 << 5) | (7 << 12)
    return bytes(rom), bytes(physical), bytes(palette), pages, t


def test_scroll_y_239_wraps_to_second_nametable_and_left_mask():
    rom, physical, palette, pages, t = _sample()
    kwargs = dict(
        chr_rom=rom, ciram=physical, palette_ram=palette,
        chr_pages=pages, mirroring_bit=1, scroll_t=t, fine_x=0,
        pattern_base=0, background_enabled=True,
        left_edge_enabled=False, width=16, height=2,
    )
    indices = render_background_codes(**kwargs)
    assert indices[:8] == bytes([0x0F] * 8)
    assert indices[8:16] == bytes([0x23] * 8)
    assert indices[16:24] == bytes([0x0F] * 8)
    assert indices[24:32] == bytes([0x22] * 8)
    full = render_background_codes(**{**kwargs, "left_edge_enabled": True})
    assert full[:16] == bytes([0x23] * 16)
    assert full[16:32] == bytes([0x22] * 16)
    # CHR-page provenance is an actual requirement, not a guessed tile identity.
    wrong = render_background_codes(**{**kwargs, "chr_pages": (0,) + pages[1:]})
    assert wrong[:16] != indices[:16]
    mutated = bytearray(rom)
    mutated[2 * 1024 + 1 * 16 + 7] = 0
    changed = render_background_codes(**{**kwargs, "chr_rom": bytes(mutated)})
    assert changed[8:16] != indices[8:16]


def test_background_rgb_requires_explicit_profile_not_capture_derived_colors():
    codes = bytes((0, 1, 2, 63))
    table = bytes(c for i in range(64) for c in (i, 255 - i, i ^ 0x33))
    assert color_codes_to_rgb(codes, table) == bytes([
        0, 255, 0x33, 1, 254, 0x32, 2, 253, 0x31, 63, 192, 0x0C,
    ])
    with pytest.raises(ValueError, match="64-color"):
        color_codes_to_rgb(codes, b"\x00" * 9)
    with pytest.raises(ValueError, match="outside"):
        color_codes_to_rgb(b"\x40", table)


def test_invalid_or_out_of_scope_ppu_states_are_explicitly_rejected():
    rom, physical, palette, pages, t = _sample()
    kwargs = dict(
        chr_rom=rom, ciram=physical, palette_ram=palette,
        chr_pages=pages, mirroring_bit=1, scroll_t=t, fine_x=0,
        pattern_base=0, background_enabled=True, left_edge_enabled=True,
    )
    for mutation in (
        {"background_enabled": False},
        {"pattern_base": 0x2000},
        {"height": 193},
        {"width": 257},
        {"fine_x": 8},
        {"scroll_t": 30 << 5},
        {"chr_pages": (999,) + pages[1:]},
        {"mirroring_bit": 3},
        {"ciram": b"invalid"},
    ):
        with pytest.raises(ValueError):
            render_background_codes(**{**kwargs, **mutation})
