"""Verify unambiguous pipe-mask pixels against paired native RGB captures."""

import argparse
from collections import Counter
import json
from pathlib import Path

from spritemine.rom import load_rom
from spritemine.sprite import compose_scanline, sprite_pixels

RGB = {0x0F: bytes(3), 0x16: bytes.fromhex("b53120"),
       0x36: bytes.fromhex("feccc5"), 0x3C: bytes.fromhex("b5ebf2")}


def match_pages(chr_rom, ppu):
    pages = []
    for offset in range(0, 8192, 1024):
        page = ppu[offset:offset + 1024]
        matches = [bank for bank in range(128) if chr_rom[bank * 1024:(bank + 1) * 1024] == page]
        if not matches or (offset == 0x1400 and len(matches) != 1):
            raise ValueError("Unresolved CHR content in PPU snapshot")
        pages.append(matches[0])
    return tuple(pages)


def stable_chr(events, scanline_limit):
    """Reject CHR writes or inversion changes between start and mask fetches."""
    selector = None
    after_start = False
    for kind, _, _, scanline, _, address, value in events:
        if kind == "start":
            after_start = True
        if kind != "mapper-write":
            continue
        if address & 0xE001 == 0x8000:
            if after_start and scanline < scanline_limit and (selector is None or (selector ^ value) & 128):
                return False
            selector = value
        elif address & 0xE001 == 0x8001 and after_start and scanline < scanline_limit:
            if selector is None or selector & 7 < 6:
                return False
    return after_start


def verify(rom, capture):
    detail = capture / "B"
    events = {}
    for line in (detail / "events.tsv").read_text(encoding="ascii").splitlines():
        kind, *fields = line.split("\t")
        row = (kind, *map(int, fields))
        events.setdefault(row[1], []).append(row)
    counts, pages_seen = Counter(checked=0, mismatch=0), Counter()
    for path in sorted(detail.glob("*-start-oam.bin")):
        frame = int(path.name.split("-")[0])
        oam = path.read_bytes()
        masks = [slot for slot in range(4) if oam[slot * 4 + 1:slot * 4 + 3] == b"\x77\x20"
                 and oam[slot * 4] < 224]
        if not masks:
            continue
        last = max(oam[slot * 4] + 16 for slot in masks)
        if not stable_chr(events[frame], last + 1):
            counts["unstable_chr_frames"] += 1
            continue
        pages = match_pages(rom.chr, (detail / f"{frame}-start-ppu.bin").read_bytes())
        opacity = sum(bool(p) for p in sprite_pixels(rom, 0x77, pages))
        pages_seen[f"{pages[5]:02x}:{opacity}"] += 1
        palette = (detail / f"{frame}-start-palette.bin").read_bytes()
        if palette[0] not in RGB:
            raise ValueError("Unsupported universal background color")
        backdrop = RGB[palette[0]]
        native = (detail / f"{frame}-end-rgb.bin").read_bytes()
        background = (capture / "background" / f"{frame}-end-rgb.bin").read_bytes()
        if len(native) != 256 * 240 * 3 or len(background) != len(native):
            raise ValueError("Expected native 256x240 RGB buffers")
        removed = bytearray(oam)
        for slot in masks:
            removed[slot * 4] = 248
        for y in range(min(oam[slot * 4] + 1 for slot in masks), last + 1):
            origin = y * 256 * 3
            colors = [background[i:i + 3] for i in range(origin, origin + 768, 3)]
            # Backdrop RGB may also be used by nonzero background values.
            # Compare only positions whose RGB rules out the universal color.
            bg = bytes(color != backdrop for color in colors)
            modeled = compose_scanline(rom, oam, pages, y, bg)
            without = compose_scanline(rom, removed, pages, y, bg)
            for x, winner in enumerate(modeled.winning_oam_slots):
                if winner not in masks or without.winning_oam_slots[x] not in range(10, 16):
                    continue
                if not bg[x]:
                    counts["backdrop_color_skipped"] += 1
                    continue
                unmasked = RGB.get(palette[16 + without.sprite_palette_offsets[x]])
                if not modeled.background_wins[x] or unmasked is None or unmasked == colors[x]:
                    counts["indistinguishable_skipped"] += 1
                    continue
                i = origin + x * 3
                counts["checked"] += 1
                if native[i:i + 3] != colors[x]:
                    counts["mismatch"] += 1
    return {"pixel_counts": dict(counts), "mask_page_and_opaque_count": dict(pages_seen)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    result = verify(load_rom(args.rom), args.capture)
    print(json.dumps(result, indent=2))
    counts = result["pixel_counts"]
    return int(not counts.get("checked") or bool(counts.get("mismatch")))


if __name__ == "__main__":
    raise SystemExit(main())
