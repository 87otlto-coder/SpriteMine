"""Synthetic-only tests: long SMB3 timelines, source integrity and offline previews.

No copyrighted ROM, emulator capture or Mario graphics are in these fixtures.
"""

from __future__ import annotations

import hashlib
import json
from argparse import Namespace
from pathlib import Path

import pytest
from PIL import Image

from research.mesence import animation_archive, animation_preview
from research.mesence import animation_timeline, animation_windows


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _frame(warmup: int, directory: Path) -> tuple[dict, Image.Image]:
    """Invent two tiny synthetic RGBA patterns, including an A/B/A/B sequence."""
    index = warmup - 8
    pose_a = index < 5 or 11 <= index < 17
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    image.putpixel((4 if pose_a else 8, 5), (110, 90, 40, 255))
    image.putpixel((6, 7), (220, 180, 80, 255))
    frame = {
        "status": "verified_captured_frame_subset",
        "provenance": "decoded_from_rom_mapped_8x16_OAM",
        "frame_count": 448385 + index,
        "start_master_clock": 400000 + index * 29780,
        "end_master_clock": 410000 + index * 29780,
        "run_dir": str(directory.resolve()),
        "input_plan": "right",
        "warmup": warmup,
        "restore": "restore synthetic 123",
        "controller_bus_sha256": "1" * 64,
        "ppu_start_sha256": "2" * 64,
        "oam_start_sha256": "3" * 64,
        "palette_start_sha256": "4" * 64,
        "rendered_rgb_sha256": "5" * 64,
        "background_rgb_sha256": "6" * 64,
        "oam_group": [10, 11],
        "position_x": 128,
        "position_y": 98,
        "width": 16,
        "height": 16,
        "opaque_pixels": 2,
        "transparent_pixels": 254,
        "tile_ids": [7, 5] if pose_a else [3, 1],
        "flip_horizontal": [True, True],
        "flip_vertical": [False, False],
        "sprite_palette_slots": [0, 0],
        "source_rom_tile_offsets": [[0, 16], [32, 48]],
        "rgba_sha256": _sha(image.tobytes()),
    }
    return {
        "frame": frame,
        "source": {
            "slot_sha256": _SLOT_SHA,
            "probe_sha256": "b" * 64,
            "rom_sha256": "c" * 64,
            "emulator_sha256": "d" * 64,
            "emulator_version": "fake MesenCE test build",
            "plan": "right",
            "start_pulse": False,
            "warmup": warmup,
        },
    }, image


_SLOT_SHA = ""


@pytest.fixture
def synthetic_archive(tmp_path, monkeypatch):
    root = tmp_path / "ROMMAGE"
    runs = root / "FIXTURE" / "SMB3" / "GraphicsValidation"
    animations = root / "FIXTURE" / "SMB3" / "Animations"
    runs.mkdir(parents=True)
    animations.mkdir()
    slot = tmp_path / "slot1.mss"
    slot.write_bytes(b"synthetic immutable slot bytes")
    global _SLOT_SHA
    _SLOT_SHA = _sha(slot.read_bytes())

    records = {}
    paths = []
    for warmup in range(8, 26):
        directory = runs / f"anim-right-w{warmup}-synthetic"
        directory.mkdir()
        paths.append(directory)
        records[directory.resolve()] = _frame(warmup, directory)
    def load(path):
        return records[Path(path).resolve()]
    monkeypatch.setattr(animation_timeline, "load_verified_window", load)
    monkeypatch.setattr(animation_windows, "load_verified_window", load)
    original_dir = animations / "right-original"
    animation_timeline.assemble_timeline(paths[:12], original_dir)
    return {
        "root": root, "slot": slot, "paths": paths,
        "records": records, "timeline": original_dir / "timeline.json",
        "animations": animations,
    }


def test_original_12_frame_archive_and_hold_summary(synthetic_archive):
    data = animation_archive.read_verified_timeline(synthetic_archive["timeline"])
    assert data["frame_count"] == 12
    assert data["unique_visual_frame_count"] == 2
    assert [(r["duration_frames"], r["first_emulator_frame"]) for r in data["visual_holds"]] == [
        (5, 448385), (6, 448390), (1, 448396)
    ]
    assert animation_archive.verified_timeline_runs(synthetic_archive["timeline"]) == (
        synthetic_archive["paths"][:12]
    )


