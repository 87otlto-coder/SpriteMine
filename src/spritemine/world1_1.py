"""World 1-1 bonus-room logical construction from the verified PRG1 stream."""

from collections import Counter
from hashlib import sha256
from pathlib import Path

from .player import _provenance
from .rom import Rom

MAIN_HEADER = 0x1FB92
BONUS_HEADER = 0x1FCA3
STREAM = BONUS_HEADER + 9
END = 0x1FCF9
SCREEN_BYTES = 16 * 27
MODEL_SHA256 = "c57b72c77899d596745065c90878327993f9a25e6289c0b22d960c58021b088a"


def _build_bonus(stream: bytes) -> tuple[bytes, list[dict]]:
    tiles = bytearray([0x80] * (2 * SCREEN_BYTES))
    commands = []

    def put(x: int, y: int, tile: int) -> None:
        if not (0 <= x < 32 and 0 <= y < 27):
            raise ValueError("Bonus room tile write outside the two-screen layout")
        tiles[x // 16 * SCREEN_BYTES + y * 16 + x % 16] = tile

    cursor = 0
    while cursor < len(stream):
        if stream[cursor] == 0xFF and cursor == len(stream) - 1:
            return bytes(tiles), commands
        if len(stream) - cursor < 4:
            break
        first, x, shape = stream[cursor:cursor + 3]
        offset = cursor
        cursor += 3
        if first & 0xF0 == 0xE0:
            commands.append({"rom_offset": STREAM + offset, "junction_slot": first & 15,
                             "y_descriptor": x, "x_descriptor": shape})
            continue
        generator = (first >> 5) * 15 + (shape >> 4) - 1
        y = first & 31
        extent = (shape & 15) + 1
        command = {"rom_offset": STREAM + offset, "generator": generator, "x": x, "y": y}
        if generator == 40:
            width = stream[cursor] + 1
            cursor += 1
            command.update(width=width, height=extent)
            for dy in range(extent):
                for dx in range(width):
                    put(x + dx, y + dy, 0xF0)
        elif generator == 22:
            command["width"] = extent
            for dx in range(extent):
                put(x + dx, y, 0x40)
        elif generator in (26, 27) and extent == 2:
            cap = 0xAD if generator == 26 else 0xB1
            for dx in range(2):
                put(x + dx, y, 0xBA + dx)
                put(x + dx, y + 1, cap + dx)
        else:
            raise ValueError(f"Unsupported bonus generator {generator} at stream offset {offset:#x}")
        commands.append(command)
    raise ValueError("Bonus stream requires a terminal 0xFF and complete commands")


def reconstruct_bonus(rom: Rom) -> tuple[dict, bytes]:
    provenance = _provenance(rom)
    stream = rom.image[STREAM:END]
    tiles, commands = _build_bonus(stream)
    headers = []
    for offset in (MAIN_HEADER, BONUS_HEADER):
        header = rom.image[offset:offset + 9]
        headers.append({"rom_offset": offset, "alternate_layout_cpu": int.from_bytes(header[:2], "little"),
                        "alternate_objects_cpu": int.from_bytes(header[2:4], "little"),
                        "screen_count": (header[4] & 15) + 1})
    return ({
        **provenance, "decoder": "spritemine.world1_1.bonus/1",
        "area": "world-1-1-bonus", "evidence": "source_model", "runtime_verified": False,
        "map_order": "screen_then_row_then_column", "screen_width": 16, "screen_height": 27,
        "headers": headers, "commands": commands, "stream_sha256": sha256(stream).hexdigest(),
        "tile_counts": dict(sorted(Counter(tiles).items())), "map_sha256": sha256(tiles).hexdigest(),
    }, tiles)


def compare_bonus(tiles: bytes, dump: Path) -> dict:
    """Compare supplied bytes without assigning capture provenance to the dump."""
    with dump.open("rb") as stream:
        observed = stream.read(len(tiles) + 1)
    if len(observed) != len(tiles):
        raise ValueError(f"Tile_Mem dump must be exactly {len(tiles)} bytes")
    mismatches = [i for i, (expected, actual) in enumerate(zip(tiles, observed)) if expected != actual]
    return {"matches": not mismatches, "dump_sha256": sha256(observed).hexdigest(),
            "mismatch_count": len(mismatches), "first_difference": mismatches[0] if mismatches else None}
