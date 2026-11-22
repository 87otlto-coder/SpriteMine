"""Optional private SMB3 A/B/A smoke. Reuses the existing pipe replay as a test driver.

The recorder never loads states or controls gameplay; the independently supplied driver does.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

from flight_recorder import digest, package, snapshots, summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("emulator", "rom", "slot", "input", "driver", "output"):
        parser.add_argument("--" + name, type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--events", action="store_true")
    args = parser.parse_args()
    if any((p / ".git").exists() for p in (args.output, *args.output.parents)):
        raise ValueError("Keep private evidence outside Git")
    sources = {name: getattr(args, name) for name in ("emulator", "rom", "slot", "input", "driver")}
    sources["recorder"] = Path(__file__).with_name("flight_recorder.lua")
    sources["settings"] = args.emulator.with_name("settings.json")
    hashes = {k: digest(v) for k, v in sources.items()}
    assert hashes["rom"] == "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"
    assert hashes["input"] == "f780c7ba7e5002f9a62161486ad29e978106588571f6bf8eb268bd909681d082"
    assert hashes["emulator"] == "8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7"
    folder = args.output / ("aba-" + uuid.uuid4().hex[:10])
    folder.mkdir(parents=True)
    script = args.driver.read_text(encoding="utf-8")
    needle = "restored = assert(emu.loadSavestate(state))"
    assert script.count(needle) == 1, "Expected original pipe_replay.lua driver"
    reference_regions = {"nesInternalRam": 2048, "nesWorkRam": 8192,
                         "nesNametableRam": 2048, "nesPaletteRam": 32,
                         "nesPpuDebug": 12288, "nesSpriteRam": 256}
    reference_code = '\nif s.frameCount == 450836 or s.frameCount == 450866 then\n'
    for name, size in reference_regions.items():
        reference_code += f'save(s.frameCount .. "-reference-{name}.bin", read_region(0, {size}, emu.memType.{name}))\n'
    reference_code += 'end\n'
    script = script.replace('if kind == "end" then', 'if kind == "end" then' + reference_code)
    signatures, times = [], []
    for leg in ("A", "B", "A2"):
        dest = folder / leg
        dest.mkdir()
        code = script
        if leg == "B":
            code = code.replace(needle, needle + '\n        dofile(assert(os.getenv("SMFR_SCRIPT")))')
        driver = dest / "driver.lua"
        driver.write_text(code, encoding="utf-8")
        env = dict(os.environ, SPRITEMINE_PIPE_OUTPUT=str(dest), SPRITEMINE_PIPE_INPUT=str(args.input),
                   SPRITEMINE_PIPE_SLOT=str(args.slot), SPRITEMINE_PIPE_FIRST="450778",
                   SPRITEMINE_PIPE_LAST="450881", SPRITEMINE_PIPE_DETAIL="0",
                   SMFR_OUTPUT=str(dest), SMFR_SCRIPT=str(sources["recorder"]),
                   SMFR_INTERVAL=str(args.interval), SMFR_CHECKPOINT="300", SMFR_FRAMES="2589",
                   SMFR_MAX_BYTES="67108864", SMFR_EVENT_CAP="32", SMFR_STOP="0",
                   SMFR_EVENTS=str(int(args.events)))
        start = time.perf_counter()
        with (dest / "emulator.log").open("wb") as log:
            subprocess.run([str(args.emulator), "--testRunner", "--timeout=90", "--doNotSaveSettings",
                            "--nes.disableSprites=false", "--nes.removeSpriteLimit=false", str(driver), str(args.rom)],
                           cwd=args.emulator.parent, env=env, stdout=log, stderr=subprocess.STDOUT,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=105, check=True)
        times.append(time.perf_counter() - start)
        signature = {p.name: digest(p) for p in dest.iterdir()
                     if p.name in ("trace.tsv", "controller.tsv") or p.name.endswith(("-rgb.bin", "-tiles.bin"))
                     or "-reference-" in p.name}
        assert len(signature) == 326, (leg, len(signature))
        assert len((dest / "trace.tsv").read_text().splitlines()) == 2590
        signatures.append(signature)
    assert signatures[0] == signatures[1] == signatures[2], "Recorder altered replay signatures"
    assert all(digest(v) == hashes[k] for k, v in sources.items()), "Source modified"
    raw_bytes = (folder / "B" / "capture.jsonl").stat().st_size
    packed = package(folder / "B")
    samples = list(snapshots(packed))
    # Independent known route labels define the test interval, not recorder addresses.
    around = [(r, m) for r, m in samples if 450820 <= r["time"]["frame"] <= 450881]
    assert len(around) >= 2
    before, after = around[0], around[-1]
    diffs = {name: sum(a != b for a, b in zip(before[1][name], after[1][name])) for name in before[1]}
    assert diffs["nesNametableRam"] > 0 and diffs["nesPaletteRam"] > 0 and diffs["nesPpuDebug"] > 0
    reference_matches = 0
    for record, memory in (before, after):
        frame = record["time"]["frame"]
        for name in reference_regions:
            assert memory[name] == (folder / "A" / f"{frame}-reference-{name}.bin").read_bytes()
            reference_matches += 1
    rgb_before = (folder / "A" / "450836-end-rgb.bin").read_bytes()
    rgb_after = (folder / "A" / "450866-end-rgb.bin").read_bytes()
    rgb_changed = sum(rgb_before[i:i+3] != rgb_after[i:i+3] for i in range(0, len(rgb_before), 3))
    assert rgb_changed > 0
    summary = summarize(packed)
    assert summary["footer"] and summary["footer"]["reason"] == "frame_limit"
    report = {"neutral": True, "matched_files_per_leg": len(signatures[0]), "polls": 2590,
              "wall_seconds_A_B_A2": times, "source_sha256": hashes,
              "source_paths": {k: str(v) for k, v in sources.items()},
              "interval": args.interval, "events": args.events,
              "raw_bytes": raw_bytes, "compressed_bytes": packed.stat().st_size,
              "capture_sha256": digest(packed), "summary": summary,
              "independent_memory_matches": reference_matches, "changed_rgb_pixels": rgb_changed,
              "area_comparison": {"before_frame": before[0]["time"]["frame"],
                                  "after_frame": after[0]["time"]["frame"], "changed_bytes": diffs},
              "reference_sha256": signatures[0]}
    (folder / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(folder)


if __name__ == "__main__":
    main()
