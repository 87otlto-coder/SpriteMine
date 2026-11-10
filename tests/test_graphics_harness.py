"""Exercise the complete A/B/A verifier using generated CHR, palettes and screens."""
import json
from pathlib import Path
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
        log = ["restore 437 0"]
        bus = []
        for n in range(1, 65):
            log.extend(["oam 80,5,0,80,80,7,0,88", f"poll {n} {n} {buttons}|{buttons}"])
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
