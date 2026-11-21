"""Fixture-free verification of replay-source CHR timing and offline CLI entry."""

import os
from pathlib import Path
import subprocess
import sys

import pytest
from types import SimpleNamespace

from spritemine.ppu_background import color_codes_to_rgb, render_background_codes
from spritemine.player import ROM_SHA256
from research.mesence import verify_visible_background as vb

from research.mesence.verify_visible_background import (
    _boundary_mirroring, _ppu_state, _start_mmc3_pages,
)


def _events(path: Path, *, bad_chr_write=False):
    lines = []
    clock = 0

    def event(kind, frame, scanline, address=0, value=0):
        nonlocal clock
        clock += 10
        lines.append(f"{kind}\t{frame}\t{clock}\t{scanline}\t0\t{address}\t{value}")

    for reg, value in enumerate((8, 96, 0, 4, 34, 79, 6, 26)):
        event("mapper-write", 450869, 241, 0x8000, 0x40 | reg)
        event("mapper-write", 450869, 241, 0x8001, value)
    event("start", 450869, -1)
    event("mapper-write", 450869, 4, 0x8000, 0x46)
    event("mapper-write", 450869, 4, 0x8001, 9)  # PRG only
    if bad_chr_write:
        event("mapper-write", 450869, 100, 0x8000, 0x40)
        event("mapper-write", 450869, 100, 0x8001, 92)
    event("irq", 450869, 191)
    event("mapper-write", 450869, 193, 0x8000, 0x40)
    event("mapper-write", 450869, 193, 0x8001, 92)  # HUD switching is excluded
    event("end", 450869, 240)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def test_chr_is_source_mapped_and_hud_irq_switch_does_not_invalidate_gameplay(tmp_path):
    path = tmp_path / "events.tsv"
    _events(path)
    assert _start_mmc3_pages(path, range(450869, 450870)) == {
        450869: (8, 9, 96, 97, 0, 4, 34, 79)
    }
    _events(path, bad_chr_write=True)
    with pytest.raises(ValueError, match="changed"):
        _start_mmc3_pages(path, range(450869, 450870))


def test_source_event_frame_presence_and_order_fail_closed(tmp_path):
    path = tmp_path / "events.tsv"
    _events(path)
    with pytest.raises(ValueError, match="Missing"):
        _start_mmc3_pages(path, range(450869, 450871))
    source = path.read_text(encoding="ascii")
    path.write_text(source + "end\t450870\t1\t240\t0\t0\t0\n", encoding="ascii")
    with pytest.raises(ValueError, match="clock order"):
        _start_mmc3_pages(path, range(450869, 450870))


def test_ciram_boundary_schema_and_duplicate_state_are_checked(tmp_path):
    boundary = tmp_path / "ppu-ciram-boundaries.tsv"
    boundary.write_text(
        "frame\tboundary\tcpu_cycle\tmirroring_bit\n"
        "450869\tstart\t1\t1\n450869\tend\t2\t1\n", encoding="ascii"
    )
    assert _boundary_mirroring(boundary)[(450869, "start")] == 1
    boundary.write_text(boundary.read_text(encoding="ascii") +
                        "450869\tstart\t3\t1\n", encoding="ascii")
    with pytest.raises(ValueError, match="Duplicate"):
        _boundary_mirroring(boundary)

    state = tmp_path / "state.txt"
    state.write_text("ppu.xScroll=0\nppu.xScroll=1\n", encoding="ascii")
    with pytest.raises(ValueError, match="Duplicate"):
        _ppu_state(state)


