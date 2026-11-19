"""Fixture-free tests for the PRG1 $2007 -> physical CIRAM acceptance boundary."""

import csv
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from spritemine.background import (
    attribute_write_addresses, ciram_offset, pattern_write_addresses,
)
from research.mesence import verify_ppu_commit_trace as check
from research.mesence.verify_background_staging import STAGING_COLUMNS


def _write(frame=450861, cycle=100, addr=0x2000, value=0x33, bit=1, inc=1):
    return {
        "sequence": 1, "kind": "write", "frame": frame,
        "cpu_cycle": cycle, "scanline": 241, "ppu_cycle": 25,
        "poll": 2500, "register": 0x2007, "value": value,
        "video_ram_addr": addr, "bus_addr": addr,
        "tmp_video_ram_addr": addr, "write_toggle": 0,
        "vertical_write": inc, "mirroring_bit": bit, "tileset": 1,
    }


def _render_ppu(physical, bit):
    ppu = bytearray(0x3000)
    mirror = "horizontal" if bit else "vertical"
    for addr in range(0x2000, 0x3000):
        ppu[addr] = physical[ciram_offset(addr, mirroring=mirror)]
    return bytes(ppu)


def test_vblank_register_writes_are_not_assumed_instantaneous():
    record = _write()
    assert check._safe_vram_write(record) == (0x2000, 0x33)
    record["scanline"] = 100
    assert check._safe_vram_write(record) is None
    record["scanline"] = 261
    assert check._safe_vram_write(record) is None
    record["scanline"] = 241
    record["bus_addr"] = 0x2010
    assert check._safe_vram_write(record) is None
    record["bus_addr"] = 0x2000
    record["ppu_cycle"] = 330
    record["scanline"] = 260
    assert check._safe_vram_write(record) is None


@pytest.mark.parametrize("bit,first,second", [(1, 0x2000, 0x2400), (0, 0x2000, 0x2800)])
def test_ciram_write_mirroring_and_debug_alias(bit, first, second):
    before = bytes([0] * 2048)
    addr = first
    a = _write(addr=addr, bit=bit, value=0xA7)
    after = bytearray(before)
    after[ciram_offset(addr, mirroring=("horizontal" if bit else "vertical"))] = 0xA7
    comparison = check.compare_ciram_frame(before, bytes(after), [a])
    assert comparison["eligible"] and comparison["matches"]
    assert comparison["applied_nametable_writes"] == 1
    view = _render_ppu(bytes(after), bit)
    assert view[first] == view[second] == 0xA7
    assert check.compare_nametable_alias(view, bytes(after), bit)["mismatches"] == 0
    broken = bytearray(view)
    broken[second] ^= 1
    assert check.compare_nametable_alias(bytes(broken), bytes(after), bit)["mismatches"] == 1
    after[1] ^= 1
    assert check.compare_ciram_frame(before, bytes(after), [a])["mismatches"] == 1


def test_nonrendering_state_required_even_when_pixel_memory_did_not_change():
    before = bytes([0] * 2048)
    data = _write()
    data["scanline"] = 160
    assert not check.compare_ciram_frame(before, before, [data])["eligible"]
    with pytest.raises(ValueError, match="exactly 2 KiB"):
        check.compare_ciram_frame(b"", before, [])


def test_private_trace_schema_and_order_checks(tmp_path):
    p = tmp_path / "reg.tsv"
    rows = [[1, "write", 450861, 200, 241, 0, 1, 0x2007, 4,
             0x2000, 0x2000, 0x2000, 0, 1, 1, 1]]
    with p.open("w", newline="", encoding="ascii") as fp:
        writer = csv.writer(fp, delimiter="\t")
        writer.writerow(check.REG_FIELDS)
        writer.writerows(rows)
    loaded = check._load_tsv(p, check.REG_FIELDS, sequence=True)
    check._check_register_rows(loaded)
    assert loaded[0]["video_ram_addr"] == 0x2000
    rows[0][0] = 2
    with p.open("w", newline="", encoding="ascii") as fp:
        writer = csv.writer(fp, delimiter="\t")
        writer.writerow(check.REG_FIELDS)
        writer.writerows(rows)
    with pytest.raises(ValueError, match="Non-monotonic"):
        check._load_tsv(p, check.REG_FIELDS, sequence=True)