def test_long_stitched_18_frame_timeline_retains_every_event(synthetic_archive):
    source = synthetic_archive
    result = animation_timeline.assemble_timeline(
        source["paths"], source["animations"] / "extended"
    )
    assert result["frame_count"] == 18
    assert result["unique_visual_frame_count"] == 2
    assert [h["duration_frames"] for h in result["visual_holds"]] == [5, 6, 6, 1]
    assert result["first_emulator_frame"] == 448385
    assert result["last_emulator_frame"] == 448402
    assert len(list((source["animations"] / "extended").glob("frame_*.png"))) == 18
    assert len(animation_archive.verified_timeline_runs(
        source["animations"] / "extended" / "timeline.json"
    )) == 18


@pytest.mark.parametrize("change", ["png", "sheet", "timeline_gap", "duplicate_warmup", "clock"])
def test_corrupt_archive_rejected_before_resume(synthetic_archive, change):
    source = synthetic_archive
    timeline = source["timeline"]
    data = json.loads(timeline.read_text())
    if change == "png":
        (timeline.parent / data["frames"][1]["png_file"]).write_bytes(b"damaged")
    elif change == "sheet":
        (timeline.parent / "spritesheet.png").write_bytes(b"damaged")
    elif change == "timeline_gap":
        data["frames"][3]["frame_count"] += 1
    elif change == "duplicate_warmup":
        data["frames"][4]["warmup"] = data["frames"][3]["warmup"]
    elif change == "clock":
        data["frames"][2]["start_master_clock"] = data["frames"][1]["start_master_clock"]
    if change not in ("png", "sheet"):
        timeline.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises((ValueError, OSError)):
        animation_archive.verified_timeline_runs(timeline)


def test_manifest_source_metadata_tampering_rejected(synthetic_archive):
    timeline = synthetic_archive["timeline"]
    data = json.loads(timeline.read_text())
    data["frames"][0]["tile_ids"] = [99, 99]
    timeline.write_text(json.dumps(data), encoding="utf-8")
    # File hashes still match; independent replay-derived metadata must not.
    assert animation_archive.read_verified_timeline(timeline)["frame_count"] == 12
    with pytest.raises(ValueError, match="disagrees"):
        animation_archive.verified_timeline_runs(timeline)


def test_archive_source_mismatch_rejected(synthetic_archive):
    source = synthetic_archive
    source["records"][source["paths"][5].resolve()][0]["source"]["probe_sha256"] = "e" * 64
    with pytest.raises(ValueError):
        animation_archive.verified_timeline_runs(source["timeline"])


def test_resume_captures_only_new_six_and_assembles_all_eighteen(
    synthetic_archive, monkeypatch
):
    source = synthetic_archive
    args = Namespace(
        root=source["root"], slot=source["slot"], rom=None,
        plan="right", first_warmup=20, count=6,
        start_pulse=False, reuse_run=[], reuse_timeline=source["timeline"],
    )
    new_warmups = []
    def capture(namespace, run):
        new_warmups.append(namespace.warmup)
        source["records"][run.resolve()] = _frame(namespace.warmup, run)
    monkeypatch.setattr(animation_windows.graphics_harness, "capture", capture)
    monkeypatch.setattr(animation_windows.graphics_report, "publish", lambda run: 0)
    old_bytes = source["timeline"].read_bytes()
    result = animation_windows.capture_animation(args)
    assert new_warmups == [20, 21, 22, 23, 24, 25]
    assert result["frame_count"] == 18
    assert len(result["reused_run_dirs"]) == 12
    assert len(result["new_run_dirs"]) == 6
    assert source["timeline"].read_bytes() == old_bytes
    assert source["slot"].read_bytes() == b"synthetic immutable slot bytes"
    assert animation_archive.read_verified_timeline(Path(result["timeline_json"]))["frame_count"] == 18


def test_wrong_slot_fails_before_emulator(synthetic_archive, monkeypatch):
    source = synthetic_archive
    source["slot"].write_bytes(b"not the original slot")
    args = Namespace(
        root=source["root"], slot=source["slot"], rom=None,
        plan="right", first_warmup=20, count=2, start_pulse=False,
        reuse_run=[], reuse_timeline=source["timeline"]
    )
    monkeypatch.setattr(animation_windows.graphics_harness, "capture",
                        lambda *_: pytest.fail("Emulator must not start"))
    with pytest.raises(ValueError, match="different slot-1 state"):
        animation_windows.capture_animation(args)


