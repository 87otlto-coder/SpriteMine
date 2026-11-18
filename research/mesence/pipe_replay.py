"""Run bounded MesenCE A/B/A captures from recorded controller poll masks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from spritemine.player import ROM_SHA256

MESEN_SHA256 = "8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def common_signature(folder):
    return {path.name: digest(path) for path in folder.iterdir()
            if path.name in ("trace.tsv", "controller.tsv")
            or path.name.endswith(("-rgb.bin", "-tiles.bin"))}


def run(args):
    parent = (args.root / "FIXTURE" / "SMB3" / "RuntimeInvestigation").resolve(strict=True)
    if any((p / ".git").exists() for p in (parent, *parent.parents)):
        raise ValueError("Captures must remain outside Git checkouts")
    script = Path(__file__).with_suffix(".lua")
    sources = {"rom": args.rom, "emulator": args.emulator, "slot": args.slot,
               "input": args.input, "settings": args.emulator.with_name("settings.json"),
               "script": script}
    hashes = {key: digest(path) for key, path in sources.items()}
    if hashes["rom"] != ROM_SHA256 or hashes["emulator"] != MESEN_SHA256:
        raise ValueError("Expected verified SMB3 USA PRG1 and MesenCE 2.2.1")
    if not 0 <= args.first <= args.last <= 0xffffffff or args.last - args.first > 120:
        raise ValueError("Expected a capture window of at most 121 frames")
    count = args.input.stat().st_size
    if not 0 < count <= 4096:
        raise ValueError("Expected 1–4096 controller poll bytes")
    output = Path(tempfile.mkdtemp(prefix="pipe-replay-", dir=parent))
    switches = ["--testRunner", "--timeout=30", "--doNotSaveSettings",
                "--nes.disableSprites=false", "--nes.removeSpriteLimit=false"]
    signatures = []
    for leg in ("A", "B", "A2"):
        folder = output / leg
        folder.mkdir()
        env = dict(os.environ, SPRITEMINE_PIPE_OUTPUT=str(folder),
                   SPRITEMINE_PIPE_INPUT=str(args.input), SPRITEMINE_PIPE_SLOT=str(args.slot),
                   SPRITEMINE_PIPE_FIRST=str(args.first), SPRITEMINE_PIPE_LAST=str(args.last),
                   SPRITEMINE_PIPE_DETAIL=str(int(leg == "B")))
        with (folder / "emulator.log").open("wb") as log:
            subprocess.run([args.emulator, *switches, script, args.rom],
                           cwd=args.emulator.parent, env=env, stdout=log, stderr=subprocess.STDOUT,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=45, check=True)
        signature = common_signature(folder)
        trace = (folder / "trace.tsv").read_text(encoding="ascii").splitlines()
        if len(trace) != count:
            raise ValueError(f"{leg} did not consume the complete input: {folder}")
        for frame in range(args.first, args.last + 1):
            for suffix in ("start-tiles", "end-tiles", "end-rgb"):
                if f"{frame}-{suffix}.bin" not in signature:
                    raise ValueError(f"{leg} missed frame {frame} {suffix}: {folder}")
        signatures.append(signature)
    if any(digest(path) != hashes[key] for key, path in sources.items()):
        raise ValueError("A replay source changed during capture")
    if not signatures[0] == signatures[1] == signatures[2]:
        raise ValueError(f"Instrumentation altered sampled behavior: {output}")
    report = {"capture_dir": str(output), "input_polls": count, "neutral": True,
              "frame_range": [args.first, args.last], "source_sha256": hashes,
              "switches": switches, "reference_sha256": signatures[0]}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "rom", "emulator", "slot", "input"):
        parser.add_argument(f"--{name}", type=lambda value: Path(value).resolve(), required=True)
    for name in ("first", "last"):
        parser.add_argument(f"--{name}", type=int, required=True)
    try:
        print(json.dumps(run(parser.parse_args()), indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"Pipe replay failed: {exc}\n")


if __name__ == "__main__":
    main()