def _make_private_synthetic_capture(tmp_path: Path, monkeypatch):
    capture = tmp_path / "run"
    folder = capture / "B"
    folder.mkdir(parents=True)
    tilemem = bytes([0x80] * 864)
    monkeypatch.setattr(check, "MODEL_SHA256", sha256(tilemem).hexdigest())
    producer_rows = []
    writes = []
    expected = bytearray([0] * 2048)
    n = 0
    for sequence, (kind, addrs) in enumerate(
        [("pattern", pattern_write_addresses(0)),
         ("attribute", attribute_write_addresses(0))], 1
    ):
        key = f"bg-{sequence:04d}"
        (folder / f"{key}-tiles.bin").write_bytes(tilemem)
        values = bytes(i % 256 for i in range(len(addrs)))
        (folder / f"{key}-{kind}.bin").write_bytes(values)
        producer_rows.append([sequence, kind, 450861, 80 if kind == "pattern" else 190,
                              241, 5, 2400, 0, 0, 0, 0, 0xC0, 1, 1])
        for addr, value in zip(addrs, values):
            n += 1
            row = _write(cycle=100 + n + (100 if kind == "attribute" else 0),
                         addr=addr, value=value, inc=int(kind == "pattern"))
            row["sequence"] = n
            writes.append(row)
            expected[ciram_offset(addr, mirroring="horizontal")] = value

    with (folder / "background-staging.tsv").open("w", newline="", encoding="ascii") as fp:
        writer = csv.writer(fp, delimiter="\t")
        writer.writerow(STAGING_COLUMNS)
        writer.writerows(producer_rows)

    reg = folder / "ppu-registers.tsv"
    with reg.open("w", newline="", encoding="ascii") as fp:
        writer = csv.DictWriter(fp, delimiter="\t", fieldnames=check.REG_FIELDS)
        writer.writeheader()
        writer.writerows(writes)
    boundary = folder / "ppu-ciram-boundaries.tsv"
    with boundary.open("w", newline="", encoding="ascii") as fp:
        writer = csv.writer(fp, delimiter="\t")
        writer.writerow(check.CIRAM_FIELDS)
        writer.writerows([(450861, "start", 50, 1), (450861, "end", 500, 1)])

    (folder / "ppu-450861-start-ciram.bin").write_bytes(bytes(2048))
    (folder / "ppu-450861-end-ciram.bin").write_bytes(expected)
    (folder / "450861-end-ppu.bin").write_bytes(_render_ppu(expected, 1))
    manifest = {
        "neutral": True, "frame_range": [450861, 450861],
        "source_sha256": {"ppu_register_probe": "synthetic"},
        "ppu_register_trace": {
            "event_count": len(writes), "log_sha256": sha256(reg.read_bytes()).hexdigest(),
            "boundary_count": 2,
            "boundary_log_sha256": sha256(boundary.read_bytes()).hexdigest(),
        },
    }
    (capture / "report.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(check, "verify_staging", lambda rom, path: {"passed": True})
    return SimpleNamespace(), capture, folder


def test_full_ppu_pipeline_synthetic_and_fail_closed(tmp_path, monkeypatch):
    rom, capture, folder = _make_private_synthetic_capture(tmp_path, monkeypatch)
    result = check.verify(rom, capture)
    assert result["passed"]
    assert result["producer_commits"]["counts"]["pattern_matched"] == 1
    assert result["producer_commits"]["counts"]["attribute_matched"] == 1
    assert result["producer_commits"]["counts"]["matched_bytes"] == 68
    assert result["memory"]["nametable_writes"] == 68
    assert result["memory"]["frames_checked"] == 1
    assert result["memory"]["alias_samples"] == 4096
    assert result["memory"]["alias_mismatches"] == 0
    assert not result["native_final_rgb_or_fetch_time_chr_verified"]

    broken = bytearray((folder / "ppu-450861-end-ciram.bin").read_bytes())
    broken[0] ^= 1
    (folder / "ppu-450861-end-ciram.bin").write_bytes(broken)
    failed = check.verify(rom, capture)
    assert not failed["passed"]
    assert failed["memory"]["physical_mismatches"] == 1
    assert failed["memory"]["alias_mismatches"] >= 1


def test_missing_or_changed_native_manifest_fails_closed(tmp_path, monkeypatch):
    rom, capture, folder = _make_private_synthetic_capture(tmp_path, monkeypatch)
    (folder / "ppu-registers.tsv").write_bytes(b"bad")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        check.verify(rom, capture)
