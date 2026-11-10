"""Verify paired MesenCE start/end CHR observations against same-session MMC3 writes.

This module prints only hashes, source ROM offsets and timing metadata. It never
exports raw game assets, screenshots or source ROM bytes. A model match establishes
a frame-boundary PPU mapping, not which bytes were fetched on visible scanlines.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

try:
    from .decode_mmc3_trace import analyze_trace, load_chr
except ImportError:  # Direct Python execution inside research/mesence.
    from decode_mmc3_trace import analyze_trace, load_chr

TOOL = "spritemine-mesence-phase-capture-v1"
RENDER_TOOL = "spritemine-mesence-render-capture-v1"
EXPECTED_EVENTS = ("startFrame", "endFrame", "startFrame", "endFrame")
SESSION_NAME = re.compile(r"^(?:phase|render)_\d{10}_\d{9,}$")
ROM_SHA1 = re.compile(r"^[0-9a-fA-F]{40}$")
SIZES = {"oam": 256, "palette": 32, "ppu_pattern": 8192}


def _nonnegative(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a nonnegative integer")
    return value


def _integer(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be an integer")
    return value


def verify_phase_session(
    manifest_path: Path,
    rom_path: Path | None = None,
    *,
    allow_synthetic_rom: bool = False,
) -> dict[str, Any]:
    """Validate one session and optionally model 8 KiB snapshots from the ROM.

    allow_synthetic_rom is ONLY for deterministic unit tests. CLI never offers
    it; a real --rom must match the verified SMB3 PRG1 revision.
    """
    path = Path(manifest_path)
    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ValueError("Capture manifest must be a JSON object")
    capture_tool = source.get("capture_tool")
    if source.get("schema_version") != 1 or capture_tool not in (TOOL, RENDER_TOOL):
        raise ValueError("Unsupported phase capture tool or schema")
    is_render = capture_tool == RENDER_TOOL
    if source.get("evidence") != "captured":
        raise ValueError("Capture provenance is not labeled captured")
    session = source.get("session_id")
    if (not isinstance(session, str) or not SESSION_NAME.fullmatch(session)
            or (is_render and not session.startswith("render_"))
            or (not is_render and not session.startswith("phase_"))):
        raise ValueError("Invalid session identity")
    if path.name != f"{session}.json":
        raise ValueError("Manifest filename differs from session identity")
    mesen_rom_sha1 = source.get("rom_sha1_reported_by_mesen")
    if not isinstance(mesen_rom_sha1, str) or not ROM_SHA1.fullmatch(mesen_rom_sha1):
        raise ValueError("Missing or invalid Mesen-reported ROM SHA-1")
    if source.get("completed_frame_pairs") != 2:
        raise ValueError("Expected exactly two completed frame pairs")
    write_limit = _nonnegative(source.get("write_limit"), "write_limit")
    dropped = _nonnegative(source.get("dropped_writes"), "dropped_writes")
    if write_limit > 4096:
        raise ValueError("Unexpectedly large write_limit")
    captures = source.get("phase_captures")
    writes = source.get("writes")
    if not isinstance(captures, list) or len(captures) != 4:
        raise ValueError("Expected four phase snapshots")
    if not isinstance(writes, list) or len(writes) > write_limit:
        raise ValueError("Invalid or oversized MMC3 write history")

    output: list[dict[str, Any]] = []
    clock_last = -1
    frames: list[int] = []
    for i, snap in enumerate(captures):
        if not isinstance(snap, dict) or snap.get("event") != EXPECTED_EVENTS[i]:
            raise ValueError(f"Snapshot {i + 1}: incorrect start/end sequence")
        frame = _nonnegative(snap.get("frame_count"), "frame_count")
        clock = _nonnegative(snap.get("master_clock"), "master_clock")
        if clock <= clock_last:
            raise ValueError("Phase master clocks must be strictly increasing")
        clock_last = clock
        if i % 2 == 1 and frame != frames[-1]:
            raise ValueError("Start and end within a frame pair disagree on frame number")
        if i == 2 and frame <= frames[0]:
            raise ValueError("Second frame pair did not advance")
        frames.append(frame)
        scanline = _integer(snap.get("ppu_scanline"), "ppu_scanline")
        cycle = _integer(snap.get("ppu_cycle"), "ppu_cycle")
        if snap.get("sprite_height") not in (8, 16):
            raise ValueError("Invalid sprite height")
        expected_names = {
            kind: f"{session}_{i + 1}_{snap['event']}_{kind}.bin" for kind in SIZES
        }
        if is_render:
            expected_names["screen_rgb"] = (
                f"{session}_{i + 1}_{snap['event']}_screen_rgb.bin"
                if i % 2 == 1 else None
            )
        filenames = snap.get("files")
        if not isinstance(filenames, dict) or filenames != expected_names:
            raise ValueError(f"Snapshot {i + 1}: mismatched file references")
        ppu_data: bytes | None = None
        checksums: dict[str, str] = {}
        for kind, expected_size in SIZES.items():
            blob = (path.parent / filenames[kind]).read_bytes()
            if len(blob) != expected_size:
                raise ValueError(
                    f"{filenames[kind]}: expected {expected_size} bytes, got {len(blob)}"
                )
            checksums[kind] = hashlib.sha256(blob).hexdigest()
            if kind == "ppu_pattern":
                ppu_data = blob
        assert ppu_data is not None
        width = None
        height = None
        if is_render:
            width = snap.get("screen_width")
            height = snap.get("screen_height")
            if i % 2 == 0:
                if width is not None or height is not None:
                    raise ValueError("startFrame must not claim rendered screen dimensions")
            else:
                if (type(width) is not int or type(height) is not int
                        or not 0 < width <= 512 or not 0 < height <= 512):
                    raise ValueError("Invalid rendered screen dimensions")
                screen_path = path.parent / expected_names["screen_rgb"]
                screen_data = screen_path.read_bytes()
                if len(screen_data) != width * height * 3:
                    raise ValueError("Rendered RGB24 buffer dimensions/size mismatch")
                checksums["screen_rgb"] = hashlib.sha256(screen_data).hexdigest()
        output.append({
            "event": snap["event"], "frame_count": frame, "master_clock": clock,
            "ppu_scanline": scanline, "ppu_cycle": cycle,
            "sprite_height": snap["sprite_height"],
            "screen_width": width, "screen_height": height,
            "sha256": checksums,
            "lower_nonzero": sum(v != 0 for v in ppu_data[:4096]),
            "upper_nonzero": sum(v != 0 for v in ppu_data[4096:]),
            "model": None,
        })

    write_clock_last = -1
    clean_writes: list[dict[str, int]] = []
    for write in writes:
        if not isinstance(write, dict):
            raise ValueError("MMC3 write must be an object")
        clock = _nonnegative(write.get("master_clock"), "write clock")
        address = _integer(write.get("address"), "write address")
        value = _integer(write.get("value"), "write value")
        frame = _nonnegative(write.get("frame_count"), "write frame_count")
        scanline = _integer(write.get("ppu_scanline"), "write scanline")
        cycle = _integer(write.get("ppu_cycle"), "write cycle")
        if not 0x8000 <= address <= 0x9FFF or not 0 <= value <= 255:
            raise ValueError("Write is outside MMC3 bank-selection range")
        if clock <= write_clock_last or not output[0]["master_clock"] < clock < output[-1]["master_clock"]:
            raise ValueError("MMC3 writes must be chronologically ordered within the session")
        write_clock_last = clock
        clean_writes.append({
            "master_clock": clock, "address": address, "value": value,
            "frame": frame, "ppu_scanline": scanline, "ppu_cycle": cycle,
        })

    report: dict[str, Any] = {
        "result": "pass_structural_phase_capture_validation",
        "session_id": session,
        "verified_smb3_rom_provided": False,
        "rom_sha1_reported_by_mesen": mesen_rom_sha1,
        "capture_tool": capture_tool,
        "capture_count": len(output),
        "captured_frames": [frames[0], frames[2]],
        "blob_count": len(output) * len(SIZES) + (2 if is_render else 0),
        "mmc3_writes": len(clean_writes),
        "dropped_writes": dropped,
        "snapshots": output,
        "mapper_model_status": "not_attempted_no_verified_rom",
        "model_matches": 0,
        "model_mismatches": 0,
        "model_unknown_snapshots": len(output),
        "not_proven": [
            "startFrame state is not the set of pixels fetched throughout the visible frame",
            "OAM/palette/PPU capture and final rendered pixels are not synchronously proven",
            "emulator save-state and input replay reproducibility",
        ],
    }
    if rom_path is None:
        return report

    chr_rom, sha1, rom_sha256, chr_offset = load_chr(
        Path(rom_path), require_smb3=not allow_synthetic_rom
    )
    if sha1.upper() != mesen_rom_sha1.upper():
        raise ValueError("Emulator ROM SHA-1 does not match supplied ROM")
    report["verified_smb3_rom_provided"] = not allow_synthetic_rom
    report["rom_sha256"] = rom_sha256
    if dropped:
        report["mapper_model_status"] = "unavailable_dropped_register_writes"
        return report

    modeled_trace = {
        "schema_version": 1, "tool": "spritemine-mmc3-register-trace-v1",
        "rom_sha1": mesen_rom_sha1,
        "dropped_writes": 0,
        "writes": clean_writes,
        "boundaries": [
            {
                "event": snap["event"], "frame": snap["frame_count"],
                "master_clock": snap["master_clock"],
                "ppu_scanline": snap["ppu_scanline"], "ppu_cycle": snap["ppu_cycle"],
            }
            for snap in output
        ],
    }
    try:
        modeled = analyze_trace(
            modeled_trace, chr_rom, rom_sha1=sha1, chr_rom_file_offset=chr_offset
        )
    except ValueError as exc:
        report["mapper_model_status"] = "unavailable_partial_or_ambiguous_trace"
        report["mapper_model_limitation"] = str(exc)
        return report

    known = 0
    mismatches = 0
    for observed, predicted in zip(output, modeled["boundaries"], strict=True):
        mapping = predicted["mapping"]
        if mapping is None:
            continue
        known += 1
        match = observed["sha256"]["ppu_pattern"] == mapping["ppu_pattern_sha256"]
        mismatches += int(not match)
        observed["model"] = {
            "matches_full_8k_ppu": match,
            "physical_1k_banks": mapping["physical_1k_bank_per_ppu_slot"],
            "source_rom_offsets_per_ppu_slot": mapping["source_rom_offsets_per_ppu_slot"],
            "expected_ppu_sha256": mapping["ppu_pattern_sha256"],
        }
    report["model_matches"] = known - mismatches
    report["model_mismatches"] = mismatches
    report["model_unknown_snapshots"] = len(output) - known
    report["mapper_model_status"] = (
        "mismatch" if mismatches else
        "matches_known_boundaries" if known else
        "unavailable_missing_initial_register_state"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate paired MesenCE PPU state and mapper changes")
    parser.add_argument("manifest", type=Path, help="Exact phase_*.json session manifest")
    parser.add_argument("--rom", type=Path, help="Local verified SMB3 PRG1 NES/ZIP (never uploaded)")
    args = parser.parse_args(argv)
    try:
        report = verify_phase_session(args.manifest, args.rom)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"SpriteMine phase capture invalid: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 3 if report["model_mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
