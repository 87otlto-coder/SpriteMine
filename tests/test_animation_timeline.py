"""Synthetic-only tests of immutable A/B/A animation timeline assembly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from research.mesence import animation_timeline
from research.mesence import graphics_report
from test_graphics_harness import run as generated_run


def test_revalidate_real_synthetic_aba_run_read_only(generated_run):
    assert graphics_report.publish(generated_run) == 0
    report_path = generated_run / "report.json"
    report_before = report_path.read_bytes()
    (generated_run / "region.png").unlink()
    (generated_run / "A.png").unlink()
    result, image = animation_timeline.load_verified_window(generated_run)
    assert image.mode == "RGBA"
    assert image.size == (16, 16)
    assert result["frame"]["status"] == "verified_captured_frame_subset"
    assert result["frame"]["opaque_pixels"] + result["frame"]["transparent_pixels"] == 256
    assert result["frame"]["oam_group"] == [10, 11]
    assert result["frame"]["source_rom_tile_offsets"]
    # Running the offline builder must never regenerate or alter archived output.
    assert report_path.read_bytes() == report_before
    assert not (generated_run / "region.png").exists()
    assert not (generated_run / "A.png").exists()


def test_archive_metadata_change_is_rejected(generated_run):
    assert graphics_report.publish(generated_run) == 0
    source = generated_run / "report.json"
    info = json.loads(source.read_text())
    info["provenance"]["probe_sha256"] = "f" * 64
    source.write_text(json.dumps(info))
    with pytest.raises(ValueError, match="Archived A/B/A evidence changed"):
        animation_timeline.load_verified_window(generated_run)


def _mock_records(tmp_path, monkeypatch, *, count=3, same_images=False):
    root = tmp_path / "FIXTURE"
    root.mkdir()
    paths = [(root / f"window{i}") for i in range(count)]
    for p in paths:
        p.mkdir()
    records = {}
    for i, path in enumerate(paths):
        image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        image.putpixel((0, 0), (181, 49, 32, 255))
        if i and not same_images:
            image.putpixel((1, 0), (254, 204, 197, 255))
        sha = hashlib.sha256(image.tobytes()).hexdigest()
        frame = {
            "frame_count": 448385 + i,
            "warmup": 8 + i,
            "start_master_clock": 466140497 + i * 89342,
            "end_master_clock": 466141000 + i * 89342,
            "restore": "restore 448316 466140497",
            "run_dir": str(path),
            "rgba_sha256": sha,
        }
        source = {
            "slot_sha256": "a" * 64,
            "probe_sha256": "b" * 64,
            "rom_sha256": "c" * 64,
            "emulator_sha256": "d" * 64,
            "emulator_version": "test",
            "plan": "right",
            "start_pulse": False,
            "warmup": 8 + i,
        }
        records[path.resolve()] = ({"frame": frame, "source": source}, image)
    monkeypatch.setattr(
        animation_timeline, "load_verified_window",
        lambda path: records[Path(path).resolve()],
    )
    return paths, records, root


def test_timeline_exports_preserve_every_frame_and_provenance(tmp_path, monkeypatch):
    paths, records, root = _mock_records(tmp_path, monkeypatch)
    target = root / "Animations" / "walk-unique"
    result = animation_timeline.assemble_timeline(paths[::-1], target)
    assert result["result"] == "contiguous_verified_OAM_frame_timeline"
    assert result["frame_count"] == 3
    assert result["first_emulator_frame"] == 448385
    assert result["last_emulator_frame"] == 448387
    assert [f["duration_frames"] for f in result["frames"]] == [1, 1, 1]
    assert [f["delta_master_clock_to_next"] for f in result["frames"]] == [
        89342, 89342, None
    ]
    assert result["timing"]["nominal_fps"] is None
    assert result["timing"]["ms_per_frame"] is None
    assert result["frames"][1]["identical_to_previous_frame"] is False
    assert result["frames"][2]["identical_to_previous_frame"] is True
    assert [f["timeline_index"] for f in result["frames"]] == [0, 1, 2]
    assert len(list(target.glob("frame_*.png"))) == 3
    with Image.open(target / "spritesheet.png") as sheet:
        assert sheet.size == (48, 16)
        assert sheet.mode == "RGBA"
    assert json.loads((target / "timeline.json").read_text()) == result
    for frame in result["frames"]:
        assert len(frame["png_sha256"]) == 64
        assert frame["rgba_sha256"]
    with pytest.raises(FileExistsError, match="Refusing"):
        animation_timeline.assemble_timeline(paths, target)


def test_identical_held_frames_remain_distinct_events(tmp_path, monkeypatch):
    paths, _, root = _mock_records(
        tmp_path, monkeypatch, same_images=True
    )
    result = animation_timeline.assemble_timeline(
        paths, root / "Animations" / "hold", write=False
    )
    assert result["frame_count"] == 3
    assert [f["identical_to_previous_frame"] for f in result["frames"]] == [
        False, True, True
    ]
    assert all(f["duration_frames"] == 1 for f in result["frames"])
    assert not (root / "Animations" / "hold").exists()


@pytest.mark.parametrize("field", [
    "frame_gap", "warmup_gap", "restore", "source_hash", "clock"
])
def test_rejects_discontinuous_or_different_replays(tmp_path, monkeypatch, field):
    paths, records, root = _mock_records(tmp_path, monkeypatch)
    altered = records[paths[1].resolve()][0]
    if field == "frame_gap":
        altered["frame"]["frame_count"] += 3
    elif field == "warmup_gap":
        altered["frame"]["warmup"] += 5
    elif field == "restore":
        altered["frame"]["restore"] = "restore 5 6"
    elif field == "source_hash":
        altered["source"]["slot_sha256"] = "5" * 64
    else:
        altered["frame"]["start_master_clock"] = 1
    with pytest.raises(ValueError):
        animation_timeline.assemble_timeline(
            paths, root / "Animations" / "should-not-exist"
        )
    assert not (root / "Animations" / "should-not-exist").exists()


def test_rejects_duplicate_runs_and_input_output_overlap(tmp_path, monkeypatch):
    paths, _, root = _mock_records(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="Duplicate"):
        animation_timeline.assemble_timeline(
            [paths[0], paths[0]], root / "Animations" / "duplicates"
        )
    with pytest.raises(ValueError, match="archived"):
        animation_timeline.assemble_timeline(paths, paths[0] / "output")
    with pytest.raises(ValueError, match="at least two"):
        animation_timeline.assemble_timeline(
            [paths[0]], root / "Animations" / "short"
        )
