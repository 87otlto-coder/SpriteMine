"""Compare SMB3's native CPU $2007 commits with physical CIRAM and staged strips.

Read-only, bounded verification of private MesenCE evidence. The probe records
CPU register callbacks BEFORE the actual PPU bus write; this verifier uses
later physical nametable snapshots to establish the memory effect.

Native passing requires an A/B/A-neutral source capture, both proven CPU
producer types, real matching $2007 write runs, and physical CIRAM agreement.
Final visible RGB and time-indexed CHR fetch remain separate gates.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from spritemine.background import (
    attribute_write_addresses, ciram_offset, pattern_write_addresses,
)
from spritemine.rom import load_rom
from research.mesence.verify_background_staging import (
    MODEL_SHA256, _read_events, verify as verify_staging,
)

REG_FIELDS = (
    "sequence", "kind", "frame", "cpu_cycle", "scanline", "ppu_cycle",
    "poll", "register", "value", "video_ram_addr", "bus_addr",
    "tmp_video_ram_addr", "write_toggle", "vertical_write",
    "mirroring_bit", "tileset",
)
CIRAM_FIELDS = ("frame", "boundary", "cpu_cycle", "mirroring_bit")


def _load_tsv(path: Path, names: tuple[str, ...], *, sequence: bool = False) -> list[dict]:
    with path.open("r", encoding="ascii", newline="") as fp:
        reader = csv.DictReader(fp, delimiter="\t")
        if tuple(reader.fieldnames or ()) != names:
            raise ValueError(f"Unexpected trace schema in {path.name}")
        rows = []
        last_cycle = -1
        for index, row in enumerate(reader, 1):
            if any(value is None or value == "" for value in row.values()):
                raise ValueError(f"Incomplete {path.name} row {index}")
            parsed = {key: (value if key in ("kind", "boundary") else int(value))
                      for key, value in row.items()}
            if sequence and parsed["sequence"] != index:
                raise ValueError("Non-monotonic PPU register event sequence")
            if parsed["cpu_cycle"] < last_cycle:
                raise ValueError("PPU event cycle order reversed")
            last_cycle = parsed["cpu_cycle"]
            rows.append(parsed)
    return rows


def _check_register_rows(rows: list[dict]) -> None:
    for row in rows:
        if (row["kind"] not in ("write", "status-read")
                or row["register"] not in (0x2000, 0x2002, 0x2005, 0x2006, 0x2007)
                or not 0 <= row["value"] < 256
                or not 0 <= row["video_ram_addr"] <= 0x7FFF
                or not 0 <= row["bus_addr"] < 0x4000
                or row["mirroring_bit"] not in (0, 1)
                or row["vertical_write"] not in (0, 1)
                or row["write_toggle"] not in (0, 1)
                or (row["kind"] == "status-read" and row["register"] != 0x2002)):
            raise ValueError(f"Malformed PPU register event #{row['sequence']}")


def _safe_vram_write(row: dict) -> tuple[int, int] | None:
    """Return CPU data write effective PPU address/value in non-rendering period.

    MesenCE applies $2007 data after a short delay; reject scanline-edge and
    visible-rendering candidates instead of assuming instantaneous writes.
    """
    if row["kind"] != "write" or row["register"] != 0x2007:
        return None
    addr = row["video_ram_addr"] & 0x3FFF
    if (row["scanline"] < 240 or row["scanline"] > 260
            or (row["scanline"] == 260 and row["ppu_cycle"] >= 325)
            or row["bus_addr"] != addr):
        return None
    return addr, row["value"]


def compare_ciram_frame(before: bytes, after: bytes, writes: list[dict]) -> dict:
    """Reconstruct 2 KiB nametable state from all recorded safe CPU $2007 writes."""
    if len(before) != 2048 or len(after) != 2048:
        raise ValueError("Physical CIRAM must be exactly 2 KiB")
    out = bytearray(before)
    applied = 0
    for row in writes:
        if row["register"] != 0x2007 or row["kind"] != "write":
            continue
        access = _safe_vram_write(row)
        if access is None:
            return {"eligible": False, "reason": "PPU data write not safe for delayed bus modeling"}
        addr, value = access
        if 0x3000 <= addr < 0x3F00:
            addr -= 0x1000
        if 0x2000 <= addr < 0x3000:
            mirroring = "horizontal" if row["mirroring_bit"] else "vertical"
            out[ciram_offset(addr, mirroring=mirroring)] = value
            applied += 1
    mismatches = [i for i, (a, b) in enumerate(zip(out, after)) if a != b]
    return {
        "eligible": True, "applied_nametable_writes": applied,
        "matches": not mismatches, "mismatches": len(mismatches),
        "first_difference": mismatches[0] if mismatches else None,
        "expected_sha256": sha256(out).hexdigest(),
        "observed_sha256": sha256(after).hexdigest(),
    }


def compare_nametable_alias(ppu: bytes, physical: bytes, mirroring_bit: int) -> dict:
    """Check all four physical 1 KiB alias windows against Mesen's PPU memory."""
    if len(ppu) != 0x3000 or len(physical) != 2048:
        raise ValueError("Expected 0x3000-byte PPU view and 2 KiB CIRAM")
    if mirroring_bit not in (0, 1):
        raise ValueError("Expected MMC3 horizontal/vertical mirror bit")
    mirroring = "horizontal" if mirroring_bit else "vertical"
    errors = []
    for address in range(0x2000, 0x3000):
        expected = physical[ciram_offset(address, mirroring=mirroring)]
        if ppu[address] != expected:
            errors.append(address)
    return {
        "compared": 4096, "mismatches": len(errors),
        "first_difference": errors[0] if errors else None,
    }