def test_direct_script_help_imports_without_repo_in_pythonpath(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = root / "research" / "mesence" / "verify_visible_background.py"
    env = dict(os.environ, PYTHONPATH=str(root / "src"))
    run = subprocess.run(
        [sys.executable, str(script), "--help"], cwd=tmp_path,
        capture_output=True, text=True, env=env, timeout=15,
    )
    assert run.returncode == 0, run.stderr
    assert "palette_source" in run.stdout



def test_full_offline_rgb_gate_and_one_pixel_tamper(tmp_path, monkeypatch):
    """Exercise the complete private-capture schema without original game bytes."""
    rom = bytearray(128 * 1024)
    # Set pattern 1 in physical CHR page 8 to a distinct all-color-1 tile.
    for row in range(8):
        rom[8 * 1024 + 16 + row] = 0xFF
    physical = bytearray(2048)
    # Both physical nametables contain synthetic tile 1.
    for nt in (0, 1024):
        for i in range(960):
            physical[nt + i] = 1
    physical = bytes(physical)
    palette = bytearray([15] * 32)
    palette[1] = 32
    palette = bytes(palette)
    profile_cpp = tmp_path / "NesDefaultVideoFilter.cpp"
    profile_cpp.write_text("/* 2C02 */ { " + ", ".join(
        f"0xFF{n:02X}{(63-n):02X}{n:02X}" for n in range(64)
    ) + " }", encoding="ascii")
    profile = bytes(channel for n in range(64) for channel in (n, 63 - n, n))

    capture = tmp_path / "capture"
    folder = capture / "B"
    folder.mkdir(parents=True)
    _events(folder / "events.tsv")
    (folder / "ppu-ciram-boundaries.tsv").write_text(
        "frame\tboundary\tcpu_cycle\tmirroring_bit\n"
        "450869\tstart\t1\t1\n450869\tend\t2\t1\n", encoding="ascii"
    )
    from research.mesence.verify_ppu_commit_trace import REG_FIELDS
    (folder / "ppu-registers.tsv").write_text("\t".join(REG_FIELDS) + "\n", encoding="ascii")
    (folder / "ppu-450869-start-ciram.bin").write_bytes(physical)
    for side in ("start", "end"):
        (folder / f"450869-{side}-palette.bin").write_bytes(palette)
    state = (
        "ppu.mask.backgroundEnabled=true\n"
        "ppu.mask.backgroundMask=false\n"
        "ppu.control.backgroundPatternAddr=0\n"
        "ppu.mask.grayscale=false\n"
        "ppu.intensifyColorBits=0\n"
        "ppu.tmpVideoRamAddr=0\n"
        "ppu.xScroll=0\n"
    )
    (folder / "450869-start-ppu-state.txt").write_text(state, encoding="ascii")
    (folder / "450869-end-ppu-state.txt").write_text(state, encoding="ascii")

    # 8 * 1-KiB CHR mapping followed by 4 KiB mirrored PPU nametables.
    pages = (8, 9, 96, 97, 0, 4, 34, 79)
    mapped = b"".join(bytes(rom[p * 1024:(p + 1) * 1024]) for p in pages)
    mapped_nt = b"".join(
        physical[((n // 2) * 1024):((n // 2 + 1) * 1024)]
        for n in range(4)
    )
    (folder / "450869-start-ppu.bin").write_bytes(mapped + mapped_nt)
    color_codes = render_background_codes(
        chr_rom=bytes(rom), ciram=physical, palette_ram=palette,
        chr_pages=pages, mirroring_bit=1, scroll_t=0, fine_x=0,
        pattern_base=0, background_enabled=True, left_edge_enabled=False,
    )
    actual = color_codes_to_rgb(color_codes, profile) + bytes(256 * 48 * 3)
    native = folder / "450869-end-rgb.bin"
    native.write_bytes(actual)

    monkeypatch.setattr(vb, "verify_ciram", lambda *args: {"passed": True})
    sample = SimpleNamespace(chr=bytes(rom), metadata=SimpleNamespace(rom_sha256=ROM_SHA256))
    good = vb.verify(sample, capture, profile_cpp, first=450869, last=450869)
    assert good["passed"]
    assert good["compared_pixels"] == 256 * 192
    assert good["mismatches"] == 0
    assert good["frames"][0]["chr_pages_1k"] == pages

    changed = bytearray(actual)
    changed[(72 * 256 + 10) * 3] ^= 1
    native.write_bytes(changed)
    broken = vb.verify(sample, capture, profile_cpp, first=450869, last=450869)
    assert not broken["passed"]
    assert broken["mismatches"] == 1
    assert broken["frames"][0]["first_difference"] == {"x": 10, "y": 72}

    # Model CHR pages and mapped debug CHR must independently agree.
    snapshot = folder / "450869-start-ppu.bin"
    mapped_tampered = bytearray(snapshot.read_bytes())
    mapped_tampered[16] ^= 1
    snapshot.write_bytes(mapped_tampered)
    with pytest.raises(ValueError, match="CHR register history"):
        vb.verify(sample, capture, profile_cpp, first=450869, last=450869)
