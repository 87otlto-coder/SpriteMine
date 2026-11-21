"""Fixture-free verification of replay-source CHR timing and offline CLI entry."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

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
