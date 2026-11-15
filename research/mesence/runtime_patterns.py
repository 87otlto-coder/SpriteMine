"""Read-only SMB3 US PRG1 player-pattern metadata; no game bytes bundled.

Source interpretation: Southbird SMB3 disassembly, PRG029 SPPF_Table.
https://github.com/captainsouthbird/smb3 (research attribution, no code copied).
These records describe six pattern slots, not final visible sprite geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROM_SHA256 = "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"
TABLE_OFFSET = 0x3AC61
RECORD_COUNT = 81
RECORD_SIZE = 6


def decode_pattern_records(data: bytes, offset: int, count: int) -> list[dict]:
    """Decode bounded six-slot records; 0xF1 means suppressed by game code.

    This primitive accepts synthetic data. Game identity is enforced separately.
    Slots are table order, not OAM order or a claim of visibility.
    """
    if type(offset) is not int or type(count) is not int or offset < 0 or count < 1:
        raise ValueError("Expected nonnegative integer offset and positive count")
    if offset > len(data) or count > (len(data) - offset) // RECORD_SIZE:
        raise ValueError("Pattern table exceeds input bounds")
    return [
        {"record_index": index, "file_offset": offset + index * RECORD_SIZE,
         "slots": [
             {"slot": slot, "tile_id": tile, "suppressed": tile == 0xF1}
             for slot, tile in enumerate(data[offset + index * 6:offset + (index + 1) * 6])
         ]}
        for index in range(count)
    ]


def inspect_rom(data: bytes) -> dict:
    digest = hashlib.sha256(data).hexdigest()
    if digest != ROM_SHA256:
        raise ValueError("Requires exact verified SMB3 US PRG1 whole-ROM SHA-256")
    records = decode_pattern_records(data, TABLE_OFFSET, RECORD_COUNT)
    return {"schema": "spritemine.smb3.player-patterns/1", "decoder": "runtime-patterns-v1",
            "provenance_type": "decoded", "rom_sha256": digest,
            "table_file_offset": TABLE_OFFSET, "prg_8k_bank": 29,
            "source_cpu_address_when_mapped": 0xCC51,
            "record_count": RECORD_COUNT,
            "table_sha256": hashlib.sha256(data[TABLE_OFFSET:TABLE_OFFSET + 486]).hexdigest(),
            "limitations": ["No live Player_Frame observation", "No final OAM geometry",
                            "No CHR mapping, palette, clipping or visibility decoding"],
            "records": records}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path, help="Private uncompressed .nes file (read only)")
    args = parser.parse_args()
    try:
        result = inspect_rom(args.rom.read_bytes())
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Pattern inspection failed: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

