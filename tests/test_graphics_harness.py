"""Exercise the complete A/B/A verifier using generated CHR, palettes and screens."""
import json
import shutil

import pytest

from research.mesence import decode_mmc3_trace, graphics_report as report
from research.mesence.graphics_harness import LEGS, digest
from research.mesence.nes_palette_reference import sprite_rgba_from_default_reference
from research.mesence.sprite_components import decode_component
from test_phase_capture import make_session


@pytest.fixture
def run(tmp_path, monkeypatch):
    manifest, rom, source = make_session(tmp_path)
    root = tmp_path / "FIXTURE"
    root.mkdir()
    shutil.copyfile(rom, root / "replay.nes")
    for mod in (report, decode_mmc3_trace):
        monkeypatch.setattr(mod, "EXPECTED_SMB3_SHA256", digest(rom))
    for name in ("slot-copy.mss", "capture.lua"):
        (root / name).write_bytes(b"synthetic")
    session = manifest.stem.replace("phase_", "render_")
    source.update(session_id=session, capture_tool="spritemine-mesence-render-capture-v1")
    oam = bytearray([248] * 256)
    oam[40:48] = bytes([80, 5, 0, 80, 80, 7, 0, 88])
    palette = bytearray(32)
    palette[17:20] = [22, 54, 15]
    normal = bytearray([42] * (256 * 240 * 3))
    bg = bytes(normal)
    pattern = (tmp_path / source["phase_captures"][2]["files"]["ppu_pattern"]).read_bytes()
    for idx in (10, 11):
        comp = decode_component(oam, pattern, palette, idx)
        for i, color in enumerate(comp.pixels):
            if color:
                pos = ((comp.y + i // 8) * 256 + comp.x + i % 8) * 3
                normal[pos:pos + 3] = sprite_rgba_from_default_reference(palette, 0, color)[:3]
    for leg, hidden in LEGS:
        folder = root / leg
        folder.mkdir()
        info = json.loads(json.dumps(source))
        for i, snap in enumerate(info["phase_captures"]):
            (folder / f"context{i+1}.bin").write_bytes(bytes(4200))
            for k, name in snap["files"].items():
                dest = name.replace(manifest.stem, session)
                snap["files"][k] = dest
                (folder / dest).write_bytes({"oam": oam, "palette": palette}.get(k, (tmp_path / name).read_bytes()))
            snap.update(screen_width=None, screen_height=None)
            snap["files"]["screen_rgb"] = None
            if i % 2:
                screen = f"{session}_{i+1}_endFrame_screen_rgb.bin"
                snap["files"]["screen_rgb"] = screen
                snap.update(screen_width=256, screen_height=240)
                (folder / screen).write_bytes(bg if hidden else normal)
        (folder / (session + ".json")).write_text(json.dumps(info))
        launch = dict(leg=leg, disable_sprites=hidden, exit_code=0, emulator_version="synthetic",
                      switches=["--testRunner", "--timeout=30", "--doNotSaveSettings",
                                "--nes.disableSprites=" + str(hidden).lower()],
                      slot_sha256=digest(root / "slot-copy.mss"), probe_sha256=digest(root / "capture.lua"),
                      emulator_sha256="0" * 64, rom_sha256=digest(rom), start_pulse=False, plan="neutral", warmup=2)
        (folder / "launch.json").write_text(json.dumps(launch))
        buttons = ",".join(k + "=false" for k in "a b down left right select start up".split())
        log = ["restore 438 0"]
        bus = []
        for n in range(1, 65):
            log.extend(["oam 80,5,0,80,80,7,0,88", f"poll {n} {300 if n == 64 else n} {buttons}|{buttons}"])
            for addr in ("4016", "4017"):
                bus.extend([f"{n} {addr} 0"] * 16)
        (folder / "replay.log").write_text("\n".join(log + ["complete"]))
        (folder / "controller-bus.log").write_text("\n".join(bus))
    return root


def test_generated_end_to_end(run):
    assert report.publish(run) == 0
    result = json.loads((run / "report.json").read_text())
    assert result["statuses"]["pixels"] == "verified"
    assert result["pixels"]["opaque_expected"] + result["pixels"]["transparent_expected"] == 256
    assert (run / "RGB-difference.png").exists()
    assert "RGB-difference.png" in (run / "report.html").read_text()


@pytest.mark.parametrize("kind", ["clock", "context", "input", "bus", "return RGB", "slot"])
def test_mismatched_return_leg_fails_closed(run, kind):
    folder = run / "A2"
    path = next(folder.glob("render*.json"))
    if kind == "clock":
        data = json.loads(path.read_text())
        data["phase_captures"][0]["master_clock"] -= 1
        path.write_text(json.dumps(data))
    elif kind == "context":
        with (folder / "context1.bin").open("ab") as f:
            f.write(b"x")
    elif kind == "input":
        p = folder / "replay.log"
        p.write_text(p.read_text().replace("a=false", "a=true", 1))
    elif kind == "bus":
        for leg, _ in LEGS:
            p = run / leg / "controller-bus.log"
            p.write_text(p.read_text().replace("4016 0", "4016 1", 1))
    elif kind == "return RGB":
        p = next(folder.glob("*2_endFrame_screen_rgb.bin"))
        rgb = bytearray(p.read_bytes())
        rgb[0] ^= 1
        p.write_bytes(rgb)
    else:
        (run / "slot-copy.mss").write_bytes(b"changed")
    assert report.publish(run) == 3
    assert json.loads((run / "report.json").read_text())["statuses"]["replay"] == "failed"
    assert not (run / "RGB-difference.png").exists()


@pytest.mark.parametrize("plan", ["right", "jump"])
def test_motion_requires_displacement_and_tile_change(plan):
    start = [97, 5, 0, 127, 97, 7, 0, 135]
    poses = [start] * 70
    assert not report.observed_motion(plan, poses)
    moved = start.copy()
    if plan == "right":
        moved[3] += 1
        moved[7] += 1
    else:
        moved[0] -= 8
        moved[4] -= 8
    poses[-1] = moved
    assert not report.observed_motion(plan, poses)
    moved[1] = 25
    assert report.observed_motion(plan, poses)


def test_right_motion_accepts_verified_vertical_drift_without_new_jump_input():
    """Real SMB3 warmup 26 moves Y 97 -> 98 at poll 88 while holding Right.

    Requiring Y to remain stationary is not a rightward-movement invariant.
    The paired OAM sprites, tile transition and positive X progress still are.
    """
    baseline = [97, 5, 0, 127, 97, 7, 0, 135]
    poses = [baseline.copy() for _ in range(88)]
    for index in range(60, 88):
        poses[index] = [97, 27, 64, 128, 97, 25, 64, 136]
    poses[-1] = [98, 27, 64, 128, 98, 25, 64, 136]
    assert report.observed_motion("right", poses)

    # Gravity alone cannot establish walking; X still has to progress.
    no_x_progress = [p.copy() for p in poses]
    for pose in no_x_progress[60:]:
        pose[3] = 127
        pose[7] = 135
    assert not report.observed_motion("right", no_x_progress)

    # Both hardware sprite components must remain vertically aligned.
    misaligned_pair = [p.copy() for p in poses]
    misaligned_pair[-1][4] = 97
    assert not report.observed_motion("right", misaligned_pair)

    # Right motion still needs a tile transition.
    no_tile_transition = [p.copy() for p in poses]
    for pose in no_tile_transition[60:]:
        pose[1] = 5
        pose[5] = 7
    assert not report.observed_motion("right", no_tile_transition)

    # Neutral must still reject all changes, even a valid right-moving pose.
    assert not report.observed_motion("neutral", poses)


def test_identical_but_unrelated_restore_rejected(run):
    for leg, _ in LEGS:
        p = run / leg / "replay.log"
        p.write_text(p.read_text().replace("restore 438", "restore 10"))
    assert report.publish(run) == 3
    assert "detached" in json.loads((run / "report.json").read_text())["reason"]

def test_portable_settings_fingerprint_must_agree_across_aba(run):
    """Optional portable launch metadata is checked without rejecting old archives."""
    for leg, _ in LEGS:
        path = run / leg / "launch.json"
        launch = json.loads(path.read_text(encoding="utf-8"))
        launch["portable_mode"] = True
        launch["portable_settings_sha256"] = "a" * 64
        path.write_text(json.dumps(launch), encoding="utf-8")
    assert report.publish(run) == 0
    altered = run / "B" / "launch.json"
    data = json.loads(altered.read_text(encoding="utf-8"))
    data["portable_settings_sha256"] = "b" * 64
    altered.write_text(json.dumps(data), encoding="utf-8")
    assert report.publish(run) == 3
    assert json.loads((run / "report.json").read_text())["statuses"]["replay"] == "failed"


def test_portable_mode_cannot_claim_missing_profile_hash(run):
    path = run / "A" / "launch.json"
    launch = json.loads(path.read_text(encoding="utf-8"))
    launch["portable_mode"] = True
    launch["portable_settings_sha256"] = None
    path.write_text(json.dumps(launch), encoding="utf-8")
    assert report.publish(run) == 3
    assert "portable" in json.loads((run / "report.json").read_text())["reason"].lower()