def matched_producer_segments(staging: list[dict], regs: list[dict], folder: Path) -> dict:
    """Locate complete 54/14-byte register writes after matching producer events.

    All candidate records must be on the same native frame, be in a safe
    non-rendering period, and address the expected PPU locations. Each CPU
    write can substantiate at most one producer event.
    """
    writes = [r for r in regs if r["kind"] == "write" and r["register"] == 0x2007]
    used: set[int] = set()
    counts = Counter()
    records = []
    for event in staging:
        name = f"bg-{event['sequence']:04d}"
        tiles = (folder / f"{name}-tiles.bin").read_bytes()
        if sha256(tiles).hexdigest() != MODEL_SHA256:
            counts["excluded_non_bonus_map"] += 1
            continue
        kind = event["kind"]
        if event["tileset"] != 1:
            counts["excluded_non_plains"] += 1
            continue
        if kind == "pattern":
            if not 0 <= event["last_ppu_column"] < 32:
                raise ValueError(f"Invalid PPU column for {name}")
            target = pattern_write_addresses(event["last_ppu_column"])
            values = (folder / f"{name}-pattern.bin").read_bytes()
            vertical = 1
        else:
            if event["last_attribute"] & 0xF8 != 0xC0:
                raise ValueError(f"Invalid PPU attribute column for {name}")
            target = attribute_write_addresses(event["last_attribute"] & 7)
            values = (folder / f"{name}-attribute.bin").read_bytes()
            vertical = 0
        if len(values) != len(target):
            raise ValueError(f"Invalid recorded CPU producer buffer length for {name}")
        start = None
        for i in range(len(writes) - len(values) + 1):
            if any(j in used for j in range(i, i + len(values))):
                continue
            candidate = writes[i:i + len(values)]
            if candidate[0]["cpu_cycle"] < event["cpu_cycle"]:
                continue
            if len({row["frame"] for row in candidate}) != 1:
                continue
            if all(
                _safe_vram_write(row) == (address, value)
                and row["vertical_write"] == vertical
                for row, address, value in zip(candidate, target, values)
            ):
                start = i
                break
        if start is None:
            counts[kind + "_not_observed"] += 1
            continue
        used.update(range(start, start + len(values)))
        counts[kind + "_matched"] += 1
        counts["matched_bytes"] += len(values)
        records.append({
            "event": name, "kind": kind, "producer_frame": event["frame"],
            "commit_frame": writes[start]["frame"],
            "first_cpu_cycle": writes[start]["cpu_cycle"],
            "last_cpu_cycle": writes[start + len(values) - 1]["cpu_cycle"],
            "bytes": len(values), "first_ppu_address": hex(target[0]),
        })
    return {"counts": dict(counts), "records": records}


