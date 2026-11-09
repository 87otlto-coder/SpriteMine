"""Analyze an MMC3 Lua write trace using local, immutable CHR-ROM bytes.

No graphics data are exported. The decoder models bank register effects *after*
pre-write callbacks and compares predicted PPU mapping at recorded frame events.
It does not claim rendering-scanline pixel provenance or mapper-state atomicity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

EXPECTED_SMB3_SHA256 = "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"
TRACE_TOOL = "spritemine-mmc3-register-trace-v1"
MAX_ROM_BYTES = 64 * 1024 * 1024


def load_chr(path: Path, *, require_smb3: bool = True) -> tuple[bytes, str, str, int]:
    """Load iNES CHR-ROM without writing or extracting the input file."""
    if path.suffix.lower() == ".nes":
        if path.stat().st_size > MAX_ROM_BYTES:
            raise ValueError("ROM exceeds safety limit")
        data = path.read_bytes()
    elif path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            candidates = [
                item for item in archive.infolist()
                if not item.is_dir() and item.filename.lower().endswith(".nes")
            ]
            if len(candidates) != 1 or candidates[0].file_size > MAX_ROM_BYTES:
                raise ValueError("ZIP must contain exactly one size-limited .nes file")
            with archive.open(candidates[0]) as source:
                data = source.read(MAX_ROM_BYTES + 1)
    else:
        raise ValueError("ROM must be a .nes or single-ROM .zip")
    if len(data) > MAX_ROM_BYTES or len(data) < 16 or data[:4] != b"NES\x1a":
        raise ValueError("Missing, oversized, or invalid iNES ROM")
    if data[7] & 0x0C:
        raise ValueError("Unsupported NES header variant")
    sha256 = hashlib.sha256(data).hexdigest()
    sha1 = hashlib.sha1(data).hexdigest().upper()
    if require_smb3 and sha256 != EXPECTED_SMB3_SHA256:
        raise ValueError("Provided ROM is not verified SMB3 US PRG1 / Revision A")
    start = 16 + (512 if data[6] & 0x04 else 0) + data[4] * 16384
    size = data[5] * 8192
    if size == 0 or len(data) < start + size:
        raise ValueError("No static CHR-ROM or truncated ROM")
    return data[start:start + size], sha1, sha256, start


def pattern_at_boundary(
    chr_rom: bytes, select: int | None, registers: list[int | None], *,
    chr_rom_file_offset: int = 0,
) -> dict[str, Any] | None:
    """Map PPU 0x0000-0x1FFF through known MMC3 R0-R5 register values."""
    if select is None or any(x is None for x in registers[:6]):
        return None
    r = [int(v) for v in registers[:6]]
    # R0/R1 choose even-aligned 2 KiB pairs, while R2-R5 choose 1 KiB banks.
    two_k = [(r[0] & 0xFE), (r[0] & 0xFE) + 1,
             (r[1] & 0xFE), (r[1] & 0xFE) + 1]
    one_k = r[2:6]
    bank_numbers = (one_k + two_k) if (select & 0x80) else (two_k + one_k)
    count = len(chr_rom) // 1024
    if len(chr_rom) % 1024 or any(not 0 <= bank < count for bank in bank_numbers):
        raise ValueError("MMC3 CHR mapping references an unsupported ROM bank")
    chunks = [chr_rom[bank * 1024:(bank + 1) * 1024] for bank in bank_numbers]
    pattern = b"".join(chunks)
    return {
        "chr_inversion_mode": 1 if select & 0x80 else 0,
        "bank_registers_r0_to_r5": r,
        "physical_1k_bank_per_ppu_slot": bank_numbers,
        "source_chr_offsets_per_ppu_slot": [bank * 1024 for bank in bank_numbers],
        "source_rom_offsets_per_ppu_slot": [chr_rom_file_offset + bank * 1024 for bank in bank_numbers],
        "lower_nonzero": sum(value != 0 for value in pattern[:4096]),
        "upper_nonzero": sum(value != 0 for value in pattern[4096:]),
        "ppu_pattern_sha256": hashlib.sha256(pattern).hexdigest(),
    }


def analyze_trace(
    trace: dict[str, Any], chr_rom: bytes, *, rom_sha1: str | None = None,
    chr_rom_file_offset: int = 0,
) -> dict[str, Any]:
    if trace.get("tool") != TRACE_TOOL or trace.get("schema_version") != 1:
        raise ValueError("Unsupported MMC3 trace format")
    if rom_sha1 is not None and trace.get("rom_sha1", "").upper() != rom_sha1.upper():
        raise ValueError("Trace ROM SHA-1 differs from the supplied ROM")
    if not isinstance(trace.get("writes"), list) or not isinstance(trace.get("boundaries"), list):
        raise ValueError("Missing writes or frame boundaries")

    events: list[tuple[int, int, str, dict[str, Any]]] = []
    for index, write in enumerate(trace["writes"]):
        if type(write.get("master_clock")) is not int or type(write.get("address")) is not int or type(write.get("value")) is not int:
            raise ValueError("Malformed MMC3 register write")
        if not 0x8000 <= write["address"] <= 0x9FFF or not 0 <= write["value"] <= 255:
            raise ValueError("MMC3 write address/value outside scope")
        events.append((write["master_clock"], index, "write", write))
    for index, boundary in enumerate(trace["boundaries"]):
        if type(boundary.get("master_clock")) is not int or boundary.get("event") not in ("startFrame", "endFrame"):
            raise ValueError("Malformed frame boundary")
        events.append((boundary["master_clock"], index, "boundary", boundary))
    if len({clock for clock, _, _, _ in events}) != len(events):
        raise ValueError("Ambiguous event ordering: duplicate master clocks")
    events.sort(key=lambda x: x[0])

    registers: list[int | None] = [None] * 8
    select: int | None = None
    boundaries: list[dict[str, Any]] = []
    chr_writes = 0
    prg_writes = 0
    for _, _, kind, event in events:
        if kind == "write":
            if event["address"] & 1:
                if select is None:
                    raise ValueError("Bank data write has no preceding bank selection in trace")
                register = select & 7
                registers[register] = event["value"]
                if register < 6:
                    chr_writes += 1
                else:
                    prg_writes += 1
            else:
                select = event["value"]
        else:
            boundaries.append({
                "event": event["event"],
                "frame": event.get("frame"),
                "master_clock": event["master_clock"],
                "ppu_scanline": event.get("ppu_scanline"),
                "ppu_cycle": event.get("ppu_cycle"),
                "mapping": pattern_at_boundary(
                    chr_rom, select, registers, chr_rom_file_offset=chr_rom_file_offset
                ),
            })
    warnings = [
        "MMC3 write callbacks are pre-write; effects are modeled after each timestamped write",
        "Unknown bank registers at trace start remain unresolved until explicitly written",
        "PPU bank mapping at a boundary is not proof of mapping used for every rendered scanline",
    ]
    if trace.get("dropped_writes", 0):
        warnings.append("Some writes were dropped; reconstructed mappings may be incomplete")
    return {
        "result": "modeled_mmc3_chr_boundary_mapping",
        "trace_rom_sha1": trace.get("rom_sha1"),
        "writes_total": len(trace["writes"]),
        "chr_bank_data_writes": chr_writes,
        "prg_bank_data_writes": prg_writes,
        "dropped_writes": trace.get("dropped_writes", 0),
        "boundaries": boundaries,
        "not_proven": warnings,
    }


def compare_capture_zip(report: dict[str, Any], archive_path: Path) -> list[dict[str, Any]]:
    """Compare private PPU snapshots to modeled boundary *hashes* only."""
    expected_by_hash: dict[str, list[str]] = {}
    for boundary in report["boundaries"]:
        mapping = boundary["mapping"]
        if mapping:
            expected_by_hash.setdefault(mapping["ppu_pattern_sha256"], []).append(
                f'{boundary["event"]} frame {boundary["frame"]}'
            )
    matches: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive_path) as archive:
        candidates = [m for m in archive.infolist() if m.filename.endswith("_ppu_pattern.bin") and not m.is_dir()]
        if not candidates:
            raise ValueError("Capture ZIP lacks PPU pattern snapshots")
        for member in candidates:
            if member.file_size != 8192:
                raise ValueError("Unexpected PPU snapshot length")
            with archive.open(member) as file:
                data = file.read(8193)
            if len(data) != 8192:
                raise ValueError("Truncated PPU snapshot")
            digest = hashlib.sha256(data).hexdigest()
            matches.append({
                "capture_file": Path(member.filename).name,
                "ppu_pattern_sha256": digest,
                "matches_modeled_boundaries": expected_by_hash.get(digest, []),
            })
    return matches


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Model MMC3 CHR bank mapping against a local SMB3 ROM")
    parser.add_argument("trace", type=Path)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--capture-zip", type=Path, help="Optional private captured PPU snapshots; compares SHA-256 only")
    args = parser.parse_args(argv)
    try:
        chr_rom, sha1, sha256, chr_offset = load_chr(args.rom)
        report = analyze_trace(
            json.loads(args.trace.read_text(encoding="utf-8")), chr_rom,
            rom_sha1=sha1, chr_rom_file_offset=chr_offset,
        )
        report["verified_rom_sha256"] = sha256
        if args.capture_zip is not None:
            report["cross_session_ppu_hash_comparison"] = compare_capture_zip(report, args.capture_zip)
            report["not_proven"].append("Cross-session byte matches do not prove identical game states")
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"MMC3 mapping analysis failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
