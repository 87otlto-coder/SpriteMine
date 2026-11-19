"""Native PPU-staging verification tests require no copyrighted fixtures."""

import csv
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from spritemine.background import (
    PlainsQuadrants, attribute_strip, attribute_strip_columns, pattern_strip,
    scroller_attribute_columns,
)
from spritemine.player import ROM_SHA256
from research.mesence import verify_background_staging as checker
from research.mesence.raccoon_route import (
    EXPECTED_POLLS, EXPECTED_SHA256, REPORT, recorded_controller_bytes,
)


def test_source_attribute_pairs_across_scroll_direction_and_screen_boundary():
    assert scroller_attribute_columns(5, 0) == (4, 5)
    assert scroller_attribute_columns(4, 1) == (4, 5)
    assert scroller_attribute_columns(16, 0) == (16, 1)
    assert scroller_attribute_columns(5, 1) == (20, 5)
    assert scroller_attribute_columns(0, 0) == (0, 241)
    assert scroller_attribute_columns(255, 0) == (254, 255)
    with pytest.raises(ValueError, match="scroll direction"):
        scroller_attribute_columns(1, 2)
    with pytest.raises(ValueError, match="8-bit column"):
        scroller_attribute_columns(256, 0)


def test_explicit_nonadjacent_attribute_columns_are_not_conflated():
    tiles = bytearray([0x80] * 864)
    # Place an unrelated palette group at screen 1 column 0.
    tiles[432] = 0x00
    adjacent = attribute_strip_columns(bytes(tiles), 0, 1)
    nonadjacent = attribute_strip_columns(bytes(tiles), 16, 1)
    assert adjacent[0] == 0xAA
    assert nonadjacent[0] == 0xA8
    assert attribute_strip(bytes(tiles), 0) == adjacent
    with pytest.raises(ValueError, match="two-screen"):
        attribute_strip_columns(bytes(tiles), 0, 241)


def test_recorded_raccoon_route_rebuilds_byte_for_byte():
    data = recorded_controller_bytes(REPORT.read_text(encoding="utf-8"))
    assert len(data) == EXPECTED_POLLS
    assert sha256(data).hexdigest() == EXPECTED_SHA256
    assert data[:60] == bytes(60)
    with pytest.raises(ValueError, match="No controller"):
        recorded_controller_bytes("not a report")
    with pytest.raises(ValueError, match="Invalid controller"):
        recorded_controller_bytes("## Replay inputs\n" + (chr := chr(96) * 3) + "text\n3*GG\n" + chr)


def _private_synthetic_capture(tmp_path: Path, monkeypatch, mismatch=False, missing_attr=False):
    capture = tmp_path / "capture"
    detail = capture / "B"
    detail.mkdir(parents=True)
    tiles = bytes([0x80] * 864)
    layout = PlainsQuadrants(bytes(range(256)) * 4)
    monkeypatch.setattr(checker, "MODEL_SHA256", sha256(tiles).hexdigest())
    monkeypatch.setattr(checker, "plains_quadrants", lambda rom: layout)
    model_pattern = pattern_strip(tiles, layout, 0, 0)
    model_attr = attribute_strip_columns(tiles, 0, 1)
    rows = []
    for sequence, kind in [(1, "pattern"), (2, "attribute")]:
        if missing_attr and kind == "attribute":
            break
        key = f"bg-{sequence:04d}"
        (detail / f"{key}-tiles.bin").write_bytes(tiles)
        p = bytearray(model_pattern)
        if mismatch and kind == "pattern":
            p[0] ^= 0x80
        (detail / f"{key}-pattern.bin").write_bytes(p)
        (detail / f"{key}-attribute.bin").write_bytes(model_attr)
        rows.append([sequence, kind, 450861, 13426820944 + sequence,
                     250, 0, 2560, 1, 0, 0, 0, 0xC0, 1, 1])
    log = detail / "background-staging.tsv"
    with log.open("w", encoding="ascii", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(checker.STAGING_COLUMNS)
        writer.writerows(rows)
    (capture / "report.json").write_text(json.dumps({
        "neutral": True,
        "source_sha256": {"rom": ROM_SHA256, "background_probe": "synthetic"},
        "background_staging": {
            "event_count": len(rows),
            "log_sha256": sha256(log.read_bytes()).hexdigest(),
        },
    }), encoding="utf-8")
    rom = SimpleNamespace(metadata=SimpleNamespace(rom_sha256=ROM_SHA256))
    return rom, capture


def test_native_staging_verifier_requires_both_producers_and_exact_bytes(tmp_path, monkeypatch):
    rom, capture = _private_synthetic_capture(tmp_path, monkeypatch)
    result = checker.verify(rom, capture)
    assert result["passed"] and result["counts"]["bytes_checked"] == 68
    assert result["counts"]["pattern_checked"] == result["counts"]["attribute_checked"] == 1
    assert not result["native_final_ppu_or_rgb_verified"]


def test_native_staging_reports_differences_without_forging_pass(tmp_path, monkeypatch):
    rom, capture = _private_synthetic_capture(tmp_path, monkeypatch, mismatch=True)
    report = checker.verify(rom, capture)
    assert not report["passed"]
    assert report["counts"]["mismatches"] == 1
    assert report["comparisons"][0]["first_difference"] == 0
    (capture / "report.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="neutrality"):
        checker.verify(rom, capture)


def test_native_staging_rejects_missing_attribute_capture(tmp_path, monkeypatch):
    rom, capture = _private_synthetic_capture(tmp_path, monkeypatch, missing_attr=True)
    result = checker.verify(rom, capture)
    assert not result["passed"]
    assert result["counts"]["pattern_checked"] == 1
    assert result["counts"]["attribute_checked"] == 0
    assert result["missing_evidence"]