def test_interrupted_capture_preserves_verified_archive(synthetic_archive, monkeypatch):
    source = synthetic_archive
    args = Namespace(
        root=source["root"], slot=source["slot"], rom=None,
        plan="right", first_warmup=20, count=2, start_pulse=False,
        reuse_run=[], reuse_timeline=source["timeline"]
    )
    seen = []
    def capture(namespace, run):
        seen.append(namespace.warmup)
        if namespace.warmup == 21:
            raise RuntimeError("synthetic emulator failure")
        (run / "private-diagnostic.txt").write_text("mock capture")
    monkeypatch.setattr(animation_windows.graphics_harness, "capture", capture)
    monkeypatch.setattr(animation_windows.graphics_report, "publish", lambda *_: 0)
    original = source["timeline"].read_bytes()
    with pytest.raises(ValueError, match="Capture failed at warmup 21"):
        animation_windows.capture_animation(args)
    assert seen == [20, 21]
    assert original == source["timeline"].read_bytes()
    assert not list(source["animations"].glob("right-8-21-*"))
    assert len(list((source["root"] / "FIXTURE" / "SMB3" / "GraphicsValidation").glob("anim-right-w2*"))) == 2


def test_preview_html_uses_verified_files_and_refuses_overwrite(synthetic_archive):
    timeline = synthetic_archive["timeline"]
    output = animation_preview.write_preview(timeline)
    page = output.read_text(encoding="utf-8")
    assert "frame_000_448385.png" in page
    assert "Play preview" in page
    assert "milliseconds unverified" in page or "loop and milliseconds unverified" in page
    assert "image-rendering: pixelated" in page
    assert "http://" not in page and "https://" not in page
    with pytest.raises(FileExistsError):
        animation_preview.write_preview(timeline)
    with pytest.raises(ValueError, match="beside"):
        animation_preview.write_preview(timeline, timeline.parent.parent / "elsewhere.html")


def test_interrupted_batch_can_reuse_successful_partial_run(synthetic_archive, monkeypatch):
    source = synthetic_archive
    old = source["timeline"]
    root = source["root"]
    slot = source["slot"]
    archive_parent = root / "FIXTURE" / "SMB3" / "GraphicsValidation"
    seen = []

    def first_attempt(namespace, run):
        seen.append(namespace.warmup)
        if namespace.warmup == 21:
            raise RuntimeError("simulated MesenCE interruption")
        source["records"][run.resolve()] = _frame(namespace.warmup, run)

    monkeypatch.setattr(animation_windows.graphics_harness, "capture", first_attempt)
    monkeypatch.setattr(animation_windows.graphics_report, "publish", lambda *_: 0)
    first_args = Namespace(
        root=root, rom=None, slot=slot, plan="right", first_warmup=20,
        count=2, start_pulse=False, reuse_run=[], reuse_timeline=old,
    )
    with pytest.raises(ValueError, match="Capture failed at warmup 21"):
        animation_windows.capture_animation(first_args)
    assert seen == [20, 21]
    successful, = list(archive_parent.glob("anim-right-w20-*"))
    prior_data = old.read_bytes()

    def second_attempt(namespace, run):
        seen.append(namespace.warmup)
        source["records"][run.resolve()] = _frame(namespace.warmup, run)

    monkeypatch.setattr(animation_windows.graphics_harness, "capture", second_attempt)
    resume_args = Namespace(
        root=root, rom=None, slot=slot, plan="right", first_warmup=21,
        count=2, start_pulse=False, reuse_run=[successful], reuse_timeline=old,
    )
    result = animation_windows.capture_animation(resume_args)
    assert seen == [20, 21, 21, 22]
    assert result["frame_count"] == 15
    assert len(result["reused_run_dirs"]) == 13
    assert len(result["new_run_dirs"]) == 2
    assert old.read_bytes() == prior_data
    assert animation_archive.read_verified_timeline(Path(result["timeline_json"]))["frame_count"] == 15
