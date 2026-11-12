"""Bounded animation capture orchestration with mocked Windows emulator processes."""
from __future__ import annotations

from argparse import Namespace

import pytest

from research.mesence import animation_windows


def _args(tmp_path, *, plan="right", count=3, first=8, start=False):
    root = tmp_path / "ROMMAGE"
    (root / "FIXTURE").mkdir(parents=True)
    slot = tmp_path / "Super Mario Bros. 3_1.mss"
    slot.write_bytes(b"immutable private slot fixture")
    return Namespace(
        root=root,
        rom=None,
        slot=slot,
        plan=plan,
        count=count,
        first_warmup=first,
        start_pulse=start,
    )


def test_capture_three_consecutive_windows_without_mutating_slot(
    tmp_path, monkeypatch
):
    args = _args(tmp_path)
    calls = []

    def fake_capture(namespace, run):
        calls.append((namespace.warmup, namespace.plan, str(run)))
        (run / "captured.txt").write_text(str(namespace.warmup))

    def fake_publish(run):
        assert (run / "captured.txt").exists()
        return 0

    def fake_timeline(runs, target):
        assert [int((run / "captured.txt").read_text()) for run in runs] == [8, 9, 10]
        assert "Animations" in str(target)
        assert target.name.startswith("right-8-10-")
        return {
            "result": "contiguous_verified_OAM_frame_timeline",
            "source_slot_sha256": animation_windows.graphics_harness.digest(args.slot),
            "frame_count": 3,
            "first_emulator_frame": 448385,
            "last_emulator_frame": 448387,
        }

    monkeypatch.setattr(animation_windows.graphics_harness, "capture", fake_capture)
    monkeypatch.setattr(animation_windows.graphics_report, "publish", fake_publish)
    monkeypatch.setattr(animation_windows, "assemble_timeline", fake_timeline)
    original = args.slot.read_bytes()
    result = animation_windows.capture_animation(args)
    assert result["status"] == "validated_local_A_B_A_sequence"
    assert result["original_slot_unchanged"] is True
    assert [row[0] for row in calls] == [8, 9, 10]
    assert all(row[1] == "right" for row in calls)
    assert args.slot.read_bytes() == original


@pytest.mark.parametrize("overrides", [
    {"count": 1},
    {"count": 13},
    {"first": 120, "count": 3},
    {"plan": "sprint"},
    {"start": True},
])
def test_invalid_requests_fail_before_emulator_launch(tmp_path, monkeypatch, overrides):
    args = _args(tmp_path, **overrides)
    monkeypatch.setattr(
        animation_windows.graphics_harness,
        "capture", lambda *_: pytest.fail("Unexpected emulator execution")
    )
    with pytest.raises(ValueError):
        animation_windows.capture_animation(args)


def test_changed_slot_is_rejected_between_windows(tmp_path, monkeypatch):
    args = _args(tmp_path)
    called = []

    def fake_capture(namespace, run):
        called.append(namespace.warmup)
        args.slot.write_bytes(b"changed state during experiment")

    monkeypatch.setattr(animation_windows.graphics_harness, "capture", fake_capture)
    monkeypatch.setattr(animation_windows.graphics_report, "publish", lambda run: 0)
    with pytest.raises(ValueError, match="Original slot backing file changed"):
        animation_windows.capture_animation(args)
    assert called == [8]


def test_graphics_gate_failure_preserves_private_run_and_stops(tmp_path, monkeypatch):
    args = _args(tmp_path)
    called = []

    def capture(namespace, run):
        called.append(namespace.warmup)
        (run / "diagnostic.txt").write_text("failed synthetic run")

    monkeypatch.setattr(animation_windows.graphics_harness, "capture", capture)
    monkeypatch.setattr(animation_windows.graphics_report, "publish", lambda run: 3)
    with pytest.raises(ValueError, match="Graphics verification failed"):
        animation_windows.capture_animation(args)
    assert called == [8]
    evidence = list((args.root / "FIXTURE" / "SMB3" / "GraphicsValidation").glob("*"))
    assert len(evidence) == 1
    assert (evidence[0] / "diagnostic.txt").exists()


