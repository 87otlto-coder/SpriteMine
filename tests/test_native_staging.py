import csv
import hashlib
import json

import pytest
from PIL import Image

from spritemine.native_staging import COLUMNS, import_staging
from spritemine.scene import Scene
from spritemine.scene_coverage import coverage, inspection
from spritemine.scene_export import export


def test_native_staging_to_scene_exports_and_coverage(tmp_path):
    capture = tmp_path / "capture"
    folder = capture / "B"
    folder.mkdir(parents=True)
    log = folder / "background-staging.tsv"
    with log.open("w", encoding="ascii", newline="") as out:
        writer = csv.writer(out, delimiter="\t")
        writer.writerow(COLUMNS)
        for sequence, half in enumerate((0, 1), 1):
            writer.writerow((sequence, "pattern", 7, 100 + half, 0, 0, 1,
                             0, 3, half, 6 + half, 0, 0, 1))
            (folder / f"bg-{sequence:04d}-pattern.bin").write_bytes(
                bytes([64 + half, 66 + half]) * 27
            )
            (folder / f"bg-{sequence:04d}-tiles.bin").write_bytes(bytes([128]) * 432)
    (capture / "report.json").write_text(json.dumps({
        "neutral": True, "background_staging": {
            "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        },
    }))
    profile = tmp_path / "rgb.bin"
    profile.write_bytes(bytes(channel for i in range(64) for channel in (i, 0, 0)))
    palette = bytes(range(32))
    for frame, solid_index in ((7, 1), (8, 2)):
        ppu = bytearray(0x3000)
        offset = 0x1000 + 64 * 16
        start = offset + (solid_index - 1) * 8
        ppu[start:start + 8] = bytes([255] * 8)
        (folder / f"{frame}-start-ppu.bin").write_bytes(ppu)
        (folder / f"{frame}-start-palette.bin").write_bytes(palette)
        (folder / f"{frame}-start-ppu-state.txt").write_text(
            "ppu.control.backgroundPatternAddr=4096\nppu.mask.grayscale=false\n"
            "ppu.paletteRamMask=63\nppu.intensifyColorBits=0\n"
        )
    recipe = import_staging(capture, 7, 7, profile, tmp_path / "scene", screens=1)
    repeat = import_staging(capture, 7, 7, profile, tmp_path / "repeat", screens=1)
    changed = import_staging(capture, 7, 8, profile, tmp_path / "changed", screens=1)
    assert recipe.read_bytes() == repeat.read_bytes()
    assert Scene.load(recipe).render(0).getpixel((48, 416)) == (9, 0, 0)
    assert Scene.load(changed).render(0).getpixel((48, 416)) == (10, 0, 0)
    assert Scene.load(recipe).render(0).getpixel((56, 416)) == (0, 0, 0)
    manifest = export(recipe, tmp_path / "output")
    assert manifest["staging_provenance"]["staging_frame"] == 7
    with Image.open(tmp_path / "output" / "scene.gif") as gif:
        assert gif.size == (256, 432)
    expected = Image.new("RGB", (16, 16))
    expected.paste((9, 0, 0), (0, 0, 8, 8))
    expected.save(tmp_path / "reference.png")
    refs = tmp_path / "references.json"
    refs.write_text(json.dumps({"checks": [{
        "file": "reference.png", "crop": [0, 0, 16, 16], "tick": 0,
        "anchor": {"capture": [0, 0], "world": [48, 416]},
    }]}))
    report = coverage(recipe, refs)
    assert report["rows"][26][3]["matched_ticks"] == [0]
    assert report["rows"][25][3]["matched_ticks"] == []
    assert report["rows"][26][2]["tiles"] == []
    failed = coverage(changed, refs)
    assert failed["samples"][0]["mismatched_pixels"] == 64
    assert failed["rows"][26][3]["mismatch_bounds_ticks"] == [0]
    assert "026 ???+" in inspection(report)

    with log.open("a", encoding="ascii", newline="") as out:
        writer = csv.writer(out, delimiter="\t")
        for sequence, half in enumerate((0, 1), 3):
            writer.writerow((sequence, "pattern", 8, 200 + half, 0, 0, 1,
                             0, 4, half, 8 + half, 0, 0, 1))
            (folder / f"bg-{sequence:04d}-pattern.bin").write_bytes(
                (folder / f"bg-{half + 1:04d}-pattern.bin").read_bytes()
            )
            (folder / f"bg-{sequence:04d}-tiles.bin").write_bytes(bytes([128]) * 432)
    report_path = capture / "report.json"
    replay = json.loads(report_path.read_text())
    replay["background_staging"]["log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
    report_path.write_text(json.dumps(replay))
    with pytest.raises(ValueError, match="incompatible graphics snapshot"):
        import_staging(capture, 7, 7, profile, tmp_path / "mixed", screens=1,
                       additional_frames=[8])
    (folder / "8-start-ppu.bin").write_bytes((folder / "7-start-ppu.bin").read_bytes())
    combined = import_staging(capture, 7, 7, profile, tmp_path / "combined", screens=1,
                              additional_frames=[8])
    assert Scene.load(combined).render(0).getpixel((64, 416)) == (9, 0, 0)
    assert json.loads(combined.read_text())["staging_provenance"]["staging_frames"] == [7, 8]
    (folder / "bg-0004-tiles.bin").write_bytes(bytes([129]) * 432)
    with pytest.raises(ValueError, match="inconsistent logical map"):
        import_staging(capture, 7, 7, profile, tmp_path / "changed-map", screens=1,
                       additional_frames=[8])

    (folder / "bg-0002-pattern.bin").write_bytes(bytes(53))
    with pytest.raises(ValueError, match="pattern or logical length"):
        import_staging(capture, 7, 7, profile, tmp_path / "invalid", screens=1)
    assert not (tmp_path / "invalid").exists()
