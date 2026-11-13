"""Synthetic-only audit tests for historical warmup-26 report reassessment.

No SMB3 ROM or game graphics are bundled or generated.
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from research.mesence import graphics_report, reassess_motion as reassess
from research.mesence.animation_timeline import _initial_report


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def old_failed_capture(tmp_path, monkeypatch):
    run = (tmp_path / "FIXTURE" / "SMB3" / "GraphicsValidation"
           / reassess.EXPECTED_NAME)
    run.mkdir(parents=True)
    for leg in ("A", "B", "A2"):
        (run / leg).mkdir()
        (run / leg / "launch.json").write_text("{}", encoding="utf-8")

    rom = b"synthetic rom reference"
    slot = b"synthetic state reference"
    probe = b"synthetic lua reference"
    (run / "replay.nes").write_bytes(rom)
    (run / "slot-copy.mss").write_bytes(slot)
    (run / "capture.lua").write_bytes(probe)

    monkeypatch.setattr(reassess, "EXPECTED_ROM_SHA256", sha(rom))
    monkeypatch.setattr(reassess, "EXPECTED_SLOT_SHA256", sha(slot))
    monkeypatch.setattr(reassess, "EXPECTED_PROBE", sha(probe))
    monkeypatch.setattr(reassess, "EXPECTED_EXE", "a" * 64)

    report = {"schema": 1, **_initial_report()}
    report["statuses"]["replay"] = "verified"
    report["statuses"]["pixels"] = "verified"
    report["statuses"]["walking"] = "failed"
    report["provenance"] = {
        "plan": "right", "warmup": 26, "rom_sha256": sha(rom),
        "slot_sha256": sha(slot), "probe_sha256": sha(probe),
        "emulator_sha256": "a" * 64,
    }
    report["boundaries"] = [
        {"frame_count": 448402}, {"frame_count": 448402},
        {"frame_count": 448403}, {"frame_count": 448403},
    ]
    (run / "report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2), encoding="utf-8"
    )
    (run / "report.html").write_text(
        graphics_report.format_report_html(run, report), encoding="utf-8"
    )

    # Five root artifacts, three launch.json files, and 71 others = 79.
    for i in range(71):
        (run / "A" / f"source_{i:03d}.dat").write_bytes(bytes((i,)))

    def fake_validate(path, result, *, write_visuals=True):
        assert Path(path).resolve() == run.resolve()
        assert not write_visuals
        result.clear()
        result.update(copy.deepcopy(report))
        result["statuses"]["walking"] = "verified"

    def fake_load(path):
        assert Path(path).resolve() == run.resolve()
        loaded = json.loads((run / "report.json").read_text())
        assert loaded["statuses"]["walking"] == "verified"
        return {"frame": {"frame_count": reassess.EXPECTED_FRAME}}, None

    monkeypatch.setattr(reassess.graphics_report, "validate", fake_validate)
    monkeypatch.setattr(reassess, "load_verified_window", fake_load)
    return run, report


def test_dry_run_does_not_modify_any_file(old_failed_capture):
    run, old_report = old_failed_capture
    before = reassess._capture_manifest(run)
    result = reassess.reassess(run)
    assert result["status"] == "ready_for_explicit_reassessment"
    assert result["changes"] == {"walking": ["failed", "verified"]}
    assert reassess._capture_manifest(run) == before
    assert not (run.parent.parent / "ReviewHistory").exists()


def test_apply_preserves_original_report_and_rechecks_raw_evidence(old_failed_capture):
    run, old_report = old_failed_capture
    before = reassess._capture_manifest(run)
    result = reassess.reassess(run, apply=True)
    assert result["status"] == "reassessed_and_independently_verified"
    assert result["raw_capture_inputs_unchanged"]
    review = Path(result["review_history"])
    assert json.loads((review / "original-report.json").read_text()) == old_report
    assert json.loads((run / "report.json").read_text())["statuses"]["walking"] == "verified"
    assert (review / "receipt.json").exists()
    assert reassess._capture_manifest(run) == {
        **before,
        "report.json": sha((run / "report.json").read_bytes()),
        "report.html": sha((run / "report.html").read_bytes()),
    }
    with pytest.raises(ValueError, match="Expected original warmup-26"):
        reassess.reassess(run)


def test_windows_crlf_reports_are_accepted_and_kept_crlf(old_failed_capture):
    run, _ = old_failed_capture
    for name in ("report.json", "report.html"):
        target = run / name
        normalized = target.read_bytes().replace(b"\r\n", b"\n")
        target.write_bytes(normalized.replace(b"\n", b"\r\n"))
    before = reassess._capture_manifest(run)
    assert reassess.reassess(run)["status"] == "ready_for_explicit_reassessment"
    assert reassess._capture_manifest(run) == before
    result = reassess.reassess(run, apply=True)
    review = Path(result["review_history"])
    for name in ("report.json", "report.html"):
        new_bytes = (run / name).read_bytes()
        assert b"\r\n" in new_bytes
        assert b"\n" not in new_bytes.replace(b"\r\n", b"")
        old_bytes = (review / ("original-" + name)).read_bytes()
        assert sha(old_bytes) == before[name]


def test_dry_run_refuses_different_metadata_without_reclassification(
    old_failed_capture, monkeypatch
):
    run, _ = old_failed_capture
    original = (run / "report.json").read_bytes()
    real = reassess.graphics_report.validate

    def corrupt_live(path, out, *, write_visuals=True):
        real(path, out, write_visuals=write_visuals)
        out["provenance"]["warmup"] = 31

    monkeypatch.setattr(reassess.graphics_report, "validate", corrupt_live)
    with pytest.raises(ValueError, match="changed more than the walking gate"):
        reassess.reassess(run, apply=True)
    assert (run / "report.json").read_bytes() == original
    assert not (run.parent.parent / "ReviewHistory").exists()


def test_postflight_failure_restores_original_verdict(old_failed_capture, monkeypatch):
    run, _ = old_failed_capture
    original = (run / "report.json").read_bytes()
    original_html = (run / "report.html").read_bytes()

    def cannot_load(path):
        raise ValueError("synthetic decoder fault")

    monkeypatch.setattr(reassess, "load_verified_window", cannot_load)
    with pytest.raises(ValueError, match="synthetic decoder fault"):
        reassess.reassess(run, apply=True)
    assert (run / "report.json").read_bytes() == original
    assert (run / "report.html").read_bytes() == original_html
    assert (run.parent.parent / "ReviewHistory").exists()


def test_missing_original_capture_bytes_rejected(old_failed_capture):
    run, _ = old_failed_capture
    (run / "slot-copy.mss").unlink()
    with pytest.raises(ValueError, match="79 complete source"):
        reassess.reassess(run, apply=True)
    assert not (run.parent.parent / "ReviewHistory").exists()
