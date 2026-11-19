"""Validate private Plains producer snapshots against independently decoded PRG1.

The capture must come from pipe_replay.py --background-staging with successful
A/B/A signatures. Matching bytes alone do not establish final PPU/fetch pixels.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from spritemine.background import (
    attribute_strip_columns, pattern_strip, plains_quadrants,
    scroller_attribute_columns,
)
from spritemine.player import ROM_SHA256
from spritemine.rom import load_rom
from spritemine.world1_1 import MODEL_SHA256

STAGING_COLUMNS = (
    "sequence", "kind", "frame", "cpu_cycle", "scanline", "ppu_cycle", "poll",
    "direction", "column", "half", "last_ppu_column", "last_attribute",
    "junction_flag", "tileset",
)


def _bytes_match(expected: bytes, actual: bytes) -> dict:
    if len(expected) != len(actual):
        raise ValueError(f"Unexpected staging buffer length {len(actual)}; expected {len(expected)}")
    mismatches = [i for i, (a, b) in enumerate(zip(expected, actual)) if a != b]
    return {
        "matches": not mismatches,
        "bytes": len(expected),
        "expected_sha256": sha256(expected).hexdigest(),
        "observed_sha256": sha256(actual).hexdigest(),
        "mismatch_count": len(mismatches),
        "first_difference": mismatches[0] if mismatches else None,
    }


def _read_events(path: Path) -> list[dict]:
    with path.open("r", encoding="ascii", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != STAGING_COLUMNS:
            raise ValueError("Unexpected native staging event schema")
        events = []
        for i, event in enumerate(reader, 1):
            if any(value is None for value in event.values()):
                raise ValueError("Incomplete native staging event")
            parsed = {key: (value if key == "kind" else int(value))
                      for key, value in event.items()}
            if parsed["sequence"] != i or parsed["kind"] not in ("pattern", "attribute"):
                raise ValueError("Non-monotonic or unsupported staging event")
            events.append(parsed)
        return events


def verify(rom, capture: Path) -> dict:
    report_path = capture / "report.json"
    manifest = json.loads(report_path.read_text(encoding="utf-8"))
    if manifest.get("neutral") is not True:
        raise ValueError("Native replay did not establish A/B/A neutrality")
    source_hashes = manifest.get("source_sha256", {})
    if source_hashes.get("rom") != ROM_SHA256 or rom.metadata.rom_sha256 != ROM_SHA256:
        raise ValueError("Unexpected ROM identity in native replay")
    if "background_probe" not in source_hashes:
        raise ValueError("Capture did not record the background probe source hash")
    info = manifest.get("background_staging") or {}
    path = capture / "B" / "background-staging.tsv"
    if sha256(path.read_bytes()).hexdigest() != info.get("log_sha256"):
        raise ValueError("Staging log hash differs from A/B/A report")
    events = _read_events(path)
    if info.get("event_count") != len(events):
        raise ValueError("Native event count differs from replay manifest")

    layout = plains_quadrants(rom)
    counts = Counter()
    comparisons = []
    for event in events:
        key = f'bg-{event["sequence"]:04d}'
        tiles = (capture / "B" / f"{key}-tiles.bin").read_bytes()
        if len(tiles) != 864:
            raise ValueError(f"Invalid {key} logical Tile_Mem length")
        if event["tileset"] != 1 or sha256(tiles).hexdigest() != MODEL_SHA256:
            counts["non_bonus_or_modified_map"] += 1
            continue
        col, direction, half = event["column"], event["direction"], event["half"]
        if direction not in (0, 1):
            raise ValueError(f"Invalid {key} scroll direction")
        if event["kind"] == "pattern":
            if not 0 <= col < 32 or half not in (0, 1):
                counts["pattern_column_out_of_model"] += 1
                continue
            expected_ppu_col = (col % 16) * 2 + half
            if event["last_ppu_column"] != expected_ppu_col:
                counts["metadata_mismatches"] += 1
                comparisons.append({"event": key, "kind": "pattern",
                                    "error": "PPU column metadata mismatch"})
                continue
            expected = pattern_strip(tiles, layout, col, half)
            observed = (capture / "B" / f"{key}-pattern.bin").read_bytes()
        else:
            first_col, second_col = scroller_attribute_columns(col, direction)
            if first_col >= 32 or second_col >= 32:
                counts["attribute_columns_out_of_model"] += 1
                continue
            expected_attr_column = 0xC0 | ((col & 15) >> 1)
            if event["last_attribute"] != expected_attr_column:
                counts["metadata_mismatches"] += 1
                comparisons.append({"event": key, "kind": "attribute",
                                    "error": "PPU attribute metadata mismatch"})
                continue
            expected = attribute_strip_columns(tiles, first_col, second_col)
            observed = (capture / "B" / f"{key}-attribute.bin").read_bytes()
        diff = _bytes_match(expected, observed)
        counts[event["kind"] + "_checked"] += 1
        counts["bytes_checked"] += len(expected)
        counts["mismatches"] += diff["mismatch_count"]
        comparisons.append({
            "event": key, "kind": event["kind"], "frame": event["frame"],
            "cpu_cycle": event["cpu_cycle"], "column": col,
            "direction": direction, **diff,
        })

    complete = (counts["pattern_checked"] > 0 and counts["attribute_checked"] > 0)
    passed = complete and counts["mismatches"] == 0 and counts["metadata_mismatches"] == 0
    return {
        "passed": passed,
        "scope": "first-entry bonus logical map -> CPU PPU staging buffers",
        "native_final_ppu_or_rgb_verified": False,
        "capture_metadata_consistent": True,
        "events_recorded": len(events),
        "counts": dict(counts),
        "comparisons": comparisons,
        "missing_evidence": (
            [] if complete else ["A matching native pattern and attribute producer event are both required"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path, help="Original verified PRG1 .nes or ZIP")
    parser.add_argument("capture", type=Path, help="Private A/B/A capture directory")
    args = parser.parse_args()
    try:
        result = verify(load_rom(args.rom), args.capture)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Background staging verification failed: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