def _previous_windows(args, *, start=8, count=3):
    """Local paths representing existing A/B/A evidence; full verifier mocked."""
    archive = args.root / "FIXTURE" / "SMB3" / "GraphicsValidation"
    archive.mkdir(parents=True, exist_ok=True)
    paths = []
    reports = {}
    original_slot_sha = animation_windows.graphics_harness.digest(args.slot)
    for n in range(start, start + count):
        directory = archive / f"anim-right-w{n}-prior"
        directory.mkdir()
        paths.append(directory)
        reports[directory.resolve()] = {
            "frame": {
                "run_dir": str(directory.resolve()),
                "warmup": n,
                "frame_count": 448377 + n,
            },
            "source": {"slot_sha256": original_slot_sha, "plan": "right"},
        }
    return paths, reports


def test_reuses_3_verified_windows_and_captures_only_next_2(tmp_path, monkeypatch):
    args = _args(tmp_path, first=11, count=2)
    paths, reports = _previous_windows(args)
    args.reuse_run = paths
    monkeypatch.setattr(
        animation_windows, "load_verified_window",
        lambda p: (reports[p.resolve()], None)
    )
    captured = []

    def fake_capture(namespace, run):
        captured.append(namespace.warmup)
        (run / "captured.txt").write_text(str(namespace.warmup))

    def fake_timeline(runs, output):
        assert len(runs) == 5
        assert [p.resolve() for p in runs[:3]] == [p.resolve() for p in paths]
        assert [int((p / "captured.txt").read_text()) for p in runs[3:]] == [11, 12]
        assert output.name.startswith("right-8-12-")
        return {
            "result": "contiguous_verified_OAM_frame_timeline",
            "source_slot_sha256": animation_windows.graphics_harness.digest(args.slot),
            "frame_count": 5,
            "first_emulator_frame": 448385,
            "last_emulator_frame": 448389,
        }

    monkeypatch.setattr(animation_windows.graphics_harness, "capture", fake_capture)
    monkeypatch.setattr(animation_windows.graphics_report, "publish", lambda run: 0)
    monkeypatch.setattr(animation_windows, "assemble_timeline", fake_timeline)
    result = animation_windows.capture_animation(args)
    assert captured == [11, 12]
    assert len(result["reused_run_dirs"]) == 3
    assert len(result["new_run_dirs"]) == 2
    assert result["frame_count"] == 5
    assert result["original_slot_unchanged"] is True


@pytest.mark.parametrize("what", [
    "gap", "wrong_slot", "wrong_plan", "over_limit", "duplicate",
])
def test_invalid_reused_windows_fail_before_new_capture(tmp_path, monkeypatch, what):
    args = _args(tmp_path, first=11, count=2)
    paths, reports = _previous_windows(args)
    args.reuse_run = paths
    if what == "gap":
        reports[paths[1].resolve()]["frame"]["warmup"] = 22
    elif what == "wrong_slot":
        reports[paths[1].resolve()]["source"]["slot_sha256"] = "f" * 64
    elif what == "wrong_plan":
        reports[paths[1].resolve()]["source"]["plan"] = "jump"
    elif what == "over_limit":
        args.count = 10
    elif what == "duplicate":
        args.reuse_run.append(paths[0])

    monkeypatch.setattr(
        animation_windows, "load_verified_window",
        lambda p: (reports[p.resolve()], None)
    )
    monkeypatch.setattr(
        animation_windows.graphics_harness, "capture",
        lambda *x: pytest.fail("Should not start emulator when reuse is invalid"),
    )
    with pytest.raises(ValueError):
        animation_windows.capture_animation(args)
