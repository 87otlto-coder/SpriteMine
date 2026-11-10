"""Build a verified SMB3 Mario frame timeline from adjacent A/B/A replay windows.

Each input is an immutable private GraphicsValidation run from PR #5. We
revalidate all three emulator legs *without writing to the run directory*.
Only the ROM-backed second startFrame and the corresponding endFrame are
accepted. One-frame-spaced warmup runs provide contiguous target frames.

Frame counts, PPU master clocks, controller plans and pixel hashes remain
explicit. Repeated visual frames are retained (no dropped holds), and no
millisecond frame duration or complete animation identity is invented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

from PIL import Image

from . import graphics_report
from .graphics_harness import private_folder
from .sprite_components import compose_explicit_oam_group, decode_component


SCHEMA = 1
GROUP = (10, 11)
MOTION_GATE = {
    "neutral": "stationary OAM pair",
    "right": "walking",
    "jump": "jumping",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _initial_report() -> dict[str, Any]:
    return {
        "statuses": {
            "replay": "not tested",
            "pixels": "not tested",
            "stationary OAM pair": "not tested",
            "walking": "not tested",
            "jumping": "not tested",
            "behind-background priority": "unsupported",
            "scanline sprite limit": "not tested",
        }
    }


def load_verified_window(run_dir: Path) -> tuple[dict[str, Any], Image.Image]:
    """Re-verify a prior A/B/A run, decode one source-backed 16x16 frame.

    This function intentionally does not create files or modify input runs.
    It allows only the existing supported #10/#11 SMB3 small Mario pair.
    """
    run = private_folder(Path(run_dir)).resolve(strict=True)
    if not run.is_dir():
        raise ValueError(f"Missing GraphicsValidation run directory: {run}")
    archived = json.loads((run / "report.json").read_text(encoding="utf-8"))
    if archived.get("schema") != SCHEMA or not isinstance(archived.get("statuses"), dict):
        raise ValueError("Missing or unsupported archived A/B/A report")

    live = _initial_report()
    graphics_report.validate(run, live, write_visuals=False)

    plan = live["provenance"]["plan"]
    if plan not in MOTION_GATE:
        raise ValueError(f"Unsupported controller plan: {plan}")
    for gate in ("replay", "pixels", MOTION_GATE[plan]):
        if live["statuses"].get(gate) != "verified":
            raise ValueError(f"Replay gate not verified: {gate}")

    # The original report must refer to exactly this verified run, not a
    # previously edited, stale or unrelated metadata report.
    if archived["statuses"].get("pixels") != "verified":
        raise ValueError("Archived report was never marked verified")
    for key in ("provenance", "restore", "timing_sha256",
                "controller_bus_sha256", "input_history_sha256",
                "context_sha256", "mmc3_trace_sha256", "screens_sha256_A_B_A2"):
        if archived.get(key) != live.get(key):
            raise ValueError(f"Archived A/B/A evidence changed: {key}")

    pair = live["pixels"]
    if pair["status"] != "region_exact_conditional_on_sprites_disabled_reference":
        raise ValueError("Independent background gate not verified")
    if (pair["opaque_reference_rgb_exact"] != pair["opaque_expected"]
            or pair["transparent_screen_equals_background"] != pair["transparent_expected"]
            or pair["control_ring_mismatches"] != 0):
        raise ValueError("Full 16x16 pixel comparison did not pass")

    path, = (run / "A").glob("render_*.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    files = manifest["phase_captures"][2]["files"]
    raw = path.parent
    oam = (raw / files["oam"]).read_bytes()
    ppu = (raw / files["ppu_pattern"]).read_bytes()
    palette = (raw / files["palette"]).read_bytes()
    start = live["boundaries"][2]
    end = live["boundaries"][3]
    if start["frame_count"] != end["frame_count"] or start["event"] != "startFrame":
        raise ValueError("Missing corresponding start/end capture frames")
    mapped = start["model"]
    if mapped is None or not mapped["matches_full_8k_ppu"]:
        raise ValueError("Source ROM to PPU mapping not independently verified")
    if start["sprite_height"] != 16:
        raise ValueError("This research step supports only 8x16 hardware sprites")

    components = [
        decode_component(
            oam, ppu, palette, index,
            physical_rom_offsets=mapped["source_rom_offsets_per_ppu_slot"],
        )
        for index in GROUP
    ]
    if any(component.behind_background for component in components):
        raise ValueError("Behind-background priority is not supported")
    image, group = compose_explicit_oam_group(
        components, reference_palette_ram=palette
    )
    if image.size != (16, 16):
        raise ValueError("Selected hardware OAM pair is not exactly 16x16")
    if ((group["left"], group["top"], 16, 16) !=
            (pair["bounds_xyxy_exclusive"][0], pair["bounds_xyxy_exclusive"][1], 16, 16)):
        raise ValueError("Image position differs from validated A/B/A rectangle")
    if (group["nontransparent_pixel_count"] != pair["opaque_expected"] or
            group["transparent_pixel_count"] != pair["transparent_expected"]):
        raise ValueError("RGBA alpha mask differs from independently validated pixels")
    if image.getbbox() is None:
        raise ValueError("Empty sprite frame cannot be accepted")

    frame = {
        "status": "verified_captured_frame_subset",
        "provenance": "decoded_from_rom_mapped_8x16_OAM",
        "frame_count": start["frame_count"],
        "start_master_clock": start["master_clock"],
        "end_master_clock": end["master_clock"],
        "run_dir": str(run),
        "input_plan": plan,
        "warmup": live["provenance"]["warmup"],
        "restore": live["restore"],
        "controller_bus_sha256": live["controller_bus_sha256"],
        "ppu_start_sha256": start["sha256"]["ppu_pattern"],
        "oam_start_sha256": start["sha256"]["oam"],
        "palette_start_sha256": start["sha256"]["palette"],
        "rendered_rgb_sha256": live["screens_sha256_A_B_A2"][0],
        "background_rgb_sha256": live["screens_sha256_A_B_A2"][1],
        "oam_group": list(GROUP),
        "position_x": group["left"],
        "position_y": group["top"],
        "width": 16,
        "height": 16,
        "opaque_pixels": group["nontransparent_pixel_count"],
        "transparent_pixels": group["transparent_pixel_count"],
        "tile_ids": [c.tile_id for c in components],
        "flip_horizontal": [c.flip_horizontal for c in components],
        "flip_vertical": [c.flip_vertical for c in components],
        "sprite_palette_slots": [c.sprite_palette_slot for c in components],
        "source_rom_tile_offsets": [
            list(c.source_rom_tile_offsets or ()) for c in components
        ],
        "rgba_sha256": _sha(image.tobytes()),
    }
    return {"frame": frame, "source": live["provenance"]}, image


def assemble_timeline(
    run_dirs: list[Path], output_dir: Path,
    *,
    write: bool = True,
) -> dict[str, Any]:
    """Strictly sequence one-frame-apart, fully verified existing A/B/A runs.

    Every source is reverified on read. No new MesenCE execution occurs.
    write=False computes only the manifest and checks; used by tests and
    potential future preview UI. No graphics are committed to Git.
    """
    if len(run_dirs) < 2:
        raise ValueError("Need at least two different A/B/A runs for a timeline")
    if len({Path(p).resolve() for p in run_dirs}) != len(run_dirs):
        raise ValueError("Duplicate run directories are not valid timeline evidence")
    records = [load_verified_window(Path(run)) for run in run_dirs]
    ordered = sorted(records, key=lambda p: p[0]["frame"]["frame_count"])
    references = [record[0]["source"] for record in ordered]
    identity = ("slot_sha256", "probe_sha256", "rom_sha256",
                "emulator_sha256", "emulator_version", "plan", "start_pulse")
    for key in identity:
        if len({str(source[key]) for source in references}) != 1:
            raise ValueError(f"Different replay source identity: {key}")
    restored = {record[0]["frame"]["restore"] for record in ordered}
    if len(restored) != 1:
        raise ValueError("Animation windows did not restore the same slot/clock")
    frame_counts = [record[0]["frame"]["frame_count"] for record in ordered]
    warmups = [record[0]["frame"]["warmup"] for record in ordered]
    if any(b - a != 1 for a, b in zip(frame_counts, frame_counts[1:])):
        raise ValueError("Animation windows must capture contiguous frame numbers")
    if any(b - a != 1 for a, b in zip(warmups, warmups[1:])):
        raise ValueError("Animation windows must use consecutive warmup values")
    clocks = [record[0]["frame"]["start_master_clock"] for record in ordered]
    if any(b <= a for a, b in zip(clocks, clocks[1:])):
        raise ValueError("Animation master clocks must increase strictly")

    frames = []
    for index, (info, image) in enumerate(ordered):
        f = dict(info["frame"])
        f["timeline_index"] = index
        f["duration_frames"] = 1
        f["delta_master_clock_to_next"] = (
            clocks[index + 1] - clocks[index] if index + 1 < len(clocks) else None
        )
        f["identical_to_previous_frame"] = (
            index > 0 and f["rgba_sha256"] == frames[-1]["rgba_sha256"]
        )
        f["png_file"] = f"frame_{index:03d}_{f['frame_count']}.png"
        frames.append(f)

    count = len(ordered)
    columns = min(8, count)
    rows = math.ceil(count / columns)
    sheet = Image.new("RGBA", (16 * columns, 16 * rows), (0, 0, 0, 0))
    for index, (_, image) in enumerate(ordered):
        sheet.alpha_composite(
            image, dest=((index % columns) * 16, (index // columns) * 16)
        )
    report = {
        "schema_version": SCHEMA,
        "result": "contiguous_verified_OAM_frame_timeline",
        "source": "A/B/A replay windows, one independently verified endFrame per run",
        "source_slot_sha256": references[0]["slot_sha256"],
        "source_rom_sha256": references[0]["rom_sha256"],
        "source_emulator_sha256": references[0]["emulator_sha256"],
        "source_probe_sha256": references[0]["probe_sha256"],
        "input_plan": references[0]["plan"],
        "restored_state": next(iter(restored)),
        "frame_count": count,
        "first_emulator_frame": frame_counts[0],
        "last_emulator_frame": frame_counts[-1],
        "timing": {
            "units": "NES emulator frames",
            "duration_frames_per_entry": 1,
            "nominal_fps": None,
            "ms_per_frame": None,
            "reason": "No wall-clock timing inferred from isolated captures",
            "repeated_rgba_frames_retained": True,
        },
        "sheet": {
            "filename": "spritesheet.png",
            "columns": columns,
            "rows": rows,
            "tile_width": 16,
            "tile_height": 16,
            "rgba_sha256": _sha(sheet.tobytes()),
        },
        "frames": frames,
        "unverified": [
            "complete game animation identity or loop boundaries",
            "absolute milliseconds without an independently verified NTSC frame clock",
            "background priority, OAM sprite limit and all other poses",
            "sprite content or palette for any uncaptured frames",
            "independent emulator replay outside supported MesenCE build",
        ],
    }
    target = private_folder(Path(output_dir))
    for record in records:
        run = Path(record[0]["frame"]["run_dir"])
        if target == run or run in target.parents or target in run.parents:
            raise ValueError("Output cannot be inside or replace an archived run directory")
    if write:
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite existing animation output: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.mkdir()
        for index, (_, image) in enumerate(ordered):
            f = frames[index]
            image.save(target / f["png_file"])
            f["png_sha256"] = _sha((target / f["png_file"]).read_bytes())
        sheet.save(target / "spritesheet.png")
        report["sheet"]["png_sha256"] = _sha((target / "spritesheet.png").read_bytes())
        (target / "timeline.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Assemble contiguous, previously verified SMB3 A/B/A replay frames"
    )
    parser.add_argument("runs", nargs="+", type=Path, help="Existing A/B/A run directories")
    parser.add_argument("--output", type=Path, required=True,
                        help="New local FIXTURE animation directory; must not exist")
    args = parser.parse_args(argv)
    try:
        result = assemble_timeline(args.runs, args.output)
    except (OSError, ValueError, KeyError, TypeError, IndexError,
            json.JSONDecodeError) as exc:
        print(f"SpriteMine animation timeline unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "result": result["result"],
        "frame_count": result["frame_count"],
        "first_emulator_frame": result["first_emulator_frame"],
        "last_emulator_frame": result["last_emulator_frame"],
        "output": str(Path(args.output).resolve()),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
