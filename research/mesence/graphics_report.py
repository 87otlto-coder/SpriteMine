"""Validate private, independent A/B/A legs and render an offline RGB comparison."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import re

from PIL import Image, ImageChops

from .analyze_render_capture import analyze_render_capture
from .decode_mmc3_trace import EXPECTED_SMB3_SHA256
from .graphics_harness import LEGS, digest, private_folder
from .nes_palette_reference import MESEN_REFERENCE_URL
from .verify_background_composite import analyze_two_renders
from .verify_phase_capture import verify_phase_session


def same(values, label):
    if any(value != values[0] for value in values[1:]):
        raise ValueError(f"{label} differs between replay legs")
    return values[0]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def trace_evidence(lines, launch):
    if not lines or not re.fullmatch(r"restore \d+ \d+", lines[0]) or lines[-1] != "complete":
        raise ValueError("Missing restore or completion record")
    clock = int(lines[0].split()[2])
    records = lines[1:-1]
    if len(records) != 2 * (62 + launch["warmup"]):
        raise ValueError("Wrong number of input polls")
    poses = []
    for i in range(0, len(records), 2):
        pose, poll = records[i:i + 2]
        if not re.fullmatch(r"oam (\d+,){7}\d+", pose):
            raise ValueError("Missing OAM history")
        poses.append([int(n) for n in pose[4:].split(",")])
        _, number, tick, pads = poll.split(" ")
        n = i // 2 + 1
        if not poll.startswith("poll ") or int(number) != n or int(tick) <= clock:
            raise ValueError("Input timeline out of order")
        clock = int(tick)
        ports = pads.split("|")
        if len(ports) != 2:
            raise ValueError("Expected two controller port observations")
        for port, buttons in enumerate(ports):
            if port == 1 and not buttons:
                continue
            expected = []
            for key in ("a", "b", "down", "left", "right", "select", "start", "up"):
                pressed = port == 0 and (
                    (key == "right" and launch["plan"] == "right" and n > 60)
                    or (key == "a" and launch["plan"] == "jump" and 60 < n <= 66)
                    or (key == "start" and launch["start_pulse"] and n == 4))
                expected.append(f"{key}={str(pressed).lower()}")
            if buttons != ",".join(expected):
                raise ValueError(f"Unexpected controller input at poll {n}")
    return poses


def check_controller_bus(data, launch, count):
    reads = {}
    for line in data.decode("ascii").splitlines():
        poll, address, bit = line.split()
        n = int(poll)
        if not 1 <= n <= count or address not in ("4016", "4017") or bit not in ("0", "1"):
            raise ValueError("Invalid controller bus sample")
        reads.setdefault((n, address), []).append(bit)
    for n in range(1, count + 1):
        player = ["0"] * 8
        if launch["start_pulse"] and n == 4:
            player[3] = "1"
        if launch["plan"] == "jump" and 60 < n <= 66:
            player[0] = "1"
        if launch["plan"] == "right" and n > 60:
            player[7] = "1"
        for address, expected in (("4016", player), ("4017", ["0"] * 8)):
            bits = reads.get((n, address), [])
            # SMB3 reads each pad twice. DMA can trigger extra reads and retries.
            if len(bits) < 16 or bits[:8] != expected or bits[-8:] != expected:
                raise ValueError(f"CPU did not receive planned input at poll {n} on {address}")


def observed_motion(plan, poses):
    stable = all(p == poses[59] for p in poses[53:60])
    paired = all(p[0] == p[4] and p[7] == p[3] + 8 for p in poses[59:])
    if not stable or not paired:
        return False
    baseline, end = poses[59], poses[-1]
    if plan == "neutral":
        return all(p == baseline for p in poses[59:])
    tiles_changed = any(p[1::4] != baseline[1::4] for p in poses[60:])
    if plan == "right":
        return tiles_changed and end[3] > baseline[3] and all(p[0] == baseline[0] for p in poses[59:])
    return tiles_changed and end[0] < baseline[0] and end[3] == baseline[3]


def validate(run, report, *, write_visuals=True):
    rom = run / "replay.nes"
    sources, phases, files, traces, identities, contexts = [], [], [], [], [], []
    for leg, hidden in LEGS:
        folder = run / leg
        meta = json.loads((folder / "launch.json").read_text())
        if (meta["leg"] != leg or meta["disable_sprites"] is not hidden or meta["exit_code"] != 0
                or meta["switches"] != ["--testRunner", "--timeout=30", "--doNotSaveSettings",
                                       "--nes.disableSprites=" + str(hidden).lower()]):
            raise ValueError("Wrong launch settings or incomplete emulator run")
        if (meta["slot_sha256"] != digest(run / "slot-copy.mss")
                or meta["probe_sha256"] != digest(run / "capture.lua")
                or meta["rom_sha256"] != EXPECTED_SMB3_SHA256
                or not re.fullmatch("[0-9a-f]{64}", meta["emulator_sha256"])
                or meta["plan"] not in ("neutral", "right", "jump")
                or type(meta["start_pulse"]) is not bool):
            raise ValueError("Invalid source provenance")
        identity = {k: meta[k] for k in ("slot_sha256", "probe_sha256", "rom_sha256",
                                              "emulator_sha256", "emulator_version", "plan", "warmup", "start_pulse")}
        # Old archives predate portable settings. New records must agree across
        # all three independent replay legs without changing legacy evidence.
        if "portable_mode" in meta or "portable_settings_sha256" in meta:
            if type(meta.get("portable_mode")) is not bool:
                raise ValueError("Invalid portable MesenCE launcher mode")
            config_sha = meta.get("portable_settings_sha256")
            if meta["portable_mode"]:
                if not isinstance(config_sha, str) or not re.fullmatch("[0-9a-f]{64}", config_sha):
                    raise ValueError("Invalid portable MesenCE settings fingerprint")
            elif config_sha is not None:
                raise ValueError("Unexpected portable settings fingerprint")
            identity["portable_mode"] = meta["portable_mode"]
            identity["portable_settings_sha256"] = config_sha
        identities.append(identity)
        capture, = folder.glob("render_*.json")
        files.append(capture)
        sources.append(json.loads(capture.read_text()))
        phases.append(verify_phase_session(capture, rom))
        lines = (folder / "replay.log").read_text().splitlines()
        poses = trace_evidence(lines, meta)
        traces.append(lines)
        hashes = []
        for i in range(1, 5):
            context = folder / f"context{i}.bin"
            if context.stat().st_size <= 4096:
                raise ValueError("Incomplete nametable and PPU context")
            hashes.append(digest(context))
        contexts.append(hashes)

    report["provenance"] = same(identities, "State/build/probe/input plan")
    history = same(traces, "Restore/input/OAM history")
    bus = same([(p.parent / "controller-bus.log").read_bytes() for p in files], "CPU controller reads")
    check_controller_bus(bus, identities[0], len(poses))
    report["controller_bus_sha256"] = hashlib.sha256(bus).hexdigest()
    report["controller_bus_reads"] = len(bus.splitlines())
    report["restore"] = history[0]
    report["input_history_sha256"] = fingerprint(history)
    report["context_sha256"] = same(contexts, "Nametable/PPU registers")
    writes = same([s["writes"] for s in sources], "Timed MMC3 writes")
    report["mmc3_trace_sha256"] = fingerprint(writes)
    for i in range(4):
        states = []
        for phase in phases:
            snap = dict(phase["snapshots"][i])
            snap["sha256"] = {k: v for k, v in snap["sha256"].items() if k != "screen_rgb"}
            states.append(snap)
        same(states, f"Boundary {i + 1}")
    report["boundaries"] = phases[0]["snapshots"]
    restored_frame = int(history[0].split()[1])
    polls = [int(line.split()[2]) for line in history if line.startswith("poll ")]
    for i in (0, 1):
        start, end = report["boundaries"][2*i:2*i+2]
        if (start["frame_count"] != restored_frame + len(polls) - 2 + i
                or not polls[-2+i] < start["master_clock"] < end["master_clock"]
                or (i == 0 and end["master_clock"] >= polls[-1])):
            raise ValueError("Capture boundary is detached from the restored frame or input clock")
    report["timing_sha256"] = fingerprint([[s[k] for k in ("frame_count", "master_clock",
                                         "ppu_scanline", "ppu_cycle")] for s in report["boundaries"]])
    for i in (1, 3):
        same([phases[j]["snapshots"][i]["sha256"]["screen_rgb"] for j in (0, 2)],
             "Enabled full-screen RGB")
    report["statuses"]["replay"] = "verified"
    if any((s["screen_width"], s["screen_height"]) != (256, 240)
           for phase in phases for s in phase["snapshots"][1::2]):
        raise NotImplementedError("Native 256x240 framebuffer required")
    paths = [p.parent / s["phase_captures"][3]["files"]["screen_rgb"] for p, s in zip(files, sources)]
    report["screens_sha256_A_B_A2"] = [digest(p) for p in paths]
    images = [Image.frombytes("RGB", (256, 240), p.read_bytes()) for p in paths]
    if write_visuals:
        for name, img in zip(
            ("A", "B", "A2", "RGB-difference"),
            images + [ImageChops.difference(*images[:2])],
        ):
            img.save(run / (name + ".png"))
    if phases[0]["mapper_model_status"] != "matches_known_boundaries":
        raise ValueError("MMC3 reconstruction failed")
    target = phases[0]["snapshots"][2]
    if not target["model"] or target["sprite_height"] != 16:
        raise NotImplementedError("Target requires a known mapping and 8x16 hardware sprites")
    diagnostic = analyze_render_capture(files[0], rom)
    report["components"] = diagnostic["sprite_positions"]
    report["palette_reference"] = MESEN_REFERENCE_URL
    report["palette_check"] = diagnostic["independent_default_palette_check"]
    if (diagnostic["chr_bank_changes_before_object_bottom"]
            or not diagnostic["oam_unchanged_between_start_and_end"]
            or not diagnostic["palette_ram_unchanged_between_start_and_end"]):
        raise NotImplementedError("OAM, palette or CHR changed during the sampled span")
    if diagnostic["independent_default_palette_check"]["status"] == "unsupported_palette_codes_for_restricted_reference":
        raise NotImplementedError("Unsupported NES palette code")
    oam_file = sources[0]["phase_captures"][2]["files"]["oam"]
    oam = (files[0].parent / oam_file).read_bytes()
    if any(oam[4*i + 2] & 0x20 for i in (10, 11)):
        raise NotImplementedError("Behind-background priority needs another model")
    pair = analyze_two_renders(files[0], files[1], rom)["comparison"]
    report["pixels"] = pair
    x, y, right, bottom = pair["bounds_xyxy_exclusive"]
    if (right - x, bottom - y) != (16, 16):
        raise NotImplementedError("Target OAM pair does not cover the supported 16x16 geometry")
    if pair["status"] != "region_exact_conditional_on_sprites_disabled_reference":
        raise ValueError(pair["status"])
    crops = [img.crop((x, y, right, bottom)) for img in images]
    crops.append(ImageChops.difference(*crops[:2]))
    strip = Image.new("RGB", (64, 16))
    for i, crop in enumerate(crops):
        strip.paste(crop, (16*i, 0))
    if write_visuals:
        strip.resize((512, 128), Image.Resampling.NEAREST).save(run / "region.png")
    report["statuses"]["pixels"] = "verified"
    plan = identities[0]["plan"]
    report["motion_observation"] = {"before_input": poses[59], "final_poll": poses[-1]}
    # Movement is an additional gate: a successful button readback alone cannot establish a pose.
    gate = {"neutral": "stationary OAM pair", "right": "walking", "jump": "jumping"}[plan]
    report["statuses"][gate] = "verified" if observed_motion(plan, poses) else "failed"


def publish(run, capture_error=None):
    run = private_folder(run)
    report = {"schema": 1, "statuses": {"replay": "not tested", "pixels": "not tested",
              "stationary OAM pair": "not tested", "walking": "not tested", "jumping": "not tested",
              "behind-background priority": "unsupported", "scanline sprite limit": "not tested"}}
    try:
        if capture_error is not None:
            raise ValueError(capture_error)
        validate(run, report)
    except (ValueError, OSError, KeyError, IndexError, TypeError, NotImplementedError) as exc:
        gate = "pixels" if report["statuses"]["replay"] == "verified" else "replay"
        report["statuses"][gate] = "unsupported" if isinstance(exc, NotImplementedError) else "failed"
        report["reason"] = str(exc)
    data = json.dumps(report, indent=2, sort_keys=True)
    (run / "report.json").write_text(data, encoding="utf-8")
    figures = "".join(f'<figure><img src="{name}.png" alt="{name}"><figcaption>{name}</figcaption></figure>'
                      for name in ("A", "B", "A2", "RGB-difference") if (run / (name + ".png")).exists()
                      and report["statuses"]["replay"] == "verified")
    if report["statuses"]["pixels"] == "verified":
        figures += '<figure><img src="region.png" alt="Four enlarged 16 by 16 regions"><figcaption>Target at 8×: A, B, A2, absolute RGB difference</figcaption></figure>'
    rows = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in report["statuses"].items())
    (run / "report.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>SMB3 graphics validation</title>'
        '<style>body{font:16px system-ui;margin:2em}th{text-align:left;padding-right:2em}'
        'figure{display:inline-block;margin:1em 1em 1em 0}img{image-rendering:pixelated}</style>'
        f'<h1>SMB3 graphics validation</h1><table>{rows}</table>{figures}'
        f'<details><summary>Evidence and hashes</summary><pre>{html.escape(data)}</pre></details>',
        encoding="utf-8")
    print(json.dumps(report["statuses"]))
    statuses = report["statuses"]
    return 0 if statuses["pixels"] == "verified" and "failed" not in statuses.values() else 3


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    raise SystemExit(publish(parser.parse_args().run))
