"""Import existing MesenCE pattern staging strips into a private scene bundle."""

import argparse
import csv
import hashlib
import json
import tempfile
from pathlib import Path

from .scene_input import adapt, load_json

# Source format: research/mesence/verify_background_staging.py (PR #23).
COLUMNS = (
    "sequence", "kind", "frame", "cpu_cycle", "scanline", "ppu_cycle", "poll",
    "direction", "column", "half", "last_ppu_column", "last_attribute",
    "junction_flag", "tileset",
)
ROWS, COLUMNS_PER_SCREEN = 27, 16
PLAYFIELD_TILE = 16


def fingerprint(data):
    return hashlib.sha256(data).hexdigest()


def collect_columns(folder, frame, screens, log_hash):
    raw = (folder / "background-staging.tsv").read_bytes()
    if fingerprint(raw) != log_hash:
        raise ValueError("staging log hash differs from replay report")
    reader = csv.DictReader(raw.decode("ascii").splitlines(), delimiter="\t")
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise ValueError("unexpected native staging event schema")
    halves, sources = {}, {}
    for sequence, row in enumerate(reader, 1):
        if None in row or None in row.values():
            raise ValueError("incomplete native staging event")
        kind = row.pop("kind")
        event = {key: int(value) for key, value in row.items()}
        if event["sequence"] != sequence or kind not in ("pattern", "attribute"):
            raise ValueError("unsupported staging event or sequence")
        if event["frame"] != frame or kind != "pattern":
            continue
        column, half = event["column"], event["half"]
        if (not 0 <= column < screens * COLUMNS_PER_SCREEN or half not in (0, 1)
                or event["direction"] not in (0, 1) or event["tileset"] != 1
                or event["last_ppu_column"] != (column % COLUMNS_PER_SCREEN) * 2 + half):
            raise ValueError(f"inconsistent Plains pattern stage at event {sequence}")
        stem = f"bg-{sequence:04d}"
        patterns = (folder / f"{stem}-pattern.bin").read_bytes()
        logical = (folder / f"{stem}-tiles.bin").read_bytes()
        if len(patterns) != ROWS * 2 or len(logical) != screens * COLUMNS_PER_SCREEN * ROWS:
            raise ValueError(f"unexpected pattern or logical length at event {sequence}")
        screen, local = divmod(column, COLUMNS_PER_SCREEN)
        start = screen * COLUMNS_PER_SCREEN * ROWS + local
        ids = logical[start:start + ROWS * COLUMNS_PER_SCREEN:COLUMNS_PER_SCREEN]
        key = (column, half)
        if key in halves and halves[key] != (patterns, ids):
            raise ValueError(f"conflicting pattern uploads for column {column}, half {half}")
        halves[key] = patterns, ids
        sources[str(sequence)] = {
            "column": column, "half": half, "cpu_cycle": event["cpu_cycle"],
            "patterns_sha256": fingerprint(patterns), "logical_sha256": fingerprint(logical),
        }
    if not halves:
        raise ValueError("no supported pattern uploads at the selected staging frame")
    return halves, sources


