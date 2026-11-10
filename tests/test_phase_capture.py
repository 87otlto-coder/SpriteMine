"""Deterministic phase-capture contract and in-session MMC3 model tests."""

from __future__ import annotations

import hashlib
import json

import pytest

from research.mesence.verify_phase_capture import verify_phase_session


def _synthetic_chr() -> bytes:
    return bytes((bank * 3 + i) % 256 for bank in range(128) for i in range(1024))


def _ppu_from_banks(chr_rom: bytes, banks: list[int]) -> bytes:
    return b"".join(chr_rom[b * 1024:(b + 1) * 1024] for b in banks)


def make_session(tmp_path):
    chr_rom = _synthetic_chr()
    rom_image = (
        b"NES\x1a" + bytes((1, 16, 0x40, 0)) + bytes(8)
        + bytes(16384) + chr_rom
    )
    rom_path = tmp_path / "synthetic.nes"
    rom_path.write_bytes(rom_image)
    rom_sha1 = hashlib.sha1(rom_image).hexdigest().upper()

    session = "phase_0000000500_1234567890"
    banks_a = [8, 9, 102, 103, 83, 4, 34, 50]
    banks_b = [92, 93, 94, 95, 126, 126, 126, 126]
    snapshots = []
    for idx, (event, frame, clock, banks) in enumerate(
        (
            ("startFrame", 500, 100, banks_a),
            ("endFrame", 500, 200, banks_b),
            ("startFrame", 501, 400, banks_a),
            ("endFrame", 501, 600, banks_b),
        ),
        start=1,
    ):
        files = {}
        blobs = {
            "oam": bytes([248] * 256),
            "palette": bytes(range(32)),
            "ppu_pattern": _ppu_from_banks(chr_rom, banks),
        }
        for name, data in blobs.items():
            filename = f"{session}_{idx}_{event}_{name}.bin"
            (tmp_path / filename).write_bytes(data)
            files[name] = filename
        snapshots.append({
            "event": event, "frame_count": frame, "master_clock": clock,
            "ppu_scanline": -1 if event == "startFrame" else 240,
            "ppu_cycle": 0, "sprite_height": 16,
            "files": files,
        })

    writes = []
    for values, frame, start_clock, scanline in (
        ([92, 94, 126, 126, 126, 126], 500, 120, 193),
        ([8, 102, 83, 4, 34, 50], 501, 260, 246),
        ([92, 94, 126, 126, 126, 126], 501, 450, 193),
    ):
        clock = start_clock
        for register, value in enumerate(values):
            for address, entry in ((0x8000, 0x40 | register), (0x8001, value)):
                writes.append({
                    "frame_count": frame, "master_clock": clock,
                    "ppu_scanline": scanline, "ppu_cycle": 30,
                    "address": address, "value": entry,
                })
                clock += 1

    info = {
        "schema_version": 1,
        "capture_tool": "spritemine-mesence-phase-capture-v1",
        "evidence": "captured",
        "rom_sha1_reported_by_mesen": rom_sha1,
        "session_id": session,
        "completed_frame_pairs": 2,
        "write_limit": 256,
        "dropped_writes": 0,
        "phase_captures": snapshots,
        "writes": writes,
    }
    manifest = tmp_path / f"{session}.json"
    manifest.write_text(json.dumps(info), encoding="utf-8")
    return manifest, rom_path, info


def _rewrite(manifest, source):
    manifest.write_text(json.dumps(source), encoding="utf-8")


def test_complete_session_reconstructs_three_known_boundaries(tmp_path):
    manifest, rom_path, _ = make_session(tmp_path)
    result = verify_phase_session(manifest, rom_path, allow_synthetic_rom=True)
    assert result["result"] == "pass_structural_phase_capture_validation"
    assert result["capture_count"] == 4 and result["blob_count"] == 12
    assert result["captured_frames"] == [500, 501]
    assert result["mmc3_writes"] == 36
    assert result["mapper_model_status"] == "matches_known_boundaries"
    assert result["model_matches"] == 3
    assert result["model_mismatches"] == 0
    assert result["model_unknown_snapshots"] == 1
    assert result["snapshots"][0]["model"] is None
    assert result["snapshots"][2]["model"]["physical_1k_banks"] == [8, 9, 102, 103, 83, 4, 34, 50]
    assert result["snapshots"][1]["model"]["physical_1k_banks"] == [92, 93, 94, 95, 126, 126, 126, 126]


