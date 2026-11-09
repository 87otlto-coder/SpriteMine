"""Validate MesenCE Lua research captures without exposing game assets.

Run with Python 3.11+; only stdlib is required. No file is modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

EXPECTED_SMB3_PRG1_SHA256 = (
    "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579"
)
CAPTURE_TOOL = "spritemine-mesence-endframe-v1"
BLOB_SUFFIXES = {
    "oam": "_oam.bin",
    "palette": "_palette.bin",
    "ppu_pattern": "_ppu_pattern.bin",
    "screen_rgb": "_screen_rgb.bin",
}
MAX_NES_BYTES = 64 * 1024 * 1024


def _rom_sha256(path: Path) -> str:
    if path.suffix.lower() == ".nes":
        if path.stat().st_size > MAX_NES_BYTES:
            raise ValueError("ROM exceeds safety limit")
        data = path.read_bytes()
    elif path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            items = [
                item for item in archive.infolist()
                if not item.is_dir() and item.filename.lower().endswith(".nes")
            ]
            if len(items) != 1 or items[0].file_size > MAX_NES_BYTES:
                raise ValueError("ZIP must contain exactly one size-limited NES ROM")
            with archive.open(items[0]) as inp:
                data = inp.read(MAX_NES_BYTES + 1)
    else:
        raise ValueError("ROM path must end in .nes or .zip")
    if len(data) > MAX_NES_BYTES:
        raise ValueError("ROM exceeds safety limit")
    return hashlib.sha256(data).hexdigest()


def verify_directory(folder: Path, rom_path: Path | None = None) -> dict[str, object]:
    """Return metadata/verification report, not raw sprite or screen data."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"Capture directory not found: {folder}")
    manifests = sorted(folder.glob("frame_??????????.json"))
    if not manifests:
        raise ValueError("No frame_XXXXXXXXXX.json captures found")

    rom_hash = _rom_sha256(Path(rom_path)) if rom_path is not None else None
    if rom_hash is not None and rom_hash != EXPECTED_SMB3_PRG1_SHA256:
        raise ValueError("Provided ROM is not the verified SMB3 US PRG1 / Revision A fixture")

    captures: list[dict[str, object]] = []
    previous_frame: int | None = None
    expected_mesen_rom_sha1: str | None = None
    for manifest in manifests:
        info = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(info, dict):
            raise ValueError(f"{manifest.name}: expected JSON object")
        if info.get("schema_version") != 1 or info.get("capture_tool") != CAPTURE_TOOL:
            raise ValueError(f"{manifest.name}: unsupported capture format")
        if info.get("evidence") != "captured" or info.get("event") != "endFrame":
            raise ValueError(f"{manifest.name}: missing capture evidence semantics")
        if info.get("console_type") != "Nes":
            raise ValueError(f"{manifest.name}: not an NES capture")
        frame = info.get("frame_count")
        if type(frame) is not int or frame < 0 or manifest.name != f"frame_{frame:010d}.json":
            raise ValueError(f"{manifest.name}: frame identity mismatch")
        if previous_frame is not None and frame <= previous_frame:
            raise ValueError("Capture frames are not strictly increasing")
        previous_frame = frame
        width, height = info.get("screen_width"), info.get("screen_height")
        if type(width) is not int or type(height) is not int:
            raise ValueError(f"{manifest.name}: missing screen dimensions")
        if not (1 <= width <= 512 and 1 <= height <= 512 and width * height <= 512 * 512):
            raise ValueError(f"{manifest.name}: unsupported screen size")
        if info.get("sprite_height") not in (8, 16):
            raise ValueError(f"{manifest.name}: unsupported sprite size")
        mesen_rom_sha1 = info.get("rom_sha1_reported_by_mesen")
        if not isinstance(mesen_rom_sha1, str) or not mesen_rom_sha1:
            raise ValueError(f"{manifest.name}: missing Mesen ROM identifier")
        if expected_mesen_rom_sha1 is None:
            expected_mesen_rom_sha1 = mesen_rom_sha1
        elif expected_mesen_rom_sha1 != mesen_rom_sha1:
            raise ValueError("Captures report different Mesen ROM identities")

        names = info.get("files")
        if not isinstance(names, dict) or set(names) != set(BLOB_SUFFIXES):
            raise ValueError(f"{manifest.name}: missing or unexpected capture files")
        basename = manifest.stem
        lengths = {"oam": 256, "palette": 32, "ppu_pattern": 8192, "screen_rgb": width * height * 3}
        sha256s: dict[str, str] = {}
        for key, suffix in BLOB_SUFFIXES.items():
            name = f"{basename}{suffix}"
            if names[key] != name:
                raise ValueError(f"{manifest.name}: invalid {key} filename")
            data_path = folder / name
            data = data_path.read_bytes()
            if len(data) != lengths[key]:
                raise ValueError(f"{name}: expected {lengths[key]} bytes, found {len(data)}")
            sha256s[key] = hashlib.sha256(data).hexdigest()
        captures.append({
            "frame_count": frame,
            "master_clock": info.get("master_clock"),
            "region": info.get("region"),
            "sprite_height": info["sprite_height"],
            "screen_size": [width, height],
            "blob_sha256": sha256s,
        })

    return {
        "result": "pass_structural_capture_validation",
        "capture_count": len(captures),
        "capture_tool": CAPTURE_TOOL,
        "verified_smb3_rom_provided": rom_hash is not None,
        "verified_rom_sha256": rom_hash,
        "mesen_rom_sha1_reported": expected_mesen_rom_sha1,
        "not_proven": [
            "same-frame atomicity",
            "input replay determinism",
            "effective CHR reads mapped to physical ROM offsets",
            "screen-buffer frame alignment",
            "authentic displayed sprite grouping and visibility",
        ],
        "captures": captures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SpriteMine MesenCE research frame capture")
    parser.add_argument("directory", type=Path, help="MesenCE LuaScriptData/spritemine_frame_probe directory")
    parser.add_argument("--rom", type=Path, help="Local SMB3 PRG1 .nes or single-ROM .zip (never uploaded)")
    args = parser.parse_args(argv)
    try:
        result = verify_directory(args.directory, args.rom)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"Capture invalid: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
