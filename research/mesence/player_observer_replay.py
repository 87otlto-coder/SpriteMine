"""Reproduce the 24-frame SMB3 player observer A/B/A check on Windows."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from time import perf_counter

from spritemine.player import ROM_SHA256, inspect_recipes
from spritemine.rom import load_rom
from spritemine.sprite import sprite_pixels, sprite_tiles

FIRST, LAST = 448385, 448408
EXPECTED = [0x3E] * 5 + [0x3F] * 6 + [0x3E] * 4 + [0x40] * 9
SWITCHES = ["--testRunner", "--timeout=30", "--doNotSaveSettings", "--nes.disableSprites=false"]
# Scope is the three NES palette codes verified by the existing graphics harness.
RGB = {0x16: bytes.fromhex("b53120"), 0x36: bytes.fromhex("feccc5"), 0x0F: bytes(3)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phase_signatures(folder):
    manifest_path, = folder.glob("render_*.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    phases = manifest["phase_captures"]
    if manifest["completed_frame_pairs"] != 25 or len(phases) != 50 or manifest["dropped_writes"]:
        raise ValueError("Expected 25 complete capture pairs with no dropped MMC3 writes")
    signatures = []
    for phase in phases:
        files = phase.pop("files")
        signatures.append((phase, {name: digest(folder / value) for name, value in files.items() if value}))
    frames = [phase["frame_count"] for phase, _ in signatures if phase["event"] == "startFrame"]
    if frames != list(range(FIRST - 1, LAST + 1)):
        raise ValueError("Replay frame IDs differ from the expected slot-1 sequence")
    return {"phases": signatures, "controller": digest(folder / "controller-bus.log"),
            "replay": digest(folder / "replay.log")}


def observations(path):
    events = {"start": [], "end": [], "irq": [], "nmi": []}
    for line in path.read_text(encoding="ascii").splitlines():
        event, frame, clock, cycle, recipe = line.split()
        events[event].append(tuple(map(int, (frame, clock, cycle, recipe))))
    for phase in ("start", "end"):
        if [row[0] for row in events[phase]] != list(range(FIRST, LAST + 1)):
            raise ValueError(f"Incomplete {phase} frame observations")
    if [row[3] for row in events["start"]] != EXPECTED:
        raise ValueError("Start-of-frame Player_Frame values differ from the expected sequence")
    return events


def compare_player(folder, timeline, rom, observed_ids):
    manifest = json.loads(next(folder.glob("render_*.json")).read_text(encoding="utf-8"))
    phases = {(item["frame_count"], item["event"]): item["files"]
              for item in manifest["phase_captures"]}
    archived = json.loads(timeline.read_text(encoding="utf-8"))["frames"]
    if [item["frame_count"] for item in archived] != list(range(FIRST, LAST + 1)):
        raise ValueError("Expected the verified 24-frame timeline")
    recipes = inspect_recipes(rom)["recipes"]
    opaque_count = 0
    for prior, frame_id in zip(archived, observed_ids):
        frame = prior["frame_count"]
        start = phases[frame, "startFrame"]
        end = phases[frame, "endFrame"]
        oam, palette, chr_view, rgb = [
            (folder / path).read_bytes()
            for path in (start["oam"], start["palette"], start["ppu_pattern"], end["screen_rgb"])
        ]
        for key, data in (("oam_start", oam), ("palette_start", palette),
                          ("ppu_start", chr_view), ("rendered_rgb", rgb)):
            if hashlib.sha256(data).hexdigest() != prior[key + "_sha256"]:
                raise ValueError(f"Fresh frame {frame} differs from archived {key} evidence")
        page = 0x50 + recipes[frame_id]["chr_page_offset"]
        pages = (0, 0, 0, 0, page, 0, 0, 0)
        rgba = bytearray(16 * 16 * 4)
        for slot in (10, 11):
            stored_y, pattern, attributes, x = oam[slot * 4:slot * 4 + 4]
            y = stored_y + 1
            if ((x - prior["position_x"]) not in (0, 8) or y != prior["position_y"]
                    or pattern & 0xC1 != 1 or attributes & 32):
                raise ValueError(f"Unsupported component placement or priority in frame {frame}")
            address = 0x1000 + (pattern & 0xFE) * 16
            top, _ = sprite_tiles(pattern, pages)
            if chr_view[address:address + 32] != rom.chr[top * 16:top * 16 + 32]:
                raise ValueError(f"Frame {frame} captured CHR differs from the ROM-derived bank")
            for index, value in enumerate(sprite_pixels(rom, pattern, pages, attributes)):
                if not value:
                    continue
                dy, dx = divmod(index, 8)
                color = RGB[palette[16 + (attributes & 3) * 4 + value]]
                screen_pos = ((y + dy) * 256 + x + dx) * 3
                if color != rgb[screen_pos:screen_pos + 3]:
                    raise ValueError(f"Native opaque RGB mismatch in frame {frame}")
                position = (dy * 16 + x - prior["position_x"] + dx) * 4
                rgba[position:position + 4] = color + b"\xff"
                opaque_count += 1
        if hashlib.sha256(rgba).hexdigest() != prior["rgba_sha256"]:
            raise ValueError(f"Reconstructed RGBA differs from archived frame {frame}")
    return {"frame_count": len(archived), "opaque_rgb_matches": opaque_count,
            "rgba_hashes_matched": len(archived)}


def capture(args):
    fixture = (args.root / "FIXTURE" / "SMB3").resolve(strict=True)
    parent = (fixture / "RuntimeInvestigation").resolve(strict=True)
    if parent.parent != fixture or any((part / ".git").exists() for part in (parent, *parent.parents)):
        raise ValueError("Capture output must remain in the private fixture directory")
    emulator = args.emulator.resolve(strict=True)
    slot = args.slot.resolve(strict=True)
    rom = args.rom.resolve(strict=True)
    settings = emulator.with_name("settings.json")
    sources = {name: digest(path) for name, path in
               (("emulator", emulator), ("slot", slot), ("rom", rom), ("settings", settings))}
    if sources["rom"] != ROM_SHA256:
        raise ValueError("Expected exact SMB3 PRG1 .nes input")
    if sources["emulator"] != "8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7":
        raise ValueError("Expected the verified MesenCE 2.2.1 Windows build")
    replay = (args.harness / "graphics_replay.lua").read_bytes()
    probe = (args.harness / "spritemine_render_probe.lua").read_bytes()
    if probe.count(b"CAPTURE_PAIRS = 2") != 1 or probe.count(b"MAX_WRITES = 256") != 1:
        raise ValueError("Unsupported render probe source")
    probe = probe.replace(b"CAPTURE_PAIRS = 2", b"CAPTURE_PAIRS = 25")
    probe = probe.replace(b"MAX_WRITES = 256", b"MAX_WRITES = 4096")
    observer = Path(__file__).with_name("player_observer.lua").read_bytes()
    run = Path(tempfile.mkdtemp(prefix="observer-", dir=parent))
    signatures, legs = [], []
    for leg, adjunct in (("A", b""), ("B", observer), ("A2", b"")):
        folder = run / leg
        folder.mkdir()
        script = folder / "capture.lua"
        script.write_bytes(b"\n".join((replay, adjunct, probe)))
        env = dict(os.environ, SPRITEMINE_CAPTURE_DIR=str(folder), SPRITEMINE_STATE=str(slot),
                   SPRITEMINE_START_PULSE="0", SPRITEMINE_INPUT_PLAN="right", SPRITEMINE_WARMUP="8")
        start = perf_counter()
        with (folder / "emulator.log").open("wb") as log:
            subprocess.run([str(emulator), *SWITCHES, str(script), str(rom)],
                           cwd=emulator.parent, env=env, stdout=log, stderr=subprocess.STDOUT,
                           timeout=55, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        legs.append({"leg": leg, "elapsed_seconds": round(perf_counter() - start, 3),
                     "script_sha256": digest(script)})
        signatures.append(phase_signatures(folder))
        for name, path in (("emulator", emulator), ("slot", slot), ("rom", rom), ("settings", settings)):
            if digest(path) != sources[name]:
                raise ValueError(f"Capture input changed during replay: {name}")
    if not signatures[0] == signatures[1] == signatures[2]:
        raise ValueError(f"Observer changed replay evidence in {run}")
    events = observations(run / "B" / "player.tsv")
    report = {"run": str(run), "sources_sha256": sources, "legs": legs, "neutral": True,
              "frame_range": [FIRST, LAST], "event_counts": {k: len(v) for k, v in events.items()},
              "start_recipe_ids": [row[3] for row in events["start"]]}
    if args.timeline:
        report["reconstruction"] = compare_player(
            run / "B", args.timeline, load_rom(rom), report["start_recipe_ids"])
    (run / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "harness", "emulator", "slot", "rom"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--timeline", type=Path, help="Previously verified private 24-frame timeline")
    try:
        print(json.dumps(capture(parser.parse_args()), indent=2))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"SpriteMine observer capture failed: {exc}\n")


if __name__ == "__main__":
    main()
