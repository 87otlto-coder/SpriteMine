"""Synthetic MesenCE portable-startup and capture evidence relocation tests.

No real ROM, state, or emulator executable is included in public fixtures.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from research.mesence import animation_archive, animation_timeline
from research.mesence import graphics_harness
from test_animation_resume import synthetic_archive  # shared synthetic capture fixture


def test_portable_mesen_reuses_content_addressed_private_runtime(tmp_path):
    tool_dir = tmp_path / "TOOLS" / "MesenCE"
    tool_dir.mkdir(parents=True)
    exe = tool_dir / "Mesen.exe"
    exe.write_bytes(b"synthetic emulator, never real game data")
    settings = tmp_path / "TOOLS" / "PrivateProfile" / "settings.json"
    settings.parent.mkdir()
    settings.write_text('{"preferences":{"singleInstance":false}}', encoding="utf-8")
    runs_parent = tmp_path / "FIXTURE" / "SMB3" / "GraphicsValidation"
    runs_parent.mkdir(parents=True)
    a, b = runs_parent / "a", runs_parent / "b"
    a.mkdir()
    b.mkdir()

    original_exe, original_settings = exe.read_bytes(), settings.read_bytes()
    first_exe, exe_hash, settings_hash = graphics_harness.prepare_portable_mesen(exe, settings, a)
    second_exe, second_exe_hash, second_settings_hash = graphics_harness.prepare_portable_mesen(exe, settings, b)
    assert first_exe == second_exe
    assert first_exe.parent.parent.name == "EmulatorRuntime"
    assert first_exe.read_bytes() == original_exe
    assert (first_exe.parent / "settings.json").read_bytes() == original_settings
    assert exe_hash == second_exe_hash == hashlib.sha256(original_exe).hexdigest()
    assert settings_hash == second_settings_hash == hashlib.sha256(original_settings).hexdigest()
    assert exe.read_bytes() == original_exe and settings.read_bytes() == original_settings


@pytest.mark.parametrize("invalid", ["not_json", "json_array", "wrong_name"])
def test_invalid_portable_settings_do_not_create_runtime(tmp_path, invalid):
    root = tmp_path / "FIXTURE" / "SMB3" / "GraphicsValidation"
    run = root / "test-run"
    run.mkdir(parents=True)
    exe = tmp_path / "Mesen.exe"
    exe.write_bytes(b"synthetic")
    config = tmp_path / ("config.json" if invalid == "wrong_name" else "settings.json")
    config.write_text("[" if invalid == "not_json" else "[]" if invalid == "json_array" else "{}")
    with pytest.raises(ValueError):
        graphics_harness.prepare_portable_mesen(exe, config, run)
    assert not (tmp_path / "FIXTURE" / "SMB3" / "EmulatorRuntime").exists()


def test_tampered_cached_runtime_is_rejected(tmp_path):
    run = tmp_path / "FIXTURE" / "SMB3" / "GraphicsValidation" / "run"
    run.mkdir(parents=True)
    exe = tmp_path / "Mesen.exe"
    exe.write_bytes(b"synthetic")
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    copied, _, _ = graphics_harness.prepare_portable_mesen(exe, settings, run)
    copied.write_bytes(b"tampered runtime")
    with pytest.raises(ValueError, match="changed"):
        graphics_harness.prepare_portable_mesen(exe, settings, run)
    assert exe.read_bytes() == b"synthetic"


def test_rehome_archive_preserves_original_manifest_and_revalidates_copies(
    synthetic_archive, tmp_path, monkeypatch
):
    """Private evidence may move C: -> F: while original timeline stays untouched."""
    source = synthetic_archive
    original_timeline = source["timeline"]
    original_bytes = original_timeline.read_bytes()
    target_runs = tmp_path / "SECOND_ROOT" / "FIXTURE" / "SMB3" / "GraphicsValidation"
    target_runs.mkdir(parents=True)

    for old_path in source["paths"][:12]:
        new_path = target_runs / old_path.name
        shutil.copytree(old_path, new_path)
        info, image = source["records"][old_path.resolve()]
        migrated = copy.deepcopy(info)
        migrated["frame"]["run_dir"] = str(new_path.resolve())
        source["records"][new_path.resolve()] = (migrated, image)

    runs = animation_archive.verified_timeline_runs(
        original_timeline, runs_parent_override=target_runs
    )
    assert len(runs) == 12
    assert runs[0].parent == target_runs.resolve()
    assert original_timeline.read_bytes() == original_bytes
    # The original absolute run_dir cannot be silently used for the copy.
    assert [str(r) for r in runs] != [
        f["run_dir"] for f in json.loads(original_bytes)["frames"]
    ]


def test_rehome_corrupted_capture_rejected(synthetic_archive, tmp_path):
    source = synthetic_archive
    target_runs = tmp_path / "RELOCATED" / "FIXTURE" / "SMB3" / "GraphicsValidation"
    target_runs.mkdir(parents=True)
    for old in source["paths"][:12]:
        relocated = target_runs / old.name
        relocated.mkdir()
        info, image = source["records"][old.resolve()]
        new_info = copy.deepcopy(info)
        new_info["frame"]["run_dir"] = str(relocated.resolve())
        source["records"][relocated.resolve()] = (new_info, image)
    # The independent decoder reports the copied archive's modified tile
    # source. Manifest must not be normalized except for absolute run_dir.
    source["records"][(target_runs / source["paths"][1].name).resolve()][0]["frame"]["tile_ids"] = [255, 255]
    with pytest.raises(ValueError, match="disagrees"):
        animation_archive.verified_timeline_runs(
            source["timeline"], runs_parent_override=target_runs
        )


def test_rehome_rejects_foreign_or_unsafe_archived_location(synthetic_archive, tmp_path):
    source = synthetic_archive
    destination = tmp_path / "SAFE" / "FIXTURE" / "SMB3" / "GraphicsValidation"
    destination.mkdir(parents=True)
    original = source["timeline"]
    d = json.loads(original.read_text())
    d["frames"][0]["run_dir"] = "C:\\arbitrary\\outside\\not-captures"
    original.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="Untrusted"):
        animation_archive.verified_timeline_runs(original, runs_parent_override=destination)

def test_relocated_resume_creates_new_receipt_without_changing_source(
    synthetic_archive, tmp_path, monkeypatch
):
    from argparse import Namespace
    from research.mesence import animation_windows
    from test_animation_resume import _frame

    source = synthetic_archive
    source_timeline = source["timeline"]
    original_bytes = source_timeline.read_bytes()
    original_sha = hashlib.sha256(original_bytes).hexdigest()
    destination_root = tmp_path / "NEW_ROOT"
    destination_runs = destination_root / "FIXTURE" / "SMB3" / "GraphicsValidation"
    destination_runs.mkdir(parents=True)
    (destination_root / "FIXTURE" / "SMB3" / "Animations").mkdir()
    for old in source["paths"][:12]:
        dest = destination_runs / old.name
        shutil.copytree(old, dest)
        old_info, image = source["records"][old.resolve()]
        new_info = copy.deepcopy(old_info)
        new_info["frame"]["run_dir"] = str(dest.resolve())
        source["records"][dest.resolve()] = (new_info, image)

    settings = destination_root / "TOOLS" / "MesenCE" / "Profile" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text('{"preferences":{}}', encoding="utf-8")
    captured = []
    def fake_capture(args, run):
        captured.append((args.warmup, args.emulator_settings))
        source["records"][run.resolve()] = _frame(args.warmup, run)
    monkeypatch.setattr(animation_windows.graphics_harness, "capture", fake_capture)
    monkeypatch.setattr(animation_windows.graphics_report, "publish", lambda _: 0)
    args = Namespace(
        root=destination_root, rom=None, slot=source["slot"],
        plan="right", first_warmup=20, count=2, start_pulse=False,
        reuse_timeline=source_timeline, rehome_archive=True,
        reuse_run=[], emulator_settings=settings,
    )
    result = animation_windows.capture_animation(args)
    assert result["frame_count"] == 14
    assert result["relocated_source_runs"] is True
    assert captured == [(20, settings.resolve()), (21, settings.resolve())]
    receipt = json.loads((Path(result["timeline_json"]).parent / "continuation.json").read_text())
    assert receipt["source_timeline_sha256"] == original_sha
    assert receipt["source_timeline_frame_count"] == 12
    assert receipt["portable_settings_sha256"] == hashlib.sha256(settings.read_bytes()).hexdigest()
    assert source_timeline.read_bytes() == original_bytes
    assert animation_archive.verified_timeline_runs(
        Path(result["timeline_json"])
    )


def test_optional_emulator_settings_frame_hash_validated(synthetic_archive):
    source = synthetic_archive
    info, _ = source["records"][source["paths"][12].resolve()]
    info["frame"]["emulator_portable_mode"] = True
    info["frame"]["emulator_settings_sha256"] = "e" * 64
    target = source["animations"] / "portable-source"
    animation_timeline.assemble_timeline(source["paths"][:14], target)
    timeline = target / "timeline.json"
    assert animation_archive.read_verified_timeline(timeline)["frames"][12]["emulator_portable_mode"] is True
    data = json.loads(timeline.read_text())
    data["frames"][12]["emulator_settings_sha256"] = "not-a-hash"
    timeline.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        animation_archive.read_verified_timeline(timeline)
