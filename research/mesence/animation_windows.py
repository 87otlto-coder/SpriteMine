"""Capture adjacent SMB3 small-Mario frames using the proven slot-1 A/B/A harness.

Runs the existing headless graphics harness once per increasing warmup value.
Each run reloads the *same* immutable save-state bytes in three independent
MesenCE processes, verifies the 16x16 target against its own sprites-hidden
reference, and preserves full controller-bus/CHR/PPU evidence.

Cost: three emulator launches per accepted animation frame. This deliberately
favors correctness over speed; not a general-purpose animation capturer yet.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import uuid
from argparse import Namespace
from pathlib import Path
from typing import Any

from . import graphics_harness, graphics_report
from .animation_archive import verified_timeline_runs
from .animation_timeline import assemble_timeline, load_verified_window


def capture_animation(args: Namespace) -> dict[str, Any]:
    """Collect >=2 neighboring validated target frames without changing slot 1."""
    count = args.count
    first = args.first_warmup
    if type(count) is not int or not 2 <= count <= 12:
        raise ValueError("Use 2..12 frames for this bounded research experiment")
    if type(first) is not int or not 2 <= first <= 120 or first + count > 121:
        raise ValueError("Warmups must all stay within the supported 2..120 range")
    if args.plan not in ("neutral", "right", "jump"):
        raise ValueError("Unsupported SMB3 controller plan")
    if args.start_pulse:
        raise ValueError("Game Start pulses are not supported for animation timelines")

    root = Path(args.root).resolve(strict=True)
    source_slot = Path(args.slot).resolve(strict=True)
    original_slot_sha = graphics_harness.digest(source_slot)
    fixture = graphics_harness.private_folder(root / "FIXTURE")
    runs_parent = graphics_harness.private_folder(
        fixture / "SMB3" / "GraphicsValidation"
    )
    animation_parent = graphics_harness.private_folder(
        fixture / "SMB3" / "Animations"
    )
    runs_parent.mkdir(parents=True, exist_ok=True)
    animation_parent.mkdir(parents=True, exist_ok=True)

    manual_reuse = getattr(args, "reuse_run", None) or []
    prior_timeline = getattr(args, "reuse_timeline", None)
    # Explicit --reuse-run paths may follow a prior timeline when a batch
    # failed partway through. Revalidate ALL of them before new execution.
    source_paths = (verified_timeline_runs(Path(prior_timeline))
                    if prior_timeline else []) + list(manual_reuse)
    reuse_paths = [
        graphics_harness.private_folder(Path(path)).resolve(strict=True)
        for path in source_paths
    ]
    if len({str(path) for path in reuse_paths}) != len(reuse_paths):
        raise ValueError("Duplicate reused A/B/A runs")
    if len(reuse_paths) + count > 119:
        raise ValueError("Maximum timeline is 119 warmups (2..120); use bounded capture batches")
    if any(runs_parent not in path.parents for path in reuse_paths):
        raise ValueError("Reuse must refer to previous local GraphicsValidation runs")

    reused_windows = [load_verified_window(path)[0] for path in reuse_paths]
    reused_windows.sort(key=lambda item: item["frame"]["warmup"])
    if reused_windows:
        warmups = [r["frame"]["warmup"] for r in reused_windows]
        expected = list(range(first - len(warmups), first))
        if warmups != expected:
            raise ValueError(
                "Reused capture warmups must be consecutive and directly precede "
                f"the new first warmup {first}; received {warmups}"
            )
        if any(
            r["source"]["slot_sha256"] != original_slot_sha
            for r in reused_windows
        ):
            raise ValueError("Reused runs reference a different slot-1 state")
        if any(r["source"]["plan"] != args.plan for r in reused_windows):
            raise ValueError("Reused runs have a different controller input plan")
        # Fail closed before paying for new A/B/A launches: a mixed archive
        # must never be accepted even if the later timeline assembly rejects it.
        identity_keys = ("slot_sha256", "rom_sha256", "emulator_sha256",
                         "emulator_version", "probe_sha256", "plan", "start_pulse")
        for key in identity_keys:
            values = [row["source"][key] for row in reused_windows]
            if any(value != values[0] for value in values[1:]):
                raise ValueError(f"Reused runs disagree on source identity: {key}")
        restores = [r["frame"]["restore"] for r in reused_windows]
        if any(value != restores[0] for value in restores[1:]):
            raise ValueError("Reused runs disagree on restored state")
        prior_frames = [r["frame"]["frame_count"] for r in reused_windows]
        prior_clocks = [r["frame"]["start_master_clock"] for r in reused_windows]
        if any(b - a != 1 for a, b in zip(prior_frames, prior_frames[1:])):
            raise ValueError("Reused runs are not consecutive emulator frames")
        if any(b <= a for a, b in zip(prior_clocks, prior_clocks[1:])):
            raise ValueError("Reused runs have non-increasing master clocks")

    accepted = [Path(r["frame"]["run_dir"]) for r in reused_windows]
    new_runs = []
    for warmup in range(first, first + count):
        if graphics_harness.digest(source_slot) != original_slot_sha:
            raise ValueError("Original slot backing file changed during sequence capture")
        run = Path(tempfile.mkdtemp(
            prefix=f"anim-{args.plan}-w{warmup}-", dir=runs_parent
        ))
        print(f"Capturing {args.plan} warmup={warmup}: {run}", flush=True)
        run_args = Namespace(
            root=root, rom=args.rom, slot=source_slot, plan=args.plan,
            warmup=warmup, start_pulse=False,
        )
        try:
            graphics_harness.capture(run_args, run)
        except Exception as exc:
            graphics_report.publish(run, f"Capture failed: {exc}")
            raise ValueError(f"Capture failed at warmup {warmup}: {run}") from exc
        if graphics_report.publish(run) != 0:
            raise ValueError(
                f"Graphics verification failed at warmup {warmup}. "
                f"Private evidence preserved in {run}"
            )
        accepted.append(run)
        new_runs.append(run)

    if graphics_harness.digest(source_slot) != original_slot_sha:
        raise ValueError("Original slot backing file changed during sequence capture")
    first_timeline_warmup = first - len(reused_windows)
    export = animation_parent / (
        f"{args.plan}-{first_timeline_warmup}-{first+count-1}-{uuid.uuid4().hex[:10]}"
    )
    result = assemble_timeline(accepted, export)
    if result["source_slot_sha256"] != original_slot_sha:
        raise ValueError("Assembled sequence source slot identity disagrees")
    return {
        "result": result["result"],
        "status": "validated_local_A_B_A_sequence",
        "plan": args.plan,
        "source_slot_sha256": original_slot_sha,
        "frame_count": result["frame_count"],
        "first_emulator_frame": result["first_emulator_frame"],
        "last_emulator_frame": result["last_emulator_frame"],
        "timeline_json": str(export / "timeline.json"),
        "spritesheet_png": str(export / "spritesheet.png"),
        "original_slot_unchanged": True,
        "input_run_dirs": [str(p) for p in accepted],
        "reused_run_dirs": [str(p) for p in accepted[:len(reused_windows)]],
        "new_run_dirs": [str(p) for p in new_runs],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run consecutive SMB3 slot-1 A/B/A graphics validation windows"
    )
    p.add_argument("--root", type=Path, default=Path("F:/Dev/ROMMAGE"))
    p.add_argument("--rom", type=Path, default=None)
    p.add_argument("--slot", type=Path, required=True,
                   help="EXISTING MesenCE slot 1 backing file, never overwritten")
    p.add_argument("--plan", choices=("neutral", "right", "jump"), default="right")
    p.add_argument("--first-warmup", type=int, default=8,
                   help="First NEW frame warmup; reused frames must directly precede it")
    p.add_argument("--count", type=int, default=3,
                   help="Number of NEW frames to capture (2–12)")
    p.add_argument("--reuse-run", type=Path, action="append", default=[],
                   help="Existing verified GraphicsValidation A/B/A directory; "
                        "repeat for previous consecutive frames or add successful "
                        "partial runs after --reuse-timeline")
    p.add_argument("--reuse-timeline", type=Path,
                   help="Previous immutable FIXTURE/SMB3/Animations/*/timeline.json; "
                        "revalidates ALL source windows and prior PNGs before adding new frames")
    p.add_argument("--start-pulse", action="store_true")
    args = p.parse_args(argv)
    try:
        result = capture_animation(args)
    except (OSError, ValueError, KeyError, TypeError, IndexError,
            json.JSONDecodeError) as exc:
        print(f"SpriteMine animation capture unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
