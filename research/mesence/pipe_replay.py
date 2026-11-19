"""Run bounded MesenCE A/B/A captures from recorded controller poll masks."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile

from spritemine.player import ROM_SHA256

MESEN_SHA256 = "8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# This whitelist describes only evidence collected on *every* A/B/A leg.
# The detailed B observer additionally emits bg-NNNN-tiles.bin snapshots;
# including those B-only files would create a false neutrality failure.
FRAME_EVIDENCE = re.compile(r"^\d+-(?:start-tiles|end-tiles|end-rgb)\.bin$")


def common_signature(folder):
    """Hash exactly the mutually comparable replay evidence, not B-only probes."""
    return {path.name: digest(path) for path in folder.iterdir()
            if path.name in ("trace.tsv", "controller.tsv")
            or FRAME_EVIDENCE.fullmatch(path.name)}


def signature_differences(reference, candidate):
    """Report real missing/extra/changed *common* evidence without masking it."""
    return {name: {
        "reference": reference.get(name), "observed": candidate.get(name)}
        for name in sorted(reference.keys() | candidate.keys())
        if reference.get(name) != candidate.get(name)}


def event_window(trace):
    """Bound the first pipe and following junction observed at input polls."""
    rows = [tuple(map(int, line.split("\t"))) for line in trace]
    entry = next((row for row in rows if row[6]), None)
    if entry is None:
        raise ValueError("Discovery replay observed no pipe movement")
    junction = next((row for row in rows if row[0] >= entry[0] and row[7]), None)
    if junction is None:
        raise ValueError("Discovery replay observed no junction request")
    return max(rows[0][1] + 1, entry[1] - 3), min(rows[-1][1] - 1, junction[1] + 40)


def run(args):
    parent = (args.root / "FIXTURE" / "SMB3" / "RuntimeInvestigation").resolve(strict=True)
    if any((p / ".git").exists() for p in (parent, *parent.parents)):
        raise ValueError("Captures must remain outside Git checkouts")
    if args.ppu_commits and not args.background_staging:
        raise ValueError("--ppu-commits requires --background-staging for source event linkage")
    script = Path(__file__).with_suffix(".lua")
    sources = {"rom": args.rom, "emulator": args.emulator, "slot": args.slot,
               "input": args.input, "settings": args.emulator.with_name("settings.json"),
               "script": script}
    if args.background_staging:
        sources["background_probe"] = Path(__file__).with_name("background_staging_probe.lua")
    if args.ppu_commits:
        sources["ppu_register_probe"] = Path(__file__).with_name("ppu_register_probe.lua")
    hashes = {key: digest(path) for key, path in sources.items()}
    if hashes["rom"] != ROM_SHA256 or hashes["emulator"] != MESEN_SHA256:
        raise ValueError("Expected verified SMB3 USA PRG1 and MesenCE 2.2.1")
    if not args.events and not (
        args.first is not None and args.last is not None
        and 0 <= args.first <= args.last <= 0xffffffff and args.last - args.first <= 120
    ):
        raise ValueError("Expected a capture window of at most 121 frames")
    count = args.input.stat().st_size
    if not 0 < count <= 4096:
        raise ValueError("Expected 1–4096 controller poll bytes")
    output = Path(tempfile.mkdtemp(prefix="pipe-replay-", dir=parent))
    if args.background_staging:
        # One Lua chunk: the optional observer shares only the base replay's
        # private read helpers and state, never gameplay mutation callbacks.
        combined = output / "capture-staging.lua"
        content = script.read_bytes() + b"\n" + sources["background_probe"].read_bytes()
        if args.ppu_commits:
            content += b"\n" + sources["ppu_register_probe"].read_bytes()
        combined.write_bytes(content)
        script = combined
    switches = ["--testRunner", "--timeout=30", "--doNotSaveSettings",
                "--nes.disableSprites=false", "--nes.removeSpriteLimit=false"]
    def capture(leg, first, last, capture_switches=switches):
        folder = output / leg
        folder.mkdir()
        env = dict(os.environ, SPRITEMINE_PIPE_OUTPUT=str(folder),
                   SPRITEMINE_PIPE_INPUT=str(args.input), SPRITEMINE_PIPE_SLOT=str(args.slot),
                   SPRITEMINE_PIPE_FIRST=str(first), SPRITEMINE_PIPE_LAST=str(last),
                   SPRITEMINE_PIPE_DETAIL=str(int(leg == "B")),
                   SPRITEMINE_BG_STAGING=str(int(args.background_staging and leg == "B")),
                   SPRITEMINE_PPU_COMMITS=str(int(args.ppu_commits and leg == "B")))
        with (folder / "emulator.log").open("wb") as log:
            subprocess.run([args.emulator, *capture_switches, script, args.rom],
                           cwd=args.emulator.parent, env=env, stdout=log, stderr=subprocess.STDOUT,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=45, check=True)
        signature = common_signature(folder)
        trace = (folder / "trace.tsv").read_text(encoding="ascii").splitlines()
        if len(trace) != count:
            raise ValueError(f"{leg} did not consume the complete input: {folder}")
        return trace, signature

    first, last = args.first, args.last
    discovery = None
    if args.events:
        trace, discovery = capture("discovery", 0, 0)
        first, last = event_window(trace)
        if not first <= last or last - first > 120:
            raise ValueError("Discovered event window exceeds capture bounds")
    signatures = []
    for leg in ("A", "B", "A2"):
        _, signature = capture(leg, first, last)
        if discovery and any(signature[name] != discovery[name] for name in ("trace.tsv", "controller.tsv")):
            raise ValueError(f"{leg} diverged from event discovery")
        for frame in range(first, last + 1):
            for suffix in ("start-tiles", "end-tiles", "end-rgb"):
                if f"{frame}-{suffix}.bin" not in signature:
                    raise ValueError(f"{leg} missed frame {frame} {suffix}: {output / leg}")
        signatures.append(signature)
    if any(digest(path) != hashes[key] for key, path in sources.items()):
        raise ValueError("A replay source changed during capture")
    if not signatures[0] == signatures[1] == signatures[2]:
        differences = {
            leg: signature_differences(signatures[0], sig)
            for leg, sig in zip(("B", "A2"), signatures[1:])
        }
        changed = {leg: changes for leg, changes in differences.items() if changes}
        raise ValueError(
            f"Instrumentation altered comparable replay evidence: {output}; "
            f"first differences {str({leg: list(items.items())[:8] for leg, items in changed.items()})[:1400]}"
        )
    background = None
    if args.background_reference:
        bg_switches = [s.replace("disableSprites=false", "disableSprites=true") for s in switches]
        _, background = capture("background", first, last, bg_switches)
        shared = {key for key in signatures[0] if not key.endswith("-rgb.bin")}
        if any(background.get(key) != signatures[0][key] for key in shared):
            raise ValueError(f"Background-only replay altered sampled game state: {output}")
    report = {"capture_dir": str(output), "input_polls": count, "neutral": True,
              "frame_range": [first, last], "source_sha256": hashes,
              "switches": switches, "reference_sha256": signatures[0]}
    if args.background_staging:
        staging = output / "B" / "background-staging.tsv"
        rows = staging.read_text(encoding="ascii").splitlines()
        report["background_staging"] = {
            "observer": "read-only, detailed B leg only",
            "event_count": len(rows) - 1,
            "log_sha256": digest(staging),
            "verified_against_rom_model": False,
        }
    if args.ppu_commits:
        registers = output / "B" / "ppu-registers.tsv"
        with registers.open("rb") as stream:
            record_count = sum(1 for _ in stream) - 1
        report["ppu_register_trace"] = {
            "observer": "CPU PPU register writes; not hardware-completed VRAM notifications",
            "event_count": record_count,
            "log_sha256": digest(registers),
            "ppu_commit_verified": False,
        }
    if background is not None:
        report["background_rgb_sha256"] = {
            key: value for key, value in background.items() if key.endswith("-rgb.bin")
        }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "rom", "emulator", "slot", "input"):
        parser.add_argument(f"--{name}", type=lambda value: Path(value).resolve(), required=True)
    for name in ("first", "last"):
        parser.add_argument(f"--{name}", type=int)
    parser.add_argument("--events", action="store_true", help="Discover first pipe and junction before capture")
    parser.add_argument("--background-reference", action="store_true", help="Capture and verify a sprites-hidden RGB reference")
    parser.add_argument("--background-staging", action="store_true",
                        help="Passively snapshot completed Plains pattern/attribute producers in B leg")
    parser.add_argument("--ppu-commits", action="store_true",
                        help="Record read-only CPU PPU register write intent and prewrite PPU state in B leg")
    try:
        print(json.dumps(run(parser.parse_args()), indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"Pipe replay failed: {exc}\n")


if __name__ == "__main__":
    main()
