"""Launch three independent, read-only slot replays under a private fixture directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from .decode_mmc3_trace import EXPECTED_SMB3_SHA256, load_chr

HERE = Path(__file__).resolve().parent
ROOT = Path("F:/Dev/ROMMAGE")
LEGS = (("A", False), ("B", True), ("A2", False))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_folder(path):
    path = path.resolve()
    if not any(p.name.upper() == "FIXTURE" for p in (path, *path.parents)):
        raise ValueError("Game output must be under FIXTURE")
    if any((p / ".git").exists() for p in (path, *path.parents)):
        raise ValueError("Game output must be outside Git checkouts")
    return path



def prepare_portable_mesen(source_exe, settings_file, run):
    """Stage an identical MesenCE build with a private settings.json.

    MesenCE 2.2.1 uses the executable folder as HomeFolder when settings.json
    exists next to the executable. This avoids an inaccessible Documents path
    without mutating the installed emulator or the user's existing settings.
    """
    source_exe = Path(source_exe).resolve(strict=True)
    settings_file = Path(settings_file).resolve(strict=True)
    if settings_file.name.lower() != "settings.json" or not settings_file.is_file():
        raise ValueError("Portable emulator settings must be a readable settings.json")
    settings_bytes = settings_file.read_bytes()
    try:
        value = json.loads(settings_bytes.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Portable MesenCE settings.json is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("Portable MesenCE settings.json must contain a JSON object")
    runtime = private_folder(Path(run) / "mesen-portable")
    runtime.mkdir()  # refuse to reuse a pre-existing runtime
    exe_copy = runtime / "Mesen.exe"
    settings_copy = runtime / "settings.json"
    shutil.copyfile(source_exe, exe_copy)
    settings_copy.write_bytes(settings_bytes)
    exe_sha, settings_sha = digest(source_exe), hashlib.sha256(settings_bytes).hexdigest()
    if digest(exe_copy) != exe_sha or digest(settings_copy) != settings_sha:
        raise ValueError("Portable MesenCE staging changed executable or settings bytes")
    return exe_copy, exe_sha, settings_sha


def capture(args, run):
    fixture = (args.root / "FIXTURE").resolve(strict=True)
    rom = args.rom or fixture / "Super Mario Bros. 3.zip"
    exe = (args.root / "TOOLS/Mesence/Mesen.exe").resolve(strict=True)
    state = args.slot.resolve(strict=True)
    load_chr(rom)
    copy = run / "slot-copy.mss"
    shutil.copyfile(state, copy)
    initial = digest(copy)
    game = run / "replay.nes"
    if rom.suffix.lower() == ".zip":
        with zipfile.ZipFile(rom) as archive:
            entry, = [e for e in archive.infolist() if e.filename.lower().endswith(".nes")]
            game.write_bytes(archive.read(entry))
    else:
        shutil.copyfile(rom, game)
    if digest(game) != EXPECTED_SMB3_SHA256:
        raise ValueError("Private ROM copy changed")
    script = run / "capture.lua"
    script.write_bytes(b"\n".join((HERE / name).read_bytes() for name in
                                  ("graphics_replay.lua", "spritemine_render_probe.lua")))
    source_exe_sha = digest(exe)
    portable_settings = getattr(args, "emulator_settings", None)
    portable_settings_path = (Path(portable_settings).resolve(strict=True)
                              if portable_settings is not None else None)
    if portable_settings_path is not None:
        launch_exe, portable_exe_sha, portable_settings_sha = prepare_portable_mesen(
            exe, portable_settings_path, run
        )
        if portable_exe_sha != source_exe_sha:
            raise ValueError("Portable MesenCE executable differs from original")
    else:
        launch_exe = exe
        portable_settings_sha = None

    version = subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-Command",
         "(Get-Item -LiteralPath $env:SPRITEMINE_EXE).VersionInfo.ProductVersion"],
        env=dict(os.environ, SPRITEMINE_EXE=str(exe)), text=True).strip()
    for leg, hidden in LEGS:
        folder = run / leg
        folder.mkdir()
        if digest(copy) != initial or digest(state) != initial:
            raise ValueError("Slot identity changed")
        env = dict(os.environ, SPRITEMINE_CAPTURE_DIR=str(folder), SPRITEMINE_STATE=str(copy),
                   SPRITEMINE_START_PULSE=str(int(args.start_pulse)), SPRITEMINE_INPUT_PLAN=args.plan, SPRITEMINE_WARMUP=str(args.warmup))
        switches = ["--testRunner", "--timeout=30", "--doNotSaveSettings",
                    "--nes.disableSprites=" + str(hidden).lower()]
        if portable_settings_path is not None:
            if (digest(portable_settings_path) != portable_settings_sha
                    or digest(launch_exe.parent / "settings.json") != portable_settings_sha
                    or digest(launch_exe) != source_exe_sha):
                raise ValueError("Portable MesenCE settings or executable changed")
        with (folder / "emulator.log").open("wb") as log:
            result = subprocess.run([str(launch_exe), *switches, str(script), str(game)],
                                    env=env, cwd=str(launch_exe.parent),
                                    stdout=log, stderr=subprocess.STDOUT, timeout=55,
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if portable_settings_path is not None:
            if (digest(portable_settings_path) != portable_settings_sha
                    or digest(launch_exe.parent / "settings.json") != portable_settings_sha
                    or digest(launch_exe) != source_exe_sha):
                raise ValueError("Portable MesenCE profile changed during replay")
        evidence = dict(leg=leg, disable_sprites=hidden, switches=switches, plan=args.plan,
                        emulator_version=version, warmup=args.warmup, start_pulse=args.start_pulse, slot_sha256=initial, emulator_sha256=digest(exe),
                        probe_sha256=digest(script), rom_sha256=digest(game), exit_code=result.returncode,
                        portable_mode=portable_settings_path is not None,
                        portable_settings_sha256=portable_settings_sha)
        (folder / "launch.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        if result.returncode:
            raise ValueError(f"{leg} emulator exit {result.returncode}. Inspect {folder}")
    if digest(state) != initial or digest(copy) != initial or digest(exe) != source_exe_sha:
        raise ValueError("Slot bytes changed during experiment")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--slot", type=Path, required=True)
    parser.add_argument("--emulator-settings", type=Path,
                        help="Private readable settings.json; stage identical Mesen.exe "
                             "in the run's FIXTURE/mesen-portable to avoid Documents access")
    parser.add_argument("--plan", choices=("neutral", "right", "jump"), default="neutral")
    parser.add_argument("--warmup", type=int, default=8, choices=range(2, 121), metavar="2..120")
    parser.add_argument("--start-pulse", action="store_true", help="Press Start on poll 4 for a paused game")
    args = parser.parse_args()
    parent = private_folder(args.root / "FIXTURE" / "SMB3/GraphicsValidation")
    parent.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=args.plan + "-", dir=parent))
    print(run, flush=True)
    from .graphics_report import publish
    try:
        capture(args, run)
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        return publish(run, str(exc))
    return publish(run)


if __name__ == "__main__":
    raise SystemExit(main())
