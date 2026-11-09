import json

import pytest

from research.mesence.verify_capture import verify_directory


def create_fixture(directory, frame=7, *, width=2, height=1):
    stem = f"frame_{frame:010d}"
    blobs = {
        "oam": b"\x00" * 256,
        "palette": b"\x00" * 32,
        "ppu_pattern": b"\x00" * 8192,
        "screen_rgb": b"\x00" * (width * height * 3),
    }
    files = {}
    for key, data in blobs.items():
        name = f"{stem}_{key}.bin"
        files[key] = name
        (directory / name).write_bytes(data)
    meta = {
        "schema_version": 1,
        "evidence": "captured",
        "capture_tool": "spritemine-mesence-endframe-v1",
        "event": "endFrame",
        "console_type": "Nes",
        "region": "Ntsc",
        "rom_sha1_reported_by_mesen": "a" * 40,
        "frame_count": frame,
        "master_clock": frame * 1000,
        "screen_width": width,
        "screen_height": height,
        "sprite_height": 8,
        "files": files,
    }
    (directory / f"{stem}.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def test_valid_structural_capture(tmp_path):
    create_fixture(tmp_path, frame=10)
    create_fixture(tmp_path, frame=11)
    report = verify_directory(tmp_path)
    assert report["result"] == "pass_structural_capture_validation"
    assert report["capture_count"] == 2
    assert not report["verified_smb3_rom_provided"]
    assert "same-frame atomicity" in report["not_proven"]
    assert len(report["captures"][0]["blob_sha256"]["oam"]) == 64


def test_missing_or_short_stream_is_rejected(tmp_path):
    create_fixture(tmp_path)
    (tmp_path / "frame_0000000007_oam.bin").write_bytes(b"bad")
    with pytest.raises(ValueError, match="expected 256"):
        verify_directory(tmp_path)


def test_frame_identity_is_not_inferred(tmp_path):
    info = create_fixture(tmp_path)
    info["frame_count"] = 8
    (tmp_path / "frame_0000000007.json").write_text(json.dumps(info), encoding="utf-8")
    with pytest.raises(ValueError, match="frame identity mismatch"):
        verify_directory(tmp_path)


def test_filename_traversal_or_cross_frame_swap_rejected(tmp_path):
    info = create_fixture(tmp_path)
    info["files"]["oam"] = "../other.bin"
    (tmp_path / "frame_0000000007.json").write_text(json.dumps(info), encoding="utf-8")
    with pytest.raises(ValueError, match="invalid oam filename"):
        verify_directory(tmp_path)


def test_inconsistent_rom_identity_rejected(tmp_path):
    create_fixture(tmp_path, frame=7)
    meta = create_fixture(tmp_path, frame=8)
    meta["rom_sha1_reported_by_mesen"] = "b" * 40
    (tmp_path / "frame_0000000008.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(ValueError, match="different Mesen ROM identities"):
        verify_directory(tmp_path)


def test_non_smb3_rom_rejected_when_supplied(tmp_path):
    create_fixture(tmp_path)
    rom = tmp_path / "unrelated.nes"
    rom.write_bytes(b"not SMB3")
    with pytest.raises(ValueError, match="not the verified SMB3"):
        verify_directory(tmp_path, rom)


def test_corrupt_screen_size_rejected(tmp_path):
    info = create_fixture(tmp_path)
    info["screen_height"] = 9999999
    (tmp_path / "frame_0000000007.json").write_text(json.dumps(info), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported screen size"):
        verify_directory(tmp_path)
