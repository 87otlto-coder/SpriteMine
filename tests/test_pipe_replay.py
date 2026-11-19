from hashlib import sha256

import pytest

from research.mesence.pipe_replay import common_signature, event_window, signature_differences
from research.mesence.verify_pipe_mask import stable_chr


def test_neutrality_signature_includes_controller_and_rendered_evidence(tmp_path):
    common = ("trace.tsv", "controller.tsv", "1-start-tiles.bin", "1-end-rgb.bin")
    detailed = ("events.tsv", "1-start-oam.bin", "checkpoint.mss",
                "bg-0001-tiles.bin", "bg-0001-pattern.bin",
                "bg-0002-attribute.bin", "background-staging.tsv")
    for name in common + detailed:
        (tmp_path / name).write_bytes(name.encode())
    assert common_signature(tmp_path) == {name: sha256(name.encode()).hexdigest() for name in common}
    (tmp_path / "controller.tsv").write_bytes(b"changed")
    assert common_signature(tmp_path)["controller.tsv"] == sha256(b"changed").hexdigest()


def test_event_window_tracks_first_pipe_and_following_junction():
    trace = [
        "1\t100\t0\t0\t0\t0\t0\t1",
        "2\t110\t0\t0\t0\t0\t14\t0",
        "3\t123\t0\t0\t0\t0\t0\t1",
        "4\t200\t0\t0\t0\t0\t0\t0",
    ]
    assert event_window(trace) == (107, 163)
    with pytest.raises(ValueError, match="no junction"):
        event_window(trace[:2])
    with pytest.raises(ValueError, match="no pipe"):
        event_window(trace[:1])


def test_pipe_fetch_mapping_rejects_early_chr_changes_but_allows_later_irq():
    def row(kind, scanline, address, value):
        return (kind, 1, 0, scanline, 0, address, value)

    trace = [
        row("mapper-write", 250, 0x8000, 0x43),
        row("start", -1, 0, 0),
        row("mapper-write", 10, 0x8000, 0x46),
        row("mapper-write", 10, 0x8001, 0x17),
    ]
    change = [row("mapper-write", 193, 0x8000, 0x43),
              row("mapper-write", 193, 0x8001, 0x7E)]
    assert stable_chr(trace + change, 145)
    assert not stable_chr(trace + change, 220)
    assert not stable_chr(trace + [row("mapper-write", 100, 0x8000, 0xC6)], 145)


def test_neutrality_excludes_only_observer_files_and_detects_real_changed_frame(tmp_path):
    baseline = tmp_path / "A"
    observer = tmp_path / "B"
    baseline.mkdir()
    observer.mkdir()
    shared = ("trace.tsv", "controller.tsv",
              "450860-start-tiles.bin", "450860-end-tiles.bin", "450860-end-rgb.bin")
    for name in shared:
        for folder in (baseline, observer):
            (folder / name).write_bytes(name.encode("ascii"))
    # These legitimate B-only extra files must not create a false A/B/A failure.
    for name in ("bg-0001-tiles.bin", "bg-0001-pattern.bin",
                 "bg-0002-attribute.bin", "background-staging.tsv"):
        (observer / name).write_bytes(b"passive capture only")
    reference = common_signature(baseline)
    assert common_signature(observer) == reference
    assert signature_differences(reference, common_signature(observer)) == {}
    # But a real common frame or controller difference remains a hard failure.
    (observer / "450860-end-rgb.bin").write_bytes(b"different")
    changed = signature_differences(reference, common_signature(observer))
    assert set(changed) == {"450860-end-rgb.bin"}
    assert changed["450860-end-rgb.bin"]["reference"] != changed["450860-end-rgb.bin"]["observed"]
    (observer / "controller.tsv").unlink()
    assert "controller.tsv" in signature_differences(reference, common_signature(observer))
