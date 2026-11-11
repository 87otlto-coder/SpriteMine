"""Synthetic-only MesenCE Lua 5.4 CI checks, portable across Windows/Python.

Preserves the historical phase, MMC3, RGB and Lua mock assertions without
POSIX heredocs, apt, /tmp paths, or shell-specific wildcards. No game ROMs.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

try:
    from .verify_phase_capture import verify_phase_session
    from .analyze_render_capture import analyze_render_capture
except ImportError:
    from verify_phase_capture import verify_phase_session
    from analyze_render_capture import analyze_render_capture

ROOT = Path(__file__).resolve().parents[2]
MESENCE = ROOT / "research" / "mesence"
SCRIPTS = (
    "spritemine_frame_probe.lua", "spritemine_mapping_probe.lua",
    "spritemine_mmc3_trace.lua", "spritemine_phase_capture.lua",
    "spritemine_render_probe.lua", "mock_mesence.lua",
    "mock_mesence_mapping.lua", "mock_mmc3_trace.lua",
    "mock_mesence_phase.lua", "mock_mesence_render.lua",
)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise AssertionError(reason)


def execute(env: dict[str, str], *args: str) -> None:
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def one(folder: Path, pattern: str) -> Path:
    hits = sorted(folder.glob(pattern))
    require(len(hits) == 1, f"Expected exactly one {pattern}; found {len(hits)}")
    return hits[0]


def create_fixture(folder: Path) -> str:
    chr_rom = bytes((bank * 3 + i) % 256 for bank in range(128)
                    for i in range(1024))
    image = b"NES\x1a" + bytes((1, 16, 0x40, 0)) + bytes(8) + bytes(16384) + chr_rom
    (folder / "synthetic.nes").write_bytes(image)
    return hashlib.sha1(image).hexdigest().upper()


def inspect_mmc3(folder: Path) -> None:
    source = json.loads(one(folder, "mmc3_trace_*.json").read_text("utf-8"))
    require(source["tool"] == "spritemine-mmc3-register-trace-v1", "MMC3 tool ID")
    require(source["completed_frame_pairs"] == 2, "MMC3 frame pair count")
    require(source["dropped_writes"] == 0, "MMC3 dropped write")
    require(len(source["boundaries"]) == 4, "MMC3 boundary count")
    require(len(source["writes"]) == 4, "MMC3 write count")
    values = [(e["address"], e["value"], e["register"]) for e in source["writes"]]
    require(values == [
        (0x8000, 0x82, "bankSelect"), (0x8001, 10, "bankData"),
        (0x8000, 0x82, "bankSelect"), (0x8001, 10, "bankData"),
    ], "MMC3 register write values")
    require(all(e["ppu_scanline"] in (66, 67) for e in source["writes"]),
            "MMC3 scanline phase")


def inspect_mapping(folder: Path) -> None:
    source = json.loads(one(folder, "mapping_probe_*.json").read_text("utf-8"))
    require(source["tool"] == "spritemine-mapping-phase-v1", "Mapping tool ID")
    require(len(source["pairs"]) == 2, "Mapping phase sample count")
    for pair in source["pairs"]:
        require(pair["start"]["ppu_upper_nonzero"] == 4096, "Pre-render pattern")
        require(pair["end"]["ppu_upper_nonzero"] == 0, "Post-render pattern")
        require(pair["end"]["odd_tile_blank_patterns"] == 2, "Blank tiles")


def inspect_phase(folder: Path) -> None:
    source = verify_phase_session(one(folder, "phase_*.json"),
                                  folder / "synthetic.nes", allow_synthetic_rom=True)
    require(source["capture_count"] == 4, "Phase boundary sample count")
    require(source["blob_count"] == 12, "Phase binary count")
    require(source["mapper_model_status"] == "matches_known_boundaries",
            "Phase MMC3 mapping status")
    require(source["model_matches"] == 3, "Known physical ROM mappings")
    require(source["model_unknown_snapshots"] == 1, "First boundary unknown")
    require(source["model_mismatches"] == 0, "Phase mapping mismatch")


def inspect_render(folder: Path) -> None:
    manifest = one(folder, "render_*.json")
    rom = folder / "synthetic.nes"
    phase = verify_phase_session(manifest, rom, allow_synthetic_rom=True)
    require(phase["capture_count"] == 4, "Rendered frame pair count")
    require(phase["blob_count"] == 14, "Rendered binary count")
    require(phase["model_matches"] == 3 and phase["model_mismatches"] == 0,
            "Rendered PPU physical mapping")
    final = phase["snapshots"][3]
    require(final["screen_width"] == 256 and final["screen_height"] == 240,
            "Native RGB screen size")
    comparison = analyze_render_capture(manifest, rom, allow_synthetic_rom=True)
    require(comparison["geometry_supported"], "RGB geometry unsupported")
    require(comparison["ppu_mapping_verified"], "RGB mapper mismatch")
    require(not comparison["chr_bank_changes_before_object_bottom"],
            "Unexpected visible-region MMC3 bank switch")
    fraction = comparison["rgb_color_comparison"]["registered_oam_coordinates"][
        "modal_agreement_fraction"
    ]
    require(fraction == 1.0, "RGB vs hardware sprite index consistency")


def main() -> None:
    lua, luac = shutil.which("lua"), shutil.which("luac")
    if not lua or not luac:
        raise RuntimeError("Lua 5.4 and luac must be installed on PATH")
    version = subprocess.run([lua, "-v"], capture_output=True, text=True, check=True)
    report = (version.stdout + version.stderr).strip()
    require("Lua 5.4" in report, f"Expected Lua 5.4, got {report}")
    print("Lua runtime: " + report, flush=True)
    with TemporaryDirectory(prefix="spritemine-ci-") as scratch:
        folder = Path(scratch)
        env = dict(os.environ)
        env.update({
            "SPRITEMINE_TEST_OUTPUT": str(folder),
            "SPRITEMINE_CAPTURE_DIR": str(folder),
            "SPRITEMINE_TEST_ROM_SHA1": create_fixture(folder),
        })
        for name in SCRIPTS:
            path = MESENCE / name
            require(path.is_file(), f"Missing Lua file: {path}")
            execute(env, luac, "-p", str(path))
        for mock, probe in (
            ("mock_mesence.lua", "spritemine_frame_probe.lua"),
            ("mock_mesence_mapping.lua", "spritemine_mapping_probe.lua"),
            ("mock_mmc3_trace.lua", "spritemine_mmc3_trace.lua"),
            ("mock_mesence_phase.lua", "spritemine_phase_capture.lua"),
            ("mock_mesence_render.lua", "spritemine_render_probe.lua"),
        ):
            execute(env, lua, str(MESENCE / mock), str(MESENCE / probe))
        inspect_mmc3(folder)
        inspect_mapping(folder)
        inspect_phase(folder)
        inspect_render(folder)
        execute(env, sys.executable, str(MESENCE / "verify_capture.py"), str(folder))
        execute(env, sys.executable, str(MESENCE / "diagnose_capture.py"), str(folder))
    print("PASS: synthetic Lua phase, ROM, MMC3 and RGB checks", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, AssertionError, ValueError, RuntimeError,
            subprocess.CalledProcessError) as exc:
        print(f"FAIL: Windows Lua research checks: {exc}", file=sys.stderr)
        raise SystemExit(1)
