"""Source-verified World 1-1 header only; no terrain/level reconstruction claim."""
from __future__ import annotations
import hashlib
from pathlib import Path
from .decode_mmc3_trace import EXPECTED_SMB3_SHA256

WORLD_1_1 = 0x1FB92
STREAM_SIZE = 264
STREAM_SHA256 = "ef2d1e5a95cd51391e5651af0cdd9ab0cba36985e4cf971d3eed7c34d506892a"


def decode_header(header: bytes) -> dict:
    if len(header) != 9:
        raise ValueError("Expected exactly nine level-header bytes")
    a,b,c,d,e = header[4:]
    return {
        "alternate_layout_cpu_pointer": int.from_bytes(header[:2], 'little'),
        "alternate_object_cpu_pointer": int.from_bytes(header[2:4], 'little'),
        "length_in_screens": (a & 15)+1,
        "player_start_y_selector": a >> 5,
        "player_start_y": (0x170,0x40,0,0x140,0x70,0xb0,0xf0,0x180)[a >> 5],
        "two_player_flag": bool(a & 16),
        "background_palette_set": b & 7,
        "object_palette_set": 8 + ((b >> 3) & 3),
        "player_start_x": (0x18,0x70,0xd8,0x80)[(b >> 5) & 3],
        "unused_flag": bool(b & 128),
        "alternate_tileset": c & 15,
        "vertical_level": bool(c & 16),
        "vertical_scroll_mode": (c >> 5) & 3,
        "pipe_not_exit_flag": bool(c & 128),
        "background_bank_index": d & 31,
        "initial_action": d >> 5,
        "music_selector": e & 15,
        "timer_selector": e >> 6,
        "timer_start": (300,400,200,0)[e >> 6],
        "uninterpreted_music_byte_bits": (e >> 4) & 3,
    }


def read_world_1_1(rom_file: Path) -> dict:
    data = Path(rom_file).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SMB3_SHA256:
        raise ValueError("Expected verified SMB3 US PRG1 ROM SHA-256")
    stream = data[WORLD_1_1+9:WORLD_1_1+9+STREAM_SIZE]
    if len(stream) != STREAM_SIZE or hashlib.sha256(stream).hexdigest() != STREAM_SHA256:
        raise ValueError("World 1-1 source-record fingerprint mismatch")
    return {"decoder": "spritemine.smb3-prg1.level-header/1",
            "provenance": "decoded", "rom_sha256": digest,
            "header_rom_offset": WORLD_1_1, "prg_bank_8k": 15,
            "header_cpu_address_when_bank_at_a000": 0xBB82,
            "header_sha256": hashlib.sha256(data[WORLD_1_1:WORLD_1_1+9]).hexdigest(),
            "object_stream_rom_offset": WORLD_1_1+9,
            "object_stream_length": STREAM_SIZE, "object_stream_sha256": STREAM_SHA256,
            "header": decode_header(data[WORLD_1_1:WORLD_1_1+9]),
            "limitations": ["Header interpretation checked against disassembly, not runtime loader execution",
                            "Object command boundaries and terrain are not decoded",
                            "No metatile, collision, enemy-layout or rendered-level verification"]}