def import_staging(capture, frame, graphics_frame, profile, destination, *, screens):
    """Import one staging frame with an explicitly selected graphics snapshot.

    The mapped PPU dump carries the eight CHR windows in fetch-address order.
    Selection of a stable graphics frame is an upstream evidence decision.
    """
    if not 1 <= screens <= 16 or min(frame, graphics_frame) < 0:
        raise ValueError("expected 1–16 screens and nonnegative frame numbers")
    report = load_json(capture / "report.json")
    if report.get("neutral") is not True:
        raise ValueError("expected a neutral A/B/A replay report")
    folder = capture / "B"
    log_hash = report["background_staging"]["log_sha256"]
    halves, sources = collect_columns(folder, frame, screens, log_hash)
    prefix = f"{graphics_frame}-start"
    ppu = (folder / f"{prefix}-ppu.bin").read_bytes()
    palette = (folder / f"{prefix}-palette.bin").read_bytes()
    rgb = profile.read_bytes()
    if (len(ppu) != 0x3000 or len(palette) != 32 or max(palette) > 63
            or len(rgb) != 192):
        raise ValueError("invalid mapped PPU, palette RAM or RGB profile length/value")
    state_bytes = (folder / f"{prefix}-ppu-state.txt").read_bytes()
    state = {}
    for line in state_bytes.decode("ascii").splitlines():
        key, value = line.split("=", 1)
        if key in state:
            raise ValueError("duplicate PPU state field")
        state[key] = value
    base = int(state["ppu.control.backgroundPatternAddr"])
    if base not in (0, 0x1000):
        raise ValueError("invalid background pattern table base")
    if (state["ppu.mask.grayscale"] != "false" or int(state["ppu.paletteRamMask"]) != 63
            or int(state["ppu.intensifyColorBits"]) != 0):
        raise ValueError("unsupported grayscale or emphasis state")

    columns = screens * COLUMNS_PER_SCREEN
    tiles = [[None] * columns for _ in range(ROWS)]
    assets = {}
    provenance = {
        "decoder": "mesence_plains_staging_v1", "capture": capture.name,
        "staging_frame": frame, "graphics_frame": graphics_frame,
        "staging_log_sha256": log_hash, "ppu_sha256": fingerprint(ppu),
        "palette_sha256": fingerprint(palette), "profile_sha256": fingerprint(rgb),
        "ppu_state_sha256": fingerprint(state_bytes),
        "rom_sha256": report.get("source_sha256", {}).get("rom"),
        "pattern_table_base": base, "events": sources,
        "mapped_chr_window_sha256": [fingerprint(ppu[i:i + 1024])
                                     for i in range(0, 8192, 1024)],
    }
    for column in range(columns):
        if (column, 0) not in halves or (column, 1) not in halves:
            continue
        left, left_ids = halves[column, 0]
        right, right_ids = halves[column, 1]
        if left_ids != right_ids:
            raise ValueError(f"logical tile snapshots disagree at column {column}")
        for row, tile in enumerate(left_ids):
            top = row * 2
            patterns = (left[top], right[top], left[top + 1], right[top + 1])
            offsets = [base + pattern * 16 for pattern in patterns]
            key = f"{tile:02x}-" + "".join(f"{pattern:02x}" for pattern in patterns)
            group = tile >> 6
            codes = [palette[0], *palette[group * 4 + 1:group * 4 + 4]]
            assets.setdefault(key, {
                "file": "mapped-chr.bin", "chr": {"offsets": offsets, "grid": [2, 2]},
                "palette": [list(rgb[code * 3:code * 3 + 3]) + [255] for code in codes],
                "provenance": {"logical_id": tile, "mapped_ppu_offsets": offsets,
                               "palette_group": group, "palette_codes": codes},
            })
            tiles[row][column] = key
    spec = {
        "version": 1, "size": [columns * PLAYFIELD_TILE, ROWS * PLAYFIELD_TILE],
        "tile_size": [PLAYFIELD_TILE, PLAYFIELD_TILE], "ticks": 1, "tick_ms": 20,
        "background": list(rgb[palette[0] * 3:palette[0] * 3 + 3]), "assets": assets,
        "layers": [{"tiles": tiles}], "staging_provenance": provenance,
    }
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "mapped-chr.bin").write_bytes(ppu[:8192])
        descriptor = root / "descriptor.json"
        descriptor.write_text(json.dumps(spec, sort_keys=True), encoding="utf-8")
        return adapt(descriptor, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("frame", type=int)
    parser.add_argument("graphics_frame", type=int)
    parser.add_argument("profile", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--screens", type=int, required=True)
    args = parser.parse_args()
    try:
        print(import_staging(args.capture, args.frame, args.graphics_frame,
                             args.profile, args.destination, screens=args.screens))
    except (KeyError, ValueError, OSError) as exc:
        parser.exit(2, f"native staging: {exc}\n")


if __name__ == "__main__":
    main()
