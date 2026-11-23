"""Source-free regression tests plus optional user-local SMB3 ROM integration."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "m1_world11"))

from goal_card import (
    CARD_FRAMES, CARD_GAME_TICKS_PER_SYMBOL, CARD_POSITION_WORLD11,
    decode_mirrored_oam_8x16, build,
)


def test_card_object_source_mapping_and_combined_period():
    assert CARD_POSITION_WORLD11 == (2688, 336)
    assert CARD_GAME_TICKS_PER_SYMBOL == 8
    assert CARD_FRAMES == (("mushroom", 0x51, 1),
                           ("flower", 0x53, 2),
                           ("star", 0x55, 1))
    assert 12 % 4 == 0 and 12 % 3 == 0  # lcm(4 background, 3 card)
    assert [CARD_FRAMES[t % 3][0] for t in range(12)] == [
        "mushroom", "flower", "star"] * 4


def test_8x16_oam_pair_is_mirrored_and_uses_transparent_zero():
    # Original graphics bytes are NOT needed for this regression.
    patterns = bytearray(8192)
    pattern_base = 0x1500  # OAM tile 0x51 selects 8x16 PPU table 1
    patterns[pattern_base] = 0x80  # code 1 at top-left of left half
    patterns[pattern_base + 16] = 0x80  # code 1 at bottom-half top-left
    palette = bytearray(32)
    palette[16 + 1 * 4 + 1] = 0x02
    rgb = bytearray(192)
    rgb[2 * 3:2 * 3 + 3] = bytes([10, 20, 30])
    pic = decode_mirrored_oam_8x16(bytes(patterns), bytes(palette), bytes(rgb), 0x51, 1)
    assert pic.size == (16, 16)
    assert pic.getpixel((0, 0)) == pic.getpixel((15, 0)) == (10, 20, 30, 255)
    assert pic.getpixel((0, 8)) == pic.getpixel((15, 8)) == (10, 20, 30, 255)
    assert pic.getpixel((1, 0))[3] == 0
    assert pic.getpixel((14, 0))[3] == 0
    assert pic.getpixel((0, 1))[3] == 0


def test_sprite_rom_data_validation_rejects_bad_inputs():
    with pytest.raises(ValueError, match="8 KiB"):
        decode_mirrored_oam_8x16(b"", bytes(32), bytes(192), 0x51, 1)
    with pytest.raises(ValueError, match="64 NES RGB"):
        decode_mirrored_oam_8x16(bytes(8192), bytes(32), bytes(191), 0x51, 1)
    with pytest.raises(ValueError, match="palette"):
        decode_mirrored_oam_8x16(bytes(8192), bytes(32), bytes(192), 0x51, 4)


def test_private_rom_card_assets_and_scene_are_reproducible_opt_in(tmp_path):
    rom = os.environ.get("SPRITEMINE_PRIVATE_ROM_ZIP")
    graphics = os.environ.get("SPRITEMINE_PRIVATE_GRAPHICS_ZIP")
    rgb = os.environ.get("SPRITEMINE_PRIVATE_RGB_PROFILE")
    if not all((rom, graphics, rgb)):
        pytest.skip("Private, owner-supplied SMB3 ROM and graphics snapshot are not in public CI")

    from make_m1_bundle import build as build_static
    from animate_world11 import build as build_background
    from spritemine.scene import Scene

    static = build_static(Path(rom), tmp_path / "static", graphics_zip=Path(graphics), rgb=Path(rgb))
    animated = build_background(Path(rom), static, Path(graphics), Path(rgb), tmp_path / "animated")
    goal_recipe = build(Path(rom), animated, Path(graphics), Path(rgb), tmp_path / "goal")
    recipe = json.loads(goal_recipe.read_text(encoding="utf-8"))
    assert recipe["ticks"] == 12 and recipe["tick_ms"] == 130
    assert recipe["layers"][-1]["tracks"][0]["at"] == [2688, 336]
    assert len(recipe["layers"][-1]["tracks"][0]["cels"]) == 3
    assert len(recipe["layers"][1]["tracks"]) == 51
    assert recipe["staging_provenance"]["goal_roulette"]["source_object_record"] == [0x41, 0xA8, 0x15]
    scene = Scene.load(goal_recipe)
    assert scene.size == (2816, 432)
    image0 = scene.render(0)
    image1 = scene.render(1)
    image2 = scene.render(2)
    assert len({i.crop((2688, 336, 2704, 352)).tobytes() for i in (image0, image1, image2)}) == 3
    with pytest.raises(FileExistsError):
        build(Path(rom), animated, Path(graphics), Path(rgb), tmp_path / "goal")


def test_12_step_scene_has_independent_3_and_4_phase_loops(tmp_path):
    """Small original-art fixture establishes the GIF export timing contract."""
    from PIL import Image
    from goal_card import export_goal_scene
    from spritemine.scene import Scene
    root = tmp_path / "scene"
    root.mkdir()
    assets = {}
    for kind, number in (("background", 4), ("roulette", 3)):
        for phase in range(number):
            name = f"{kind}_{phase}"
            image = Image.new("RGB", (4, 4),
                              (30 + phase * 40, 20 if kind == "background" else 80, 10))
            file = root / (name + ".png")
            image.save(file)
            assets[name] = {"file": file.name}
    recipe = {
        "version": 1, "size": [8, 4], "tile_size": [4, 4],
        "ticks": 12, "tick_ms": 130, "background": [0, 0, 0],
        "assets": assets, "layers": [{"tracks": [
            {"at": [0, 0], "cels": [
                {"asset": f"background_{k}", "ticks": 1} for k in range(4)]},
            {"at": [4, 0], "cels": [
                {"asset": f"roulette_{k}", "ticks": 1} for k in range(3)]}
        ]}]
    }
    source = root / "recipe.json"
    source.write_text(json.dumps(recipe), encoding="utf-8")
    scene = Scene.load(source)
    assert scene.render(0) != scene.render(1)
    assert scene.render(0).getpixel((4, 0)) == scene.render(3).getpixel((4, 0))
    assert scene.render(0).getpixel((0, 0)) == scene.render(4).getpixel((0, 0))
    report = export_goal_scene(source, tmp_path / "export")
    assert report["frame_count"] == 12
    assert report["gif_rgb_matches_every_png_frame"]
    assert len(report["frame_png_sha256"]) == 12
