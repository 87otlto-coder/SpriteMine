"""Synthetic MMC3 trace reconstruction regression tests (no game assets)."""
from __future__ import annotations

import zipfile

import pytest
from research.mesence.decode_mmc3_trace import (
    analyze_trace,
    compare_capture_zip,
    load_chr,
    pattern_at_boundary,
)


def fake_chr() -> bytes:
    # 128 distinct 1 KiB blocks, index 126 is entirely blank.
    return b"".join(bytes([0 if i == 126 else i + 1]) * 1024 for i in range(128))


def fake_trace() -> dict:
    events = []
    clock = 110
    for reg, value in enumerate((8, 102, 83, 4, 34, 50)):
        events.append({"master_clock": clock, "address": 0x8000, "value": 0x40 | reg})
        clock += 1
        events.append({"master_clock": clock, "address": 0x8001, "value": value})
        clock += 1
    return {
        "schema_version": 1, "tool": "spritemine-mmc3-register-trace-v1", "rom_sha1": "a" * 40,
        "dropped_writes": 0, "writes": events,
        "boundaries": [
            {"master_clock": 10, "event": "startFrame", "frame": 1},
            {"master_clock": 200, "event": "endFrame", "frame": 1},
        ],
    }


def test_bank_alignment_and_mmc3_two_modes():
    rom = fake_chr()
    regs = [9, 103, 83, 4, 34, 50, None, None]
    mapped = pattern_at_boundary(rom, 0x40, regs, chr_rom_file_offset=0x40010)
    assert mapped["physical_1k_bank_per_ppu_slot"] == [8, 9, 102, 103, 83, 4, 34, 50]
    assert mapped["source_chr_offsets_per_ppu_slot"] == [x * 1024 for x in mapped["physical_1k_bank_per_ppu_slot"]]
    assert mapped["source_rom_offsets_per_ppu_slot"][0] == 0x40010 + 8 * 1024
    assert mapped["lower_nonzero"] == 4096
    assert mapped["upper_nonzero"] == 4096
    inverse = pattern_at_boundary(rom, 0xC0, regs)
    assert inverse["physical_1k_bank_per_ppu_slot"] == [83, 4, 34, 50, 8, 9, 102, 103]
    assert inverse["chr_inversion_mode"] == 1


def test_missing_bank_registers_are_not_guessed():
    assert pattern_at_boundary(fake_chr(), None, [8, 102, 83, 4, 34, 50, None, None]) is None
    assert pattern_at_boundary(fake_chr(), 0x40, [8, 102, None, 4, 34, 50, None, None]) is None


def test_trace_builds_only_known_boundary_mapping():
    result = analyze_trace(fake_trace(), fake_chr(), rom_sha1="a" * 40)
    assert result["writes_total"] == 12
    assert result["chr_bank_data_writes"] == 6
    assert result["prg_bank_data_writes"] == 0
    assert result["boundaries"][0]["mapping"] is None
    mapped = result["boundaries"][1]["mapping"]
    assert mapped["physical_1k_bank_per_ppu_slot"] == [8, 9, 102, 103, 83, 4, 34, 50]
    assert mapped["ppu_pattern_sha256"]


def test_trace_rejects_wrong_rom_identity():
    with pytest.raises(ValueError, match="SHA-1"):
        analyze_trace(fake_trace(), fake_chr(), rom_sha1="b" * 40)


def test_bank_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="unsupported ROM bank"):
        pattern_at_boundary(fake_chr(), 0x40, [250, 102, 83, 4, 34, 50, None, None])


def test_optional_capture_comparison_never_exports_pixels(tmp_path):
    summary = analyze_trace(fake_trace(), fake_chr())
    mapped = summary["boundaries"][1]["mapping"]
    banks = mapped["physical_1k_bank_per_ppu_slot"]
    source = fake_chr()
    blob = b"".join(source[b * 1024:(b + 1) * 1024] for b in banks)
    path = tmp_path / "capture.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("frame_0000000001_ppu_pattern.bin", blob)
    compared = compare_capture_zip(summary, path)
    assert compared[0]["matches_modeled_boundaries"] == ["endFrame frame 1"]
    assert list(tmp_path.iterdir()) == [path]


def test_trainer_offset_and_chr_rom_integrity(tmp_path):
    hdr = b"NES\x1a" + bytes((1, 1, 0x04, 0)) + bytes(8)
    data = hdr + bytes(512) + bytes(16384) + bytes(8192)
    path = tmp_path / "fixture.nes"
    path.write_bytes(data)
    chr_bytes, sha1, sha256, offset = load_chr(path, require_smb3=False)
    assert len(chr_bytes) == 8192
    assert offset == 16 + 512 + 16384
    assert len(sha1) == 40 and len(sha256) == 64
