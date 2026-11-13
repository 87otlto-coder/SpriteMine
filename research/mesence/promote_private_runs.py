"""Promote six verified SMB3 PRG1 MesenCE runs into canonical Windows FIXTURE.

No game assets are bundled or emitted to Git; this helper only copies locally
available private A/B/A evidence. Default is strictly read-only (--apply writes).
The sharing ZIP deliberately lacks original ROM/save-state copies and cannot
replace the complete private 79-file source capture directories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path, PureWindowsPath

from .animation_archive import read_verified_timeline, verified_timeline_runs
from .graphics_harness import private_folder

EXPECTED_TIMELINE_SHA256 = "1e48bf12926edcb80e451154c4e1a7aa809480d9467e313c2ea460a452eba1eb"
EXPECTED_ROM_SHA256 = "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"
EXPECTED_SLOT_SHA256 = "31f5f5ae97d9f8c5d8aa3fded0c6a2d64f2c19c9fedad1d7237d81d264d759f2"
EXPECTED_RUNS = (
    "anim-right-w8-extakxfv", "anim-right-w9-bq6nc6ix",
    "anim-right-w10-tmyvtt1w", "anim-right-w11-y2ss03yj",
    "anim-right-w12-h26pbwik", "anim-right-w13-1sd63men",
    "anim-right-w14-5wf5l2l2", "anim-right-w15-a01sl8v2",
    "anim-right-w16-t_3vhuza", "anim-right-w17-8n_cvxvz",
    "anim-right-w18-rspfqrxu", "anim-right-w19-g649rb_k",
    "anim-right-w20-y27dpwoh", "anim-right-w21-uttsrxta",
    "anim-right-w22-_zxu9jx8", "anim-right-w23-pxk3ehjt",
    "anim-right-w24-afiml2y8", "anim-right-w25-9ymgp0xa",
)
COMPLETE_FILE_COUNT = 79


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_files(run: Path) -> dict[str, str]:
    if run.is_symlink() or not run.is_dir():
        raise ValueError(f"Capture directory missing or is a link: {run}")
    result = {}
    for entry in run.rglob("*"):
        if entry.is_symlink():
            raise ValueError(f"Symlink is forbidden in capture evidence: {entry}")
        if not entry.is_file() and not entry.is_dir():
            raise ValueError(f"Unsupported capture entry: {entry}")
        if entry.is_file():
            relative = entry.relative_to(run).as_posix()
            result[relative] = _sha(entry)
    if len(result) != COMPLETE_FILE_COUNT:
        raise ValueError(
            f"Expected {COMPLETE_FILE_COUNT} COMPLETE private files in {run}; "
            f"found {len(result)}. The sharing archive has only 77 per run."
        )
    for required in ("replay.nes", "slot-copy.mss", "capture.lua",
                     "report.json", "A/launch.json", "B/launch.json",
                     "A2/launch.json"):
        if required not in result:
            raise ValueError(f"Missing original capture evidence: {run / required}")
    if result["replay.nes"] != EXPECTED_ROM_SHA256:
        raise ValueError(f"Wrong SMB3 PRG1 ROM copy: {run}")
    if result["slot-copy.mss"] != EXPECTED_SLOT_SHA256:
        raise ValueError(f"Wrong immutable MesenCE save state: {run}")
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    statuses = report.get("statuses", {})
    if any(statuses.get(gate) != "verified" for gate in ("replay", "pixels", "walking")):
        raise ValueError(f"Source run has incomplete verification gates: {run}")
    return result


def _validate_root(parent: Path) -> Path:
    parent = private_folder(parent).resolve(strict=True)
    if (parent.name != "GraphicsValidation" or parent.parent.name != "SMB3"
            or parent.parent.parent.name.upper() != "FIXTURE"):
        raise ValueError("Expected <workspace>/FIXTURE/SMB3/GraphicsValidation")
    if not parent.is_dir():
        raise ValueError("GraphicsValidation location is not a directory")
    return parent


def check_and_promote(timeline_file: Path, target_root: Path, *, apply: bool = False) -> dict:
    timeline = private_folder(Path(timeline_file)).resolve(strict=True)
    target_base = Path(target_root).resolve(strict=True)
    dest = _validate_root(target_base / "FIXTURE" / "SMB3" / "GraphicsValidation")
    if _sha(timeline) != EXPECTED_TIMELINE_SHA256:
        raise ValueError("Original 18-frame timeline SHA-256 mismatch; aborting")
    data = read_verified_timeline(timeline)
    if (data["frame_count"] != 18 or data["first_emulator_frame"] != 448385
            or data["last_emulator_frame"] != 448402
            or data["source_slot_sha256"] != EXPECTED_SLOT_SHA256
            or data["source_rom_sha256"] != EXPECTED_ROM_SHA256
            or data["input_plan"] != "right"):
        raise ValueError("Not the accepted 18-frame SMB3 PRG1 right-input archive")
    paths = [PureWindowsPath(frame["run_dir"]).name for frame in data["frames"]]
    if tuple(paths) != EXPECTED_RUNS:
        raise ValueError("Archived 18 source-directory identifiers differ")

    # Full private source validation is mandatory, even for dry run.
    source_runs = verified_timeline_runs(timeline)
    source_parent = _validate_root(source_runs[0].parent)
    if source_parent == dest:
        raise ValueError("Source and destination are the same directory")
    before_timeline = _sha(timeline)

    missing, already = [], []
    for index, name in enumerate(EXPECTED_RUNS):
        src = source_runs[index]
        if src.parent != source_parent or src.name != name:
            raise ValueError(f"Unexpected private capture path: {src}")
        source_hashes = _run_files(src)
        target = dest / name
        if target.exists() or target.is_symlink():
            if _run_files(target) != source_hashes:
                raise ValueError(f"Existing canonical capture differs: {target}")
            already.append(name)
        else:
            if index < 12:
                raise ValueError(f"Original warmup 8-19 is unexpectedly absent: {target}")
            missing.append(name)

    if not apply:
        return {
            "status": "ready_for_explicit_write",
            "verified_original_windows": len(source_runs),
            "unchanged_canonical_runs": len(already),
            "missing_runs": missing,
            "source_timeline_sha256": before_timeline,
            "files_per_run": COMPLETE_FILE_COUNT,
        }

    # All 18 source runs and existing target runs were checked before ANY write.
    stage_parent = private_folder(target_base / "FIXTURE" / "SMB3" / "TransferStaging")
    stage_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="pr19-six-runs-", dir=stage_parent))
    promoted = []
    try:
        # Stage and SHA-validate every missing run BEFORE promotion.
        for name in missing:
            src = source_parent / name
            staged = stage / name
            shutil.copytree(src, staged)
            if _run_files(staged) != _run_files(src):
                raise ValueError(f"Staged transfer bytes differ: {name}")
        if _sha(timeline) != before_timeline:
            raise ValueError("Source timeline changed during staging")
        for name in missing:
            target = dest / name
            if target.exists() or target.is_symlink():
                raise FileExistsError(f"Refusing to overwrite canonical evidence: {target}")
            (stage / name).rename(target)
            promoted.append(name)
        verified = verified_timeline_runs(timeline, runs_parent_override=dest)
        if len(verified) != 18:
            raise ValueError("Relocated A/B/A source verification did not yield 18 windows")
        if _sha(timeline) != before_timeline:
            raise ValueError("Source timeline changed during verification")
        if not any(stage.iterdir()):
            stage.rmdir()  # remove empty staging shell only; never delete evidence
        return {
            "status": "promoted_and_reverified",
            "originally_present": len(already),
            "promoted_runs": promoted,
            "verified_canonical_windows": len(verified),
            "source_timeline_sha256": before_timeline,
            "files_per_run": COMPLETE_FILE_COUNT,
        }
    finally:
        # No automatic deletion of private evidence or partially staged inputs.
        # The staging directory is intentionally preserved for audit/recovery.
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--timeline", type=Path, required=True,
                   help="Original COMPLETE private 18-frame C: timeline.json")
    p.add_argument("--target-root", type=Path, default=Path("F:/Dev/ROMMAGE"),
                   help="Canonical workspace; must contain FIXTURE/SMB3/GraphicsValidation")
    p.add_argument("--apply", action="store_true",
                   help="Explicitly copy the six missing full A/B/A directories; default read-only")
    args = p.parse_args(argv)
    try:
        result = check_and_promote(args.timeline, args.target_root, apply=args.apply)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"SpriteMine private source promotion FAILED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
