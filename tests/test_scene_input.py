import hashlib
import json

import pytest
from PIL import Image

from spritemine.scene import Scene
from spritemine.scene_input import adapt, compare_viewports


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_adapt_chr_local_capture_and_compare_scrolled_references(tmp_path):
    source = tmp_path / "inputs"
    source.mkdir()
    raw = bytes([128] * 8 + [0] * 8)
    (source / "chr.bin").write_bytes(raw)
    Image.new("RGBA", (3, 3), (10, 78, 40, 255)).save(source / "capture.png")
    desc = {
        "version": 1, "size": [24, 32], "tick_ms": 20, "ticks": 2,
        "tile_size": [8, 8], "background": [8, 9, 10],
        "assets": {
            "stripe": {
                "file": "chr.bin", "chr": {"offsets": [0]},
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "palette": [[0, 0, 0, 0], [220, 2, 3, 255], [0, 0, 0, 255], [0, 0, 0, 255]],
            },
            "capture": {"file": "capture.png", "crop": [1, 1, 1, 1]},
        },
        "layers": [
            {"tile_origin": [8, 16], "tiles": [["stripe"]]},
            {"tracks": [{"at": [8, 16], "cels": [{"asset": "capture", "ticks": 1}, {"ticks": 1}]}]},
        ],
    }
    descriptor = write_json(source / "descriptor.json", desc)
    recipe = adapt(descriptor, tmp_path / "bundle")
    scene = Scene.load(recipe)
    assert scene.render(0).getpixel((8, 16)) == (10, 78, 40)
    assert scene.render(1).getpixel((8, 16)) == (220, 2, 3)
    assert scene.render(1).getpixel((9, 16)) == (8, 9, 10)
    assert scene.sources["stripe"]["provenance"]["source_sha256"] == hashlib.sha256(raw).hexdigest()

    checks = []
    for tick, scroll, x, y, width in [(0, [8, 16], 2, 3, 8), (1, [7, 19], 3, 3, 8)]:
        reference = Image.new("RGB", (12, 10), (8, 9, 10))
        for row in range(y, 10):
            reference.putpixel((x, row), (220, 2, 3))
        if tick == 0:
            reference.putpixel((x, y), (10, 78, 40))
        name = f"ref{tick}.png"
        reference.save(source / name)
        checks.append({"file": name, "crop": [x, y, width, 4], "tick": tick, "scroll": scroll, "origin": [2, 3]})
    refs = write_json(source / "refs.json", {"checks": checks})
    assert [item["world_rect"] for item in compare_viewports(recipe, refs)] == [[8, 16, 8, 4], [8, 19, 8, 4]]
    assert [item["mismatched_pixels"] for item in compare_viewports(recipe, refs)] == [0, 0]
    reference.putpixel((3, 3), (220, 2, 4))  # blue-only change
    reference.save(source / "ref1.png")
    result = compare_viewports(recipe, refs)[1]
    assert result["mismatched_pixels"] == 1
    assert result["mismatch_bounds_in_crop"] == (0, 0, 1, 1)

    raw_reference = reference.tobytes()
    (source / "ref1.bin").write_bytes(raw_reference)
    checks[1].update(
        file="ref1.bin", format="rgb24", size=[12, 10],
        sha256=hashlib.sha256(raw_reference).hexdigest(),
    )
    write_json(refs, {"checks": checks})
    result = compare_viewports(recipe, refs)[1]
    assert result["mismatched_pixels"] == 1
    assert result["reference_sha256"] == checks[1]["sha256"]
    (source / "ref1.bin").write_bytes(raw_reference[:-1])
    with pytest.raises(ValueError, match="SHA-256"):
        compare_viewports(recipe, refs)
    checks[1].pop("sha256")
    write_json(refs, {"checks": checks})
    with pytest.raises(ValueError, match="data length"):
        compare_viewports(recipe, refs)

    desc["assets"]["stripe"]["chr"]["offsets"] = [16]
    write_json(descriptor, desc)
    with pytest.raises(ValueError, match="outside its source"):
        adapt(descriptor, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()
