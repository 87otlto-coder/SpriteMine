"""Read-only integrity checks for private SMB3 animation timeline archives.

File-level validation supports local previews without launching MesenCE.
Resume additionally revalidates every source A/B/A run before new captures.
No original game assets or frames are stored in this module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path, PureWindowsPath
from typing import Any

from PIL import Image

from .graphics_harness import private_folder


_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_hash(value: object, label: str) -> None:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise ValueError(f"Missing or invalid SHA-256: {label}")


def read_verified_timeline(timeline_file: Path) -> dict[str, Any]:
    """Check JSON, every original RGBA PNG, spritesheet and frame chronology.

    This verifies archive file integrity only; it DOES NOT independently
    revalidate emulator A/B/A evidence. Use verified_timeline_runs for resume.
    """
    path = private_folder(Path(timeline_file)).resolve(strict=True)
    if (path.name != "timeline.json" or path.parent.parent.name != "Animations"
            or path.parent.parent.parent.name != "SMB3"):
        raise ValueError("Expected FIXTURE/SMB3/Animations/<run>/timeline.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported timeline schema")
    frames = data.get("frames")
    if (not isinstance(frames, list) or len(frames) < 2
            or len(frames) != data.get("frame_count")):
        raise ValueError("Timeline frame count does not match frame records")
    for key in ("source_slot_sha256", "source_rom_sha256",
                "source_emulator_sha256", "source_probe_sha256"):
        _require_hash(data.get(key), key)
    if data.get("result") != "contiguous_verified_OAM_frame_timeline":
        raise ValueError("Unsupported timeline result")
    if data.get("input_plan") not in ("right", "neutral", "jump"):
        raise ValueError("Unrecognized input plan")

    images: list[Image.Image] = []
    holds: list[dict[str, Any]] = []
    frames_seen: set[int] = set()
    warmups_seen: set[int] = set()
    clocks: list[int] = []
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError(f"Frame {index} is not a record")
        number = frame.get("frame_count")
        warmup = frame.get("warmup")
        clock = frame.get("start_master_clock")
        if (type(number) is not int or type(warmup) is not int
                or type(clock) is not int or frame.get("timeline_index") != index):
            raise ValueError(f"Invalid frame identity at index {index}")
        if (number in frames_seen or warmup in warmups_seen
                or (index and (number != frames[index - 1]["frame_count"] + 1
                               or warmup != frames[index - 1]["warmup"] + 1
                               or clock <= clocks[-1]))):
            raise ValueError(f"Duplicate, discontinuous or unordered frame {index}")
        frames_seen.add(number)
        warmups_seen.add(warmup)
        clocks.append(clock)
        if frame.get("duration_frames") != 1:
            raise ValueError("Original one-frame events may not be collapsed")
        if frame.get("input_plan") != data["input_plan"]:
            raise ValueError("Frame input plan does not match timeline")
        if frame.get("restore") != data.get("restored_state"):
            raise ValueError("Frame restore identity differs")
        if frame.get("width") != 16 or frame.get("height") != 16:
            raise ValueError("Only verified 16x16 Mario frames are supported")
        if "emulator_portable_mode" in frame or "emulator_settings_sha256" in frame:
            mode = frame.get("emulator_portable_mode")
            config_sha = frame.get("emulator_settings_sha256")
            if type(mode) is not bool:
                raise ValueError("Frame portable emulator mode is invalid")
            if mode:
                _require_hash(config_sha, f"frame {index} portable settings")
            elif config_sha is not None:
                raise ValueError("Frame has unexpected portable settings hash")
        _require_hash(frame.get("rgba_sha256"), f"frame {index} RGBA")
        _require_hash(frame.get("png_sha256"), f"frame {index} PNG")
        filename = f"frame_{index:03d}_{number}.png"
        if frame.get("png_file") != filename:
            raise ValueError(f"Unsafe or unexpected PNG filename at index {index}")
        png = path.parent / filename
        if _digest(png.read_bytes()) != frame["png_sha256"]:
            raise ValueError(f"PNG file hash mismatch at frame {index}")
        with Image.open(png) as opened:
            opened.load()
            if opened.mode != "RGBA" or opened.size != (16, 16):
                raise ValueError(f"PNG mode or dimensions changed at frame {index}")
            image = opened.copy()
        if _digest(image.tobytes()) != frame["rgba_sha256"]:
            raise ValueError(f"RGBA pixels changed at frame {index}")
        images.append(image)
        if frame.get("identical_to_previous_frame") is not (
                index > 0 and frame["rgba_sha256"] == frames[index - 1]["rgba_sha256"]):
            raise ValueError("Incorrect repeated-frame marker")
        if holds and holds[-1]["rgba_sha256"] == frame["rgba_sha256"]:
            holds[-1]["last_timeline_index"] = index
            holds[-1]["last_emulator_frame"] = number
            holds[-1]["duration_frames"] += 1
        else:
            holds.append({
                "first_timeline_index": index,
                "last_timeline_index": index,
                "first_emulator_frame": number,
                "last_emulator_frame": number,
                "duration_frames": 1,
                "rgba_sha256": frame["rgba_sha256"],
            })

    for index, frame in enumerate(frames):
        expected_delta = clocks[index + 1] - clocks[index] if index + 1 < len(frames) else None
        if frame.get("delta_master_clock_to_next") != expected_delta:
            raise ValueError(f"Incorrect clock delta at frame {index}")
    if (data.get("first_emulator_frame") != frames[0]["frame_count"]
            or data.get("last_emulator_frame") != frames[-1]["frame_count"]
            or data.get("unique_visual_frame_count") != len({f["rgba_sha256"] for f in frames})
            or data.get("visual_hold_count") != len(holds)
            or data.get("visual_holds") != holds):
        raise ValueError("Timeline identity or visual hold summary mismatch")

    sheet_info = data.get("sheet")
    if not isinstance(sheet_info, dict) or sheet_info.get("filename") != "spritesheet.png":
        raise ValueError("Unsupported spritesheet layout")
    cols = min(8, len(frames))
    rows = math.ceil(len(frames) / cols)
    if (sheet_info.get("columns") != cols or sheet_info.get("rows") != rows
            or sheet_info.get("tile_width") != 16
            or sheet_info.get("tile_height") != 16):
        raise ValueError("Spritesheet geometry differs from frame records")
    _require_hash(sheet_info.get("png_sha256"), "spritesheet PNG")
    _require_hash(sheet_info.get("rgba_sha256"), "spritesheet RGBA")
    sheet_path = path.parent / "spritesheet.png"
    if _digest(sheet_path.read_bytes()) != sheet_info["png_sha256"]:
        raise ValueError("Spritesheet file hash mismatch")
    with Image.open(sheet_path) as opened:
        opened.load()
        if opened.mode != "RGBA" or opened.size != (16 * cols, 16 * rows):
            raise ValueError("Spritesheet mode or dimensions are invalid")
        sheet = opened.copy()
    if _digest(sheet.tobytes()) != sheet_info["rgba_sha256"]:
        raise ValueError("Spritesheet RGBA hash mismatch")
    for i, image in enumerate(images):
        x, y = (i % cols) * 16, (i // cols) * 16
        if sheet.crop((x, y, x + 16, y + 16)).tobytes() != image.tobytes():
            raise ValueError(f"Spritesheet frame {i} does not match PNG")
    return data


def verified_timeline_runs(
    timeline_file: Path, *, runs_parent_override: Path | None = None
) -> list[Path]:
    """Validate a prior timeline AND all immutable A/B/A source captures.

    Refuses a tampered manifest, replaced PNG, missing run, or provenance
    discrepancy before caller launches any new emulator process.
    """
    path = private_folder(Path(timeline_file)).resolve(strict=True)
    data = read_verified_timeline(path)
    archived_runs_parent = path.parent.parent.parent / "GraphicsValidation"
    runs_parent = (private_folder(Path(runs_parent_override)).resolve(strict=True)
                   if runs_parent_override is not None else archived_runs_parent)
    if runs_parent.name != "GraphicsValidation" or runs_parent.parent.name != "SMB3":
        raise ValueError("Relocated runs must be under FIXTURE/SMB3/GraphicsValidation")
    runs = []
    for frame in data["frames"]:
        original = str(frame["run_dir"])
        if runs_parent_override is not None:
            # The original manifest remains immutable. Resolve each archived
            # leaf only inside the explicitly selected private FIXTURE root;
            # verify every A/B/A byte through the normal validator below.
            source = PureWindowsPath(original)
            parts = source.parts
            if (len(parts) < 4 or parts[-3].upper() != "SMB3"
                    or parts[-2] != "GraphicsValidation"
                    or "FIXTURE" not in (part.upper() for part in parts)):
                raise ValueError("Untrusted source capture location in archived timeline")
            leaf = source.name
            if not leaf.startswith("anim-") or leaf in (".", "..") or ":" in leaf:
                raise ValueError("Invalid archived capture directory name")
            run = private_folder(runs_parent / leaf).resolve(strict=True)
        else:
            run = private_folder(Path(original)).resolve(strict=True)
        if run.parent != runs_parent:
            raise ValueError("Prior timeline refers outside expected GraphicsValidation folder")
        runs.append(run)
    if len(set(runs)) != len(runs):
        raise ValueError("Prior timeline contains duplicate source runs")

    # Import lazily: the timeline assembler does not depend on this module.
    from .animation_timeline import assemble_timeline

    rebuilt = assemble_timeline(runs, path.parent / "__never_written__", write=False)
    original = copy.deepcopy(data)
    for frame, source_run in zip(original["frames"], runs):
        frame.pop("png_sha256")
        if runs_parent_override is not None:
            # Compare all evidence fields unchanged except its absolute
            # filesystem locator, which necessarily differs after copying.
            frame["run_dir"] = str(source_run)
    original["sheet"].pop("png_sha256")
    if rebuilt != original:
        raise ValueError("Archived timeline disagrees with independently reverified A/B/A runs")
    return runs
