"""Verify ROM-derived SMB3 bonus-room background RGB against private native frames.

Uses physical CIRAM, original PRG1 CHR ROM, MMC3 register-write history,
PPU temporary scroll state and palette RAM. The reference 2C02 RGB table is
read from a *separate* pinned MesenCE source file, not copied into SpriteMine.

The initial acceptance window is World 1-1 bonus entry, frames 450869-450881,
gameplay scanlines 0-191. HUD, OAM, other levels and per-dot timing are out
of scope and must not be reported as verified.
"""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from spritemine.player import ROM_SHA256
from spritemine.ppu_background import (
    Mmc3ChrRegisters, color_codes_to_rgb, read_2c02_rgb_profile,
    render_background_codes,
)
from spritemine.rom import load_rom
from spritemine.background import ciram_offset
from research.mesence.verify_ppu_commit_trace import (
    REG_FIELDS, _load_tsv, verify as verify_ciram,
)

FIRST_ACCEPTED = 450869
LAST_ACCEPTED = 450881
WIDTH = 256
HEIGHT = 192


def _start_mmc3_pages(events_path: Path, accepted: range) -> dict[int, tuple[int, ...]]:
    """Replay observed $8000/$8001 history and reject changing visible CHR banks."""
    mapper = Mmc3ChrRegisters()
    starts: dict[int, tuple[int, ...]] = {}
    unstable: set[int] = set()
    rendering_frame: int | None = None
    last_cycle = -1
    with events_path.open("r", encoding="ascii", newline="") as stream:
        for number, line in enumerate(stream, 1):
            pieces = line.rstrip("\r\n").split("\t")
            if len(pieces) != 7:
                raise ValueError(f"Malformed emulator event row {number}")
            kind, frame_text, cycle_text, scanline_text, _, address_text, value_text = pieces
            frame, cycle, scanline = int(frame_text), int(cycle_text), int(scanline_text)
            address, value = int(address_text), int(value_text)
            if cycle < last_cycle:
                raise ValueError("Emulator event clock order reversed")
            last_cycle = cycle
            if kind == "start":
                if frame in starts:
                    raise ValueError(f"Duplicate start-frame event {frame}")
                starts[frame] = mapper.pages()
                rendering_frame = frame
            elif kind == "end":
                if rendering_frame == frame:
                    rendering_frame = None
            elif kind == "mapper-write" and address in (0x8000, 0x8001):
                before = mapper.pages() if rendering_frame in accepted else None
                mapper.write(address, value)
                if (rendering_frame == frame and frame in accepted
                        and 0 <= scanline < HEIGHT and mapper.pages() != before):
                    unstable.add(frame)
    if unstable:
        raise ValueError(f"MMC3 CHR changed during sampled gameplay: {sorted(unstable)}")
    missing = set(accepted) - starts.keys()
    if missing:
        raise ValueError(f"Missing native start-frame CHR history: {sorted(missing)}")
    return {frame: starts[frame] for frame in accepted}