def test_without_source_rom_verifies_only_structure(tmp_path):
    manifest, _, _ = make_session(tmp_path)
    report = verify_phase_session(manifest)
    assert report["mapper_model_status"] == "not_attempted_no_verified_rom"
    assert report["model_matches"] == 0
    assert not report["verified_smb3_rom_provided"]


def test_corrupted_ppu_blob_is_rejected(tmp_path):
    manifest, _, info = make_session(tmp_path)
    filename = info["phase_captures"][1]["files"]["ppu_pattern"]
    (tmp_path / filename).write_bytes(b"\0" * 8)
    with pytest.raises(ValueError, match="expected 8192"):
        verify_phase_session(manifest)


def test_filename_traversal_or_swapped_sample_is_rejected(tmp_path):
    manifest, _, info = make_session(tmp_path)
    info["phase_captures"][0]["files"]["oam"] = "../invalid.bin"
    _rewrite(manifest, info)
    with pytest.raises(ValueError, match="mismatched file references"):
        verify_phase_session(manifest)


def test_event_order_is_not_forgiven(tmp_path):
    manifest, _, info = make_session(tmp_path)
    info["phase_captures"][1]["event"] = "startFrame"
    _rewrite(manifest, info)
    with pytest.raises(ValueError, match="incorrect start/end"):
        verify_phase_session(manifest)


def test_duplicate_clock_rejected(tmp_path):
    manifest, _, info = make_session(tmp_path)
    info["phase_captures"][1]["master_clock"] = 100
    _rewrite(manifest, info)
    with pytest.raises(ValueError, match="strictly increasing"):
        verify_phase_session(manifest)


def test_mapper_write_clock_rejected(tmp_path):
    manifest, _, info = make_session(tmp_path)
    info["writes"][1]["master_clock"] = info["writes"][0]["master_clock"]
    _rewrite(manifest, info)
    with pytest.raises(ValueError, match="chronologically ordered"):
        verify_phase_session(manifest)


def test_incomplete_register_trace_disables_model_without_faking_success(tmp_path):
    manifest, rom, info = make_session(tmp_path)
    info["dropped_writes"] = 3
    _rewrite(manifest, info)
    report = verify_phase_session(manifest, rom, allow_synthetic_rom=True)
    assert report["mapper_model_status"] == "unavailable_dropped_register_writes"
    assert report["model_unknown_snapshots"] == 4


def test_wrong_rom_identity_rejected(tmp_path):
    manifest, rom, _ = make_session(tmp_path)
    image = bytearray(rom.read_bytes())
    image[-1] ^= 1
    rom.write_bytes(image)
    with pytest.raises(ValueError, match="Emulator ROM SHA-1"):
        verify_phase_session(manifest, rom, allow_synthetic_rom=True)


def test_model_mismatch_is_visible_not_silently_accepted(tmp_path):
    manifest, rom, info = make_session(tmp_path)
    path = tmp_path / info["phase_captures"][3]["files"]["ppu_pattern"]
    data = bytearray(path.read_bytes())
    data[200] ^= 1
    path.write_bytes(data)
    report = verify_phase_session(manifest, rom, allow_synthetic_rom=True)
    assert report["mapper_model_status"] == "mismatch"
    assert report["model_mismatches"] == 1
    assert report["model_matches"] == 2


def test_absent_initial_register_mapping_is_labeled_unknown(tmp_path):
    manifest, rom, info = make_session(tmp_path)
    info["writes"] = []
    _rewrite(manifest, info)
    report = verify_phase_session(manifest, rom, allow_synthetic_rom=True)
    assert report["mapper_model_status"] == "unavailable_missing_initial_register_state"
    assert report["model_unknown_snapshots"] == 4


def test_real_cli_requires_verified_smb3_not_synthetic_rom(tmp_path):
    manifest, rom, _ = make_session(tmp_path)
    with pytest.raises(ValueError, match="not verified SMB3"):
        verify_phase_session(manifest, rom)
