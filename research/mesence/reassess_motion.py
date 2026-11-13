"""Read-only-first, auditable reassessment of the real SMB3 warmup-26 motion gate.

Only the known preserved A/B/A capture may be reassessed. No emulator or game
extraction is invoked. Reconstructs the entire report independently, refuses
any change beyond walking=failed -> verified, and backs up both original
report artifacts under private FIXTURE before an explicit --apply.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import graphics_report
from .animation_timeline import _initial_report, load_verified_window
from .graphics_harness import private_folder
from .promote_private_runs import EXPECTED_ROM_SHA256, EXPECTED_SLOT_SHA256

EXPECTED_NAME = "anim-right-w26-9_qhwqzy"
EXPECTED_FRAME = 448403
EXPECTED_PROBE = "8b50620cc322893a272fdf07292f83aeb0690ff2a595efdd9081d9f5b0722283"
EXPECTED_EXE = "8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7"
EXPECTED_FILE_COUNT = 79


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _capture_manifest(run: Path) -> dict[str, str]:
    result = {}
    for path in run.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlink in captured evidence: {path}")
        if path.is_file():
            result[path.relative_to(run).as_posix()] = _sha(path.read_bytes())
        elif not path.is_dir():
            raise ValueError(f"Unsupported capture entry: {path}")
    if len(result) != EXPECTED_FILE_COUNT:
        raise ValueError(f"Expected {EXPECTED_FILE_COUNT} complete source files; got {len(result)}")
    for file in ("report.json", "report.html", "replay.nes", "slot-copy.mss",
                 "capture.lua", "A/launch.json", "B/launch.json", "A2/launch.json"):
        if file not in result:
            raise ValueError(f"Missing archived source file: {file}")
    return result


def reassess(run_dir: Path, *, apply: bool = False) -> dict:
    run = private_folder(Path(run_dir)).resolve(strict=True)
    if (not run.is_dir() or run.name != EXPECTED_NAME
            or run.parent.name != "GraphicsValidation"
            or run.parent.parent.name != "SMB3"
            or run.parent.parent.parent.name.upper() != "FIXTURE"):
        raise ValueError("This narrow reassessment accepts only the original warmup-26 capture")
    original_hashes = _capture_manifest(run)
    if (original_hashes["replay.nes"] != EXPECTED_ROM_SHA256
            or original_hashes["slot-copy.mss"] != EXPECTED_SLOT_SHA256
            or original_hashes["capture.lua"] != EXPECTED_PROBE):
        raise ValueError("Original ROM, slot or replay probe is not the accepted evidence")

    report_file = run / "report.json"
    html_file = run / "report.html"
    report_bytes = report_file.read_bytes()
    html_bytes = html_file.read_bytes()
    archived = json.loads(report_bytes.decode("utf-8"))
    if (archived.get("schema") != 1
            or archived.get("statuses", {}).get("replay") != "verified"
            or archived["statuses"].get("pixels") != "verified"
            or archived["statuses"].get("walking") != "failed"
            or "reason" in archived):
        raise ValueError("Expected original warmup-26 walking-only rejection report")

    provenance = archived.get("provenance", {})
    if (provenance.get("plan") != "right"
            or provenance.get("warmup") != 26
            or provenance.get("rom_sha256") != EXPECTED_ROM_SHA256
            or provenance.get("slot_sha256") != EXPECTED_SLOT_SHA256
            or provenance.get("probe_sha256") != EXPECTED_PROBE
            or provenance.get("emulator_sha256") != EXPECTED_EXE):
        raise ValueError("Unexpected A/B/A capture provenance")

    # The legacy publisher used Path.write_text, which translates embedded
    # JSON newlines to CRLF on Windows. Do not mistake that for source tampering.
    # The published JSON uses sort_keys=True, but the original HTML rows
    # followed the validator's insertion order. Restore that display order
    # strictly from the fixed schema before comparing the archived HTML.
    original_status_order = tuple(_initial_report()["statuses"])
    if set(archived["statuses"]) != set(original_status_order):
        raise ValueError("Unexpected status keys in archived A/B/A report")
    display_report = copy.deepcopy(archived)
    display_report["statuses"] = {
        key: archived["statuses"][key] for key in original_status_order
    }
    existing_html = html_bytes.decode("utf-8")
    rendered_html = graphics_report.format_report_html(run, display_report)
    if existing_html not in (rendered_html, rendered_html.replace("\n", "\r\n")):
        raise ValueError("Original HTML report differs from the archived report; preserve it")

    updated = {"schema": 1, **_initial_report()}
    graphics_report.validate(run, updated, write_visuals=False)
    if updated["statuses"].get("walking") != "verified":
        raise ValueError("Corrected movement gate still fails; preserve captured evidence")
    if updated["boundaries"][2]["frame_count"] != EXPECTED_FRAME:
        raise ValueError("Reassessed capture is not emulator frame 448403")
    only_walk_reclassified = copy.deepcopy(archived)
    only_walk_reclassified["statuses"]["walking"] = "verified"
    if updated != only_walk_reclassified:
        differing = sorted(k for k in set(updated) | set(only_walk_reclassified)
                           if updated.get(k) != only_walk_reclassified.get(k))
        raise ValueError(f"Independent revalidation changed more than the walking gate: {differing}")

    # Keep the original platform's report line endings in the revised artifacts.
    json_eol = "\r\n" if b"\r\n" in report_bytes else "\n"
    html_eol = "\r\n" if b"\r\n" in html_bytes else "\n"
    updated_bytes = json.dumps(updated, indent=2, sort_keys=True).replace(
        "\n", json_eol
    ).encode("utf-8")
    updated_html = graphics_report.format_report_html(run, updated).replace(
        "\n", html_eol
    ).encode("utf-8")
    result = {
        "status": "ready_for_explicit_reassessment",
        "run": str(run),
        "emulator_frame": EXPECTED_FRAME,
        "original_report_sha256": _sha(report_bytes),
        "revalidated_report_sha256": _sha(updated_bytes),
        "unchanged_capture_files": EXPECTED_FILE_COUNT - 2,
        "changes": {"walking": ["failed", "verified"]},
    }
    if not apply:
        return result

    # Preserve both original published files BEFORE replacing either.
    review_parent = private_folder(run.parent.parent / "ReviewHistory")
    review = review_parent / f"{EXPECTED_NAME}-{_sha(report_bytes)[:16]}"
    if review.exists():
        raise FileExistsError(f"Existing reassessment evidence must not be overwritten: {review}")
    review_parent.mkdir(parents=True, exist_ok=True)
    review.mkdir()
    (review / "original-report.json").write_bytes(report_bytes)
    (review / "original-report.html").write_bytes(html_bytes)
    (review / "revalidated-report.json").write_bytes(updated_bytes)
    (review / "revalidated-report.html").write_bytes(updated_html)
    receipt = {
        "schema": "spritemine.smb3.w26-walking-reassessment/1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "run": str(run),
        "original_file_sha256": original_hashes,
        "original_report_sha256": _sha(report_bytes),
        "original_html_sha256": _sha(html_bytes),
        "new_report_sha256": _sha(updated_bytes),
        "new_html_sha256": _sha(updated_html),
        "basis": "Replay, pixel and pair checks verified; rightward displacement plus "
                 "tile change; independent one-pixel Y drift at poll 88",
    }
    (review / "receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    if ((_sha(report_file.read_bytes()) != _sha(report_bytes))
            or (_sha(html_file.read_bytes()) != _sha(html_bytes))):
        raise ValueError("Original report changed while preserving audit evidence")

    temp_report = run / f".revalidated-report-{uuid.uuid4().hex}.tmp"
    temp_html = run / f".revalidated-html-{uuid.uuid4().hex}.tmp"
    try:
        temp_report.write_bytes(updated_bytes)
        temp_html.write_bytes(updated_html)
        os.replace(temp_report, report_file)
        os.replace(temp_html, html_file)
        # Independently reassemble from the A/B/A source with no new writes.
        record, _ = load_verified_window(run)
        if record["frame"]["frame_count"] != EXPECTED_FRAME:
            raise ValueError("Post-reassessment source frame identity changed")
        after = _capture_manifest(run)
        for name, original_sha in original_hashes.items():
            if name not in ("report.json", "report.html") and after[name] != original_sha:
                raise ValueError(f"Immutable capture input changed during reassessment: {name}")
        if after["report.json"] != _sha(updated_bytes) or after["report.html"] != _sha(updated_html):
            raise ValueError("Reassessed report hashes differ from archived revision")
    except Exception:
        # Restore the archived original verdict if a postflight check fails.
        # ReviewHistory still contains both versions and the error is re-raised.
        report_file.write_bytes(report_bytes)
        html_file.write_bytes(html_bytes)
        raise
    finally:
        temp_report.unlink(missing_ok=True)
        temp_html.unlink(missing_ok=True)

    return {
        **result,
        "status": "reassessed_and_independently_verified",
        "review_history": str(review),
        "raw_capture_inputs_unchanged": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--apply", action="store_true",
                        help="Back up original reports and write only a new verified verdict")
    args = parser.parse_args(argv)
    try:
        result = reassess(args.run, apply=args.apply)
    except (OSError, ValueError, KeyError, IndexError, TypeError,
            json.JSONDecodeError) as exc:
        print(f"SpriteMine motion reassessment FAILED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