def _boundary_mirroring(path: Path) -> dict[tuple[int, str], int]:
    found: dict[tuple[int, str], int] = {}
    with path.open("r", encoding="ascii", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != (
            "frame", "boundary", "cpu_cycle", "mirroring_bit"
        ):
            raise ValueError("Unsupported physical CIRAM boundary schema")
        for row in reader:
            frame, side = int(row["frame"]), row["boundary"]
            bit = int(row["mirroring_bit"])
            if side not in ("start", "end") or bit not in (0, 1):
                raise ValueError("Unexpected native boundary or mirroring bit")
            key = frame, side
            if key in found:
                raise ValueError(f"Duplicate physical CIRAM boundary: {key}")
            found[key] = bit
    return found


def _ppu_state(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="ascii").splitlines():
        if "=" not in line:
            raise ValueError(f"Malformed PPU state record in {path.name}")
        key, value = line.split("=", 1)
        if key in values:
            raise ValueError("Duplicate PPU state value")
        values[key] = value
    return values


def _read_exact(path: Path, size: int) -> bytes:
    value = path.read_bytes()
    if len(value) != size:
        raise ValueError(f"{path.name}: expected {size} bytes, found {len(value)}")
    return value


def verify(rom, capture: Path, palette_source: Path,
           first: int = FIRST_ACCEPTED, last: int = LAST_ACCEPTED) -> dict:
    if not FIRST_ACCEPTED <= first <= last <= LAST_ACCEPTED:
        raise ValueError("Only the established SMB3 World 1-1 bonus viewport is accepted")
    if rom.metadata.rom_sha256 != ROM_SHA256:
        raise ValueError("Unexpected SMB3 PRG1 ROM identity")
    if not verify_ciram(rom, capture)["passed"]:
        raise ValueError("Parent native CPU/PPU/CIRAM acceptance has not passed")

    folder = capture / "B"
    frames = range(first, last + 1)
    source = palette_source.read_bytes()
    colors = read_2c02_rgb_profile(source.decode("utf-8-sig"))
    pages_by_frame = _start_mmc3_pages(folder / "events.tsv", frames)
    mirroring = _boundary_mirroring(folder / "ppu-ciram-boundaries.tsv")
    writes = _load_tsv(folder / "ppu-registers.tsv", REG_FIELDS, sequence=True)
    visible_palette_writes = {
        row["frame"] for row in writes
        if row["kind"] == "write" and row["register"] == 0x2007
        and 0 <= row["scanline"] < HEIGHT
        and 0x3F00 <= (row["video_ram_addr"] & 0x3FFF) < 0x4000
    }
    if visible_palette_writes.intersection(frames):
        raise ValueError("Palette RAM was written during sampled gameplay scanlines")
    details = []
    samples = 0
    differences = 0
    for frame in frames:
        key = (frame, "start")
        if key not in mirroring or (frame, "end") not in mirroring:
            raise ValueError(f"Missing physical CIRAM mirroring records at frame {frame}")
        if mirroring[key] != mirroring[(frame, "end")]:
            raise ValueError(f"Mid-frame nametable mirroring changed at frame {frame}")
        state = _ppu_state(folder / f"{frame}-start-ppu-state.txt")
        final_state = _ppu_state(folder / f"{frame}-end-ppu-state.txt")
        if any(state.get(k) != final_state.get(k) for k in (
            "ppu.mask.backgroundEnabled", "ppu.mask.backgroundMask",
            "ppu.control.backgroundPatternAddr", "ppu.mask.grayscale",
            "ppu.intensifyColorBits",
        )):
            raise ValueError(f"Unsupported change in PPU rendering state at {frame}")
        if state.get("ppu.mask.grayscale") != "false" or int(
            state.get("ppu.intensifyColorBits", "-1")
        ) != 0:
            raise ValueError(f"Grayscale/emphasis rendering unsupported at frame {frame}")
        if state.get("ppu.mask.backgroundEnabled") != "true":
            raise ValueError(f"Background rendering disabled at frame {frame}")
        mapped = _read_exact(folder / f"{frame}-start-ppu.bin", 0x3000)
        physical = _read_exact(folder / f"ppu-{frame}-start-ciram.bin", 2048)
        palette = _read_exact(folder / f"{frame}-start-palette.bin", 32)
        if palette != _read_exact(folder / f"{frame}-end-palette.bin", 32):
            raise ValueError(f"Native palette changed within the sampled frame {frame}")

        pages = pages_by_frame[frame]
        if any(
            rom.chr[page * 1024:page * 1024 + 1024] !=
            mapped[index * 1024:index * 1024 + 1024]
            for index, page in enumerate(pages)
        ):
            raise ValueError(f"MMC3 CHR register history disagrees with PPU bank snapshot: {frame}")
        mode = "horizontal" if mirroring[key] else "vertical"
        if any(
            physical[ciram_offset(address, mirroring=mode)] != mapped[address]
            for address in range(0x2000, 0x3000)
        ):
            raise ValueError(f"Start-frame PPU nametable alias discrepancy: {frame}")
        color_codes = render_background_codes(
            chr_rom=rom.chr, ciram=physical, palette_ram=palette,
            chr_pages=pages, mirroring_bit=mirroring[key],
            scroll_t=int(state["ppu.tmpVideoRamAddr"]),
            fine_x=int(state["ppu.xScroll"]),
            pattern_base=int(state["ppu.control.backgroundPatternAddr"]),
            background_enabled=True,
            left_edge_enabled=state["ppu.mask.backgroundMask"] == "true",
            width=WIDTH, height=HEIGHT,
        )
        computed = color_codes_to_rgb(color_codes, colors)
        observed = _read_exact(folder / f"{frame}-end-rgb.bin", 256 * 240 * 3)
        visible = observed[:WIDTH * HEIGHT * 3]
        mismatches = [
            offset // 3 for offset in range(0, len(computed), 3)
            if computed[offset:offset + 3] != visible[offset:offset + 3]
        ]
        compared = WIDTH * HEIGHT
        samples += compared
        differences += len(mismatches)
        details.append({
            "frame": frame, "compared_pixels": compared,
            "mismatches": len(mismatches),
            "first_difference": (
                {"x": mismatches[0] % WIDTH, "y": mismatches[0] // WIDTH}
                if mismatches else None
            ),
            "chr_pages_1k": pages,
            "palette_ram_sha256": sha256(palette).hexdigest(),
            "model_rgb_sha256": sha256(computed).hexdigest(),
            "native_gameplay_rgb_sha256": sha256(visible).hexdigest(),
        })
    return {
        "passed": differences == 0 and samples == len(frames) * WIDTH * HEIGHT,
        "scope": "World 1-1 first-entry bonus viewport, 256x192 RGB, no HUD",
        "sampled_frames": len(frames),
        "frame_range": [first, last],
        "compared_pixels": samples, "mismatches": differences,
        "source_rom_sha256": rom.metadata.rom_sha256,
        "rgb_profile": "MesenCE pinned default 2C02, externally supplied GPLv3 source",
        "rgb_profile_source_sha256": sha256(source).hexdigest(),
        "native_ppu_ciram_verified": True,
        "per_dot_fetch_or_mask_timing_verified": False,
        "hud_and_sprite_compositing_verified": False,
        "frames": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("capture", type=Path)
    parser.add_argument("palette_source", type=Path,
                        help="Local MesenCE 2.2.1 Core/NES/NesDefaultVideoFilter.cpp")
    parser.add_argument("--first", type=int, default=FIRST_ACCEPTED)
    parser.add_argument("--last", type=int, default=LAST_ACCEPTED)
    args = parser.parse_args()
    try:
        result = verify(load_rom(args.rom), args.capture, args.palette_source,
                        first=args.first, last=args.last)
    except (ValueError, OSError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Visible background verification failed: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