def verify(rom, capture: Path) -> dict:
    manifest = json.loads((capture / "report.json").read_text(encoding="utf-8"))
    if manifest.get("neutral") is not True:
        raise ValueError("Native A/B/A neutrality was not established")
    info = manifest.get("ppu_register_trace") or {}
    if "ppu_register_probe" not in manifest.get("source_sha256", {}):
        raise ValueError("Source PPU probe hash missing")
    prior = verify_staging(rom, capture)
    if not prior["passed"]:
        raise ValueError("Native CPU staging gate is not accepted")

    folder = capture / "B"
    register_file = folder / "ppu-registers.tsv"
    boundary_file = folder / "ppu-ciram-boundaries.tsv"
    if sha256(register_file.read_bytes()).hexdigest() != info.get("log_sha256"):
        raise ValueError("PPU register trace fingerprint mismatch")
    if sha256(boundary_file.read_bytes()).hexdigest() != info.get("boundary_log_sha256"):
        raise ValueError("CIRAM boundary trace fingerprint mismatch")
    regs = _load_tsv(register_file, REG_FIELDS, sequence=True)
    _check_register_rows(regs)
    boundaries = _load_tsv(boundary_file, CIRAM_FIELDS)
    if len(regs) != info.get("event_count") or len(boundaries) != info.get("boundary_count"):
        raise ValueError("PPU event count mismatch")
    if not regs:
        raise ValueError("PPU trace contains no register events")
    expected_span = manifest["frame_range"]
    if not isinstance(expected_span, list) or len(expected_span) != 2:
        raise ValueError("Invalid native event frame range")
    start, end = expected_span
    if any(not start <= r["frame"] <= end for r in regs + boundaries):
        raise ValueError("PPU record outside bounded replay frames")

    producer_log = _read_events(folder / "background-staging.tsv")
    matching = matched_producer_segments(producer_log, regs, folder)

    boundary_by_key = {}
    for item in boundaries:
        if item["boundary"] not in ("start", "end"):
            raise ValueError("Unknown CIRAM snapshot boundary")
        key = (item["frame"], item["boundary"])
        if key in boundary_by_key:
            raise ValueError("Duplicate CIRAM snapshot boundary")
        boundary_by_key[key] = item

    counters = Counter()
    results = []
    for frame in range(start, end + 1):
        left = boundary_by_key.get((frame, "start"))
        right = boundary_by_key.get((frame, "end"))
        if not left or not right:
            raise ValueError(f"Missing physical CIRAM boundary for frame {frame}")
        before = (folder / f"ppu-{frame}-start-ciram.bin").read_bytes()
        after = (folder / f"ppu-{frame}-end-ciram.bin").read_bytes()
        ppu = (folder / f"{frame}-end-ppu.bin").read_bytes()
        alias = compare_nametable_alias(ppu, after, right["mirroring_bit"])
        counters["alias_samples"] += alias["compared"]
        counters["alias_mismatches"] += alias["mismatches"]
        frame_writes = [r for r in regs if r["frame"] == frame]
        comparison = compare_ciram_frame(before, after, frame_writes)
        if comparison["eligible"] and comparison["applied_nametable_writes"]:
            counters["frames_checked"] += 1
            counters["bytes_checked"] += len(after)
            counters["nametable_writes"] += comparison["applied_nametable_writes"]
            counters["physical_mismatches"] += comparison["mismatches"]
        elif not comparison["eligible"]:
            counters["frames_excluded_unsafe_write"] += 1
        results.append({
            "frame": frame, "mirroring_bit": right["mirroring_bit"],
            "physical": comparison, "alias": alias,
        })

    c = matching["counts"]
    passes = (
        c.get("pattern_matched", 0) > 0
        and c.get("attribute_matched", 0) > 0
        and c.get("pattern_not_observed", 0) == 0
        and c.get("attribute_not_observed", 0) == 0
        and counters["frames_checked"] > 0
        and counters["physical_mismatches"] == 0
        and counters["alias_mismatches"] == 0
    )
    return {
        "passed": passes,
        "scope": "bonus CPU staging -> $2007 write intent -> physical CIRAM frames",
        "native_final_rgb_or_fetch_time_chr_verified": False,
        "capture_neutral": True,
        "staging_passed": True,
        "ppu_source_provenance": manifest["source_sha256"],
        "producer_commits": matching,
        "memory": dict(counters),
        "frames": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result = verify(load_rom(args.rom), args.capture)
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f"PPU commit verification failed: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
