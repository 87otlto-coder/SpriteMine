"""Read-only SMB3 PRG1 player-pattern recipes, not a complete sprite renderer.

Offsets were matched against Southbird's PRG029 tables and the verified ROM.
The six table components require game-specific clipping, mirroring, priority,
bank selection and OAM allocation before they become visible sprites.
No copyrighted pattern table or graphics bytes are embedded here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from .decode_mmc3_trace import EXPECTED_SMB3_SHA256
from .runtime_patterns import decode_pattern_records

DECODER = "spritemine.smb3-prg1.player-recipe/1"
OFFSETS = 0x3AC10
PATTERNS = 0x3AC61
PAGES = 0x3AE47
FRAME_COUNT = 81
TABLE_HASHES = {
    "offsets": "6244cf2be9719ef22a1ada5357104eb781864d9b107a30b0d3b6acfc675fc240",
    "patterns": "4c655ba8a75e38616af7567e99867b697485ab1bf663a52e59643e0fec7606b5",
    "pages": "b9e1db86cd863b6b7977b0623276163d2edbeaecce7dac40a330ec90b2b1ebd3",
}


def _decode_tables(offsets: bytes, patterns: bytes, pages: bytes, frame: int) -> dict:
    """Interpret the actual doubled-offset/biased-pointer lookup algorithm."""
    if type(frame) is not int or not 0 <= frame < FRAME_COUNT:
        raise ValueError("Player frame must be an integer from 0 through 80")
    if len(offsets) != FRAME_COUNT or len(pages) != FRAME_COUNT or len(patterns) != 486:
        raise ValueError("Truncated or unsupported player tables")
    index = offsets[frame] * 2 - 4
    if index < 0 or index + 6 > len(patterns):
        raise ValueError("Player recipe points outside the verified pattern table")
    record, = decode_pattern_records(patterns, index, 1)
    # The routine writes the first table row to OAM slots +3,+4,+5;
    # the second table row to +0,+1,+2. F1 is game-level suppression.
    return {
        "frame": frame,
        "chr_page_offset": pages[frame],
        "pattern_table_index": index,
        "components": [
            {"table_component": i, "relative_oam_slot": (i + 3) % 6,
             "column": i % 3, "row": i // 3,
             "tile_id": record['slots'][i]['tile_id'],
             "suppressed_by_game_marker": record['slots'][i]['suppressed'],
             "source_rom_offset": PATTERNS + index + i}
            for i in range(6)
        ],
    }


def read_recipe(rom_file: Path, frame: int) -> dict:
    """Return source-backed data only for the exact accepted immutable .nes."""
    data = Path(rom_file).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SMB3_SHA256:
        raise ValueError("Expected verified SMB3 US PRG1 ROM SHA-256")
    tables = {"offsets": data[OFFSETS:PATTERNS],
              "patterns": data[PATTERNS:PAGES],
              "pages": data[PAGES:PAGES + FRAME_COUNT]}
    for name, table in tables.items():
        if hashlib.sha256(table).hexdigest() != TABLE_HASHES[name]:
            raise ValueError(f"Player {name} table fingerprint mismatch")
    result = _decode_tables(tables["offsets"], tables["patterns"], tables["pages"], frame)
    return {"decoder": DECODER, "provenance": "decoded", "rom_sha256": digest,
            "prg_bank_8k": 29, "table_sha256": TABLE_HASHES.copy(), **result,
            "limitations": ["Not final OAM or a rendered metasprite",
                            "No runtime frame-identity claim",
                            "CHR bank, attributes, clipping and special cases need runtime evidence"]}
