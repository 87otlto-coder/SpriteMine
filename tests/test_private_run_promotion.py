"""Synthetic-only private SMB3 capture promotion tests; no game bytes.

Use a tiny mock capture directory in orchestration tests; separately check
strict 79-file completeness to ensure stripped sharing ZIPs are rejected.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from research.mesence import animation_timeline, promote_private_runs as promote
from test_animation_resume import synthetic_archive


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _complete_mock_run(root: Path, monkeypatch) -> Path:
    run = root / "FIXTURE" / "SMB3" / "GraphicsValidation" / "anim-right-w20-complete"
    run.mkdir(parents=True)
    (run / "A").mkdir()
    (run / "B").mkdir()
    (run / "A2").mkdir()
    (run / "replay.nes").write_bytes(b"synthetic ROM bytes")
    (run / "slot-copy.mss").write_bytes(b"synthetic state bytes")
    (run / "capture.lua").write_text("-- synthetic only", encoding="utf-8")
    (run / "report.json").write_text(json.dumps({
        "statuses": {"replay": "verified", "pixels": "verified", "walking": "verified"}
    }), encoding="utf-8")
    for leg in ("A", "B", "A2"):
        (run / leg / "launch.json").write_text("{}", encoding="utf-8")
    # Seven required files plus 72 others = 79 files.
    for i in range(72):
        (run / "A" / f"mock_{i:03d}.bin").write_bytes(bytes((i,)))
    monkeypatch.setattr(promote, "EXPECTED_ROM_SHA256", sha(b"synthetic ROM bytes"))
    monkeypatch.setattr(promote, "EXPECTED_SLOT_SHA256", sha(b"synthetic state bytes"))
    return run


def test_exact_79_file_private_source_is_valid(tmp_path, monkeypatch):
    run = _complete_mock_run(tmp_path, monkeypatch)
    hashes = promote._run_files(run)
    assert len(hashes) == 79
    assert hashes["replay.nes"] == sha(b"synthetic ROM bytes")


@pytest.mark.parametrize("missing", ["replay.nes", "slot-copy.mss"])
def test_77_or_78_file_sharing_export_cannot_be_promoted(tmp_path, monkeypatch, missing):
    run = _complete_mock_run(tmp_path, monkeypatch)
    (run / missing).unlink()
    with pytest.raises(ValueError, match="79 COMPLETE private files"):
        promote._run_files(run)


def test_partial_capture_cannot_be_promoted(tmp_path, monkeypatch):
    run = _complete_mock_run(tmp_path, monkeypatch)
    report = json.loads((run / "report.json").read_text())
    report["statuses"]["walking"] = "failed"
    (run / "report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="incomplete verification"):
        promote._run_files(run)


def _setup_mock_promotion(synthetic_archive, tmp_path, monkeypatch):
    s = synthetic_archive
    # The shared fixture's original timeline intentionally has only 12 frames.
    # Promotion requires exactly the verified 18-frame sequence (warmups 8–25).
    # Build a distinct synthetic 18-frame archive; never relax the production gate.
    complete_dir = s["animations"] / "right-complete-18"
    animation_timeline.assemble_timeline(s["paths"], complete_dir)
    original_timeline = complete_dir / "timeline.json"
    old_bytes = original_timeline.read_bytes()
    names = tuple(p.name for p in s["paths"])
    monkeypatch.setattr(promote, "EXPECTED_TIMELINE_SHA256", sha(old_bytes))
    monkeypatch.setattr(promote, "EXPECTED_RUNS", names)
    monkeypatch.setattr(promote, "EXPECTED_ROM_SHA256", "c" * 64)
    monkeypatch.setattr(promote, "EXPECTED_SLOT_SHA256", sha(s["slot"].read_bytes()))
    for run in s["paths"]:
        (run / "payload.bin").write_bytes(run.name.encode())

    root = tmp_path / "CANONICAL"
    dest = root / "FIXTURE" / "SMB3" / "GraphicsValidation"
    dest.mkdir(parents=True)
    for source in s["paths"][:12]:
        shutil.copytree(source, dest / source.name)

    records = s["records"]
    by_name = {path.name: records[path.resolve()] for path in s["paths"]}

    def mock_load(run):
        run = Path(run).resolve()
        original, image = by_name[run.name]
        info = copy.deepcopy(original)
        info["frame"]["run_dir"] = str(run)
        return info, image

    monkeypatch.setattr(animation_timeline, "load_verified_window", mock_load)

    def mock_files(run):
        run = Path(run)
        payload = run / "payload.bin"
        if not payload.is_file():
            raise ValueError(f"Mock capture missing: {run}")
        return {"payload.bin": sha(payload.read_bytes())}

    monkeypatch.setattr(promote, "_run_files", mock_files)
    # Avoid accidentally relying on Linux/Windows-specific source paths:
    # the real run_dir source is always independently reverified.
    return original_timeline, old_bytes, root, dest, s


def test_promotion_rejects_valid_but_incomplete_12_frame_archive(
    synthetic_archive, tmp_path, monkeypatch
):
    """A genuine valid 12-frame fixture must fail the 18-frame promotion gate."""
    source = synthetic_archive
    timeline = source["timeline"]
    monkeypatch.setattr(promote, "EXPECTED_TIMELINE_SHA256", sha(timeline.read_bytes()))
    monkeypatch.setattr(promote, "EXPECTED_ROM_SHA256", "c" * 64)
    monkeypatch.setattr(promote, "EXPECTED_SLOT_SHA256", sha(source["slot"].read_bytes()))
    canonical = tmp_path / "CANONICAL"
    (canonical / "FIXTURE" / "SMB3" / "GraphicsValidation").mkdir(parents=True)
    with pytest.raises(ValueError, match="Not the accepted 18-frame"):
        promote.check_and_promote(timeline, canonical)
    assert not any((canonical / "FIXTURE" / "SMB3" / "GraphicsValidation").iterdir())


def test_promotion_dry_run_is_read_only_and_apply_verifies_all_18(synthetic_archive, tmp_path, monkeypatch):
    original, old_bytes, root, dest, s = _setup_mock_promotion(
        synthetic_archive, tmp_path, monkeypatch
    )
    initial = promote.check_and_promote(original, root)
    assert initial["status"] == "ready_for_explicit_write"
    assert initial["verified_original_windows"] == 18
    assert initial["unchanged_canonical_runs"] == 12
    assert initial["missing_runs"] == [p.name for p in s["paths"][12:]]
    assert len(list(dest.iterdir())) == 12
    assert not (root / "FIXTURE" / "SMB3" / "TransferStaging").exists()
    assert original.read_bytes() == old_bytes

    applied = promote.check_and_promote(original, root, apply=True)
    assert applied["status"] == "promoted_and_reverified"
    assert applied["promoted_runs"] == initial["missing_runs"]
    assert applied["verified_canonical_windows"] == 18
    assert len(list(dest.iterdir())) == 18
    for source in s["paths"]:
        assert (dest / source.name / "payload.bin").read_bytes() == source.name.encode()
    assert original.read_bytes() == old_bytes

    repeated = promote.check_and_promote(original, root)
    assert repeated["missing_runs"] == []
    assert repeated["unchanged_canonical_runs"] == 18


def test_existing_canonical_conflict_refuses_all_writes(synthetic_archive, tmp_path, monkeypatch):
    original, old_bytes, root, dest, s = _setup_mock_promotion(
        synthetic_archive, tmp_path, monkeypatch
    )
    existing = dest / s["paths"][0].name / "payload.bin"
    existing.write_bytes(b"tampered already accepted file")
    with pytest.raises(ValueError, match="Existing canonical capture differs"):
        promote.check_and_promote(original, root, apply=True)
    assert not (dest / s["paths"][12].name).exists()
    assert not (root / "FIXTURE" / "SMB3" / "TransferStaging").exists()
    assert original.read_bytes() == old_bytes


def test_share_archive_missing_original_slot_is_rejected(synthetic_archive, tmp_path, monkeypatch):
    # Completeness guard runs before any source-copy operations.
    run = _complete_mock_run(tmp_path, monkeypatch)
    (run / "slot-copy.mss").unlink()
    (run / "replay.nes").unlink()
    with pytest.raises(ValueError, match="found 77"):
        promote._run_files(run)
