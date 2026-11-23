"""Adapt local NES graphics and compare compositor viewports against PNG references."""

import argparse
import hashlib
import io
import json
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

from .chr import TILE_BYTES, decode_tile
from .scene import Scene, integers, viewport_to_world


def local_file(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError("input path escapes the descriptor directory")
    return path


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def chr_image(data, spec):
    columns, rows = integers(spec.get("grid", [1, 1]), 2, "CHR grid")
    offsets = spec["offsets"]
    if min(columns, rows) < 1 or columns * rows != len(offsets):
        raise ValueError("CHR offsets must fill the declared grid")
    image = Image.new("P", (columns * 8, rows * 8))
    image.putpalette([0, 0, 0, 85, 85, 85, 170, 170, 170, 255, 255, 255])
    for index, offset in enumerate(offsets):
        if type(offset) is not int or offset < 0 or offset % TILE_BYTES:
            raise ValueError("CHR offset must be a nonnegative aligned byte offset")
        end = offset + TILE_BYTES
        if end > len(data):
            raise ValueError("CHR offset is outside its source")
        tile = Image.frombytes("P", (8, 8), decode_tile(data[offset:end]))
        image.paste(tile, (index % columns * 8, index // columns * 8))
    return image


def adapt(descriptor, destination):
    """Materialize a recipe bundle from a normalized local input descriptor."""
    recipe = load_json(descriptor)
    root = descriptor.resolve().parent
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as workspace:
        bundle = Path(workspace) / "bundle"
        bundle.mkdir()
        for index, (name, spec) in enumerate(recipe["assets"].items()):
            data = local_file(root, spec["file"]).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if spec.pop("source_sha256", digest) != digest:
                raise ValueError(f"source SHA-256 mismatch: {name}")
            target = bundle / f"asset-{index:04}.png"
            if "chr" in spec:
                pattern = spec.pop("chr")
                if "palette" not in spec:
                    raise ValueError("CHR assets require an explicit RGBA palette")
                chr_image(data, pattern).save(target, bits=2)
                spec["provenance"] = {
                    **spec.get("provenance", {}), "source_sha256": digest,
                    "chr": pattern, "decoder": "spritemine.chr:nes_2bpp_v1",
                }
            else:
                target.write_bytes(data)
            spec.update(file=target.name, sha256=hashlib.sha256(target.read_bytes()).hexdigest())
        path = bundle / "recipe.json"
        path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
        Scene.load(path)
        bundle.rename(destination)
    return destination / "recipe.json"


def read_reference(root, check):
    """Read a PNG or packed, row-major RGB24 reference and retain its hash."""
    data = local_file(root, check["file"]).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if check.get("sha256", digest) != digest:
        raise ValueError("reference SHA-256 mismatch")
    format_name = check.get("format", "png")
    if format_name == "rgb24":
        width, height = integers(check["size"], 2, "RGB24 size")
        if min(width, height) < 1 or len(data) != width * height * 3:
            raise ValueError("RGB24 data length differs from its declared dimensions")
        return Image.frombytes("RGB", (width, height), data), digest
    if format_name != "png":
        raise ValueError(f"unsupported reference format: {format_name}")
    with Image.open(io.BytesIO(data), formats=["PNG"]) as image:
        return image.convert("RGB"), digest


def reference_world_origin(check, crop):
    """Resolve crop placement via explicit scroll or a measured world anchor."""
    x, y, width, height = crop
    if "playfield" in check:
        left, top, field_width, field_height = integers(check["playfield"], 4, "playfield")
        if (min(field_width, field_height) < 1 or x < left or y < top
                or x + width > left + field_width or y + height > top + field_height):
            raise ValueError("reference crop crosses the declared playfield boundary")
    if "anchor" not in check:
        return viewport_to_world((x, y), check["scroll"], check.get("origin", [0, 0]))
    if "scroll" in check or "origin" in check:
        raise ValueError("choose either a world anchor or scroll and origin")
    anchor = check["anchor"]
    return viewport_to_world((x, y), anchor["world"], anchor["capture"])


def compare_viewports(recipe, references):
    """Compare declared viewport rectangles at explicit ticks and camera offsets."""
    scene = Scene.load(recipe)
    root = references.resolve().parent
    checks = load_json(references)["checks"]
    if not checks:
        raise ValueError("at least one viewport check is required")
    results = []
    for check in checks:
        x, y, width, height = integers(check["crop"], 4, "reference crop")
        tick, = integers([check["tick"]], 1, "reference tick")
        wx, wy = reference_world_origin(check, (x, y, width, height))
        image, digest = read_reference(root, check)
        if min(x, y) < 0 or min(width, height) < 1 or (
            x + width > image.width or y + height > image.height
        ):
            raise ValueError("reference crop lies outside its image")
        expected = image.crop((x, y, x + width, y + height))
        if min(wx, wy) < 0 or wx + width > scene.size[0] or wy + height > scene.size[1]:
            raise ValueError("reference viewport lies outside the scene")
        actual = scene.render(tick).crop((wx, wy, wx + width, wy + height))
        delta = ImageChops.difference(expected, actual)
        bounds = delta.getbbox()
        red, green, blue = delta.split()
        changed = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        results.append({
            "reference": check["file"], "reference_sha256": digest,
            "tick": tick, "world_rect": [wx, wy, width, height],
            "pixels": width * height,
            "mismatched_pixels": width * height - changed.histogram()[0],
            "mismatch_bounds_in_crop": bounds,
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("adapt")
    build.add_argument("descriptor", type=Path)
    build.add_argument("destination", type=Path)
    compare = commands.add_parser("compare")
    compare.add_argument("recipe", type=Path)
    compare.add_argument("references", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "adapt":
            print(adapt(args.descriptor, args.destination))
            return 0
        results = compare_viewports(args.recipe, args.references)
        print(json.dumps(results, indent=2))
        return int(any(result["mismatched_pixels"] for result in results))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        parser.exit(2, f"scene input: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
