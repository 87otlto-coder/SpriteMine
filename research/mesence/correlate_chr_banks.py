"""Match captured 1-KiB PPU pattern windows to source ROM and MMC3 trace.

Writes are pre-write callbacks: modeled layouts are post-write *predictions*.
Captured snapshots and traces can originate from different sessions. Outputs
contain only derived metadata, never ROM bytes or image pixels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

WINDOW_BYTES = 1024
PPU_PATTERN_BYTES = 8192


def inspect_pattern(chr_rom: bytes, pattern: bytes) -> list[dict[str, object]]:
    if len(pattern) != PPU_PATTERN_BYTES:
        raise ValueError("Captured PPU pattern must contain exactly 8192 bytes")
    if not chr_rom or len(chr_rom) % WINDOW_BYTES:
        raise ValueError("CHR-ROM must contain complete 1024-byte banks")
    physical = [chr_rom[i:i + WINDOW_BYTES] for i in range(0, len(chr_rom), WINDOW_BYTES)]
    windows = []
    for slot in range(8):
        data = pattern[slot * WINDOW_BYTES:(slot + 1) * WINDOW_BYTES]
        matched = [index for index, page in enumerate(physical) if page == data]
        windows.append({
            "ppu_start": slot * WINDOW_BYTES,
            "physical_1k_chr_bank_matches": matched,
            "unique_match": len(matched) == 1,
            "nonzero_bytes": sum(x != 0 for x in data),
        })
    return windows


def expected_mmc3_pages(registers: dict[int, int], chr_mode: int) -> list[int]:
    """Model MesenCE MMC3::UpdateChrMapping: bit 7 sets CHR mode, bit 6 PRG mode."""
    if chr_mode not in (0, 1) or any(i not in registers for i in range(6)):
        raise ValueError("Need CHR mode 0 or 1 and bank registers R0..R5")
    r = registers
    pair0 = [r[0] & 0xFE, (r[0] & 0xFE) + 1]
    pair1 = [r[1] & 0xFE, (r[1] & 0xFE) + 1]
    singles = [r[2], r[3], r[4], r[5]]
    return pair0 + pair1 + singles if chr_mode == 0 else singles + pair0 + pair1


def trace_chr_mappings(trace: dict[str, object]) -> list[dict[str, object]]:
    """Predict CHR layouts only after all six register values were witnessed."""
    if trace.get("tool") != "spritemine-mmc3-register-trace-v1":
        raise ValueError("Not a supported MMC3 trace")
    rows = trace.get("writes")
    if not isinstance(rows, list):
        raise ValueError("MMC3 trace has no writes list")
    if trace.get("dropped_writes", 0):
        raise ValueError("Cannot reconstruct mappings from a truncated trace")
    regs: dict[int, int] = {}
    selected: int | None = None
    mode: int | None = None
    last_clock = -1
    layouts: list[dict[str, object]] = []
    last_pages: list[int] | None = None
    for row in rows:
        clock = row["master_clock"]
        if not isinstance(clock, int) or clock <= last_clock:
            raise ValueError("Trace writes must have increasing integer master clocks")
        last_clock = clock
        address, value = row["address"], row["value"]
        if not (isinstance(value, int) and 0 <= value <= 255):
            raise ValueError("MMC3 write value must be an 8-bit integer")
        if address == 0x8000:
            selected = value & 7
            mode = (value >> 7) & 1
        elif address == 0x8001:
            if selected is None:
                raise ValueError("Bank-data write preceded observed bank-select")
            regs[selected] = value
        else:
            raise ValueError("Trace contains a non-bank-select/data address")
        if mode is not None and all(i in regs for i in range(6)):
            pages = expected_mmc3_pages(regs, mode)
            if pages != last_pages:
                layouts.append({
                    "after_write_master_clock": clock,
                    "frame": row["frame"],
                    "ppu_scanline": row["ppu_scanline"],
                    "ppu_cycle": row["ppu_cycle"],
                    "chr_mode_bit7": mode,
                    "modeled_ppu_chr_bank_slots": pages,
                    "note": "Predicted post-write register layout; callback samples pre-write",
                })
                last_pages = pages
    return layouts


def correlate(rom_file: Path, pattern_file: Path, trace_file: Path) -> dict[str, object]:
    from spritemine.rom import load_rom

    rom = load_rom(rom_file)
    if rom.metadata.mapper != 4:
        raise ValueError("This experiment expects MMC3 mapper 4")
    trace = json.loads(trace_file.read_text(encoding="utf-8"))
    sha1 = hashlib.sha1(rom.image).hexdigest().upper()
    if trace.get("rom_sha1", "").upper() != sha1:
        raise ValueError("Trace ROM SHA-1 differs from supplied ROM")
    windows = inspect_pattern(rom.chr, pattern_file.read_bytes())
    mappings = trace_chr_mappings(trace)
    exact_matches = [
        layout for layout in mappings
        if all(index in windows[slot]["physical_1k_chr_bank_matches"]
               for slot, index in enumerate(layout["modeled_ppu_chr_bank_slots"]))
    ]
    return {
        "result": "metadata_only_chr_provenance_comparison",
        "source_rom_sha256": rom.metadata.rom_sha256,
        "trace_rom_sha1_matches_rom": True,
        "trace_writes": len(trace["writes"]),
        "trace_dropped_writes": trace["dropped_writes"],
        "snapshot_windows": windows,
        "modeled_layout_count": len(mappings),
        "layouts_matching_all_eight_snapshot_windows": exact_matches,
        "limitations": [
            "ROM/capture and trace may originate from different frames or sessions",
            "trace layouts are modeled after observed pre-write callbacks",
            "this is not proof of which PPU bytes were fetched on each visible scanline",
            "sprite identity, transparency, visibility and composite pixels not proven",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Match PPU snapshot to MMC3 source ROM banks")
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--pattern", type=Path, required=True)
    parser.add_argument("--trace", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(correlate(args.rom, args.pattern, args.trace), indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"CHR bank correlation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
