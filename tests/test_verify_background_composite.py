"""Synthetic background-reference verifier tests; no SMB3 game pixels."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from research.mesence.verify_background_composite import compare_region_with_bounds


def _fixture():
    width, height = 256, 240
    background = bytearray(bytes.fromhex("223344") * (width * height))
    normal = bytearray(background)
    indexed = {
        (100, 160): (0, 1),
        (101, 160): (0, 2),
        (100, 161): (0, 3),
        (102, 161): (0, 1),
    }
    palette = bytearray(32)
    palette[0x11:0x14] = bytes((0x16, 0x36, 0x0F))
    colors = {
        (0, 1): bytes.fromhex("B53120"),
        (0, 2): bytes.fromhex("FECCC5"),
        (0, 3): bytes.fromhex("000000"),
    }
    for (x, y), identity in indexed.items():
        begin = (y * width + x) * 3
        normal[begin:begin + 3] = colors[identity]
    return normal, background, indexed, bytes(palette)


def test_exact_opaque_and_transparent_pixels_with_independent_bg():
    normal, bg, indexed, palette = _fixture()
    report = compare_region_with_bounds(
        bytes(normal), bytes(bg), 256, 240,
        indexed, palette, bbox=(100, 160, 104, 164)
    )
    assert report["status"] == "region_exact_conditional_on_sprites_disabled_reference"
    assert report["opaque_expected"] == 4
    assert report["opaque_reference_rgb_exact"] == 4
    assert report["opaque_reference_rgb_mismatches"] == 0
    assert report["sprite_visible_rgb_diff_from_reference"] == 4
    assert report["transparent_expected"] == 12
    assert report["transparent_screen_equals_background"] == 12
    assert report["transparent_screen_mismatches"] == 0
    assert report["control_ring_mismatches"] == 0
    assert report["control_ring_exact"] > 0


def test_transparency_mismatch_is_not_hidden_by_perfect_opaque_match():
    normal, bg, indexed, palette = _fixture()
    begin = (162 * 256 + 103) * 3
    normal[begin:begin + 3] = bytes.fromhex("AA0000")
    report = compare_region_with_bounds(
        bytes(normal), bytes(bg), 256, 240,
        indexed, palette, bbox=(100, 160, 104, 164)
    )
    assert report["status"] == "composited_region_mismatch"
    assert report["opaque_reference_rgb_exact"] == 4
    assert report["transparent_screen_equals_background"] == 11
    assert report["transparent_screen_mismatches"] == 1
    assert {"x": 103, "y": 162, "class": "transparent"} in report["first_mismatch_positions"]


def test_wrong_opaque_color_fails_even_when_bg_matches():
    normal, bg, indexed, palette = _fixture()
    off = (160 * 256 + 101) * 3
    normal[off:off + 3] = bytes.fromhex("FFFFFF")
    report = compare_region_with_bounds(
        bytes(normal), bytes(bg), 256, 240,
        indexed, palette, bbox=(100, 160, 104, 164)
    )
    assert report["status"] == "composited_region_mismatch"
    assert report["opaque_reference_rgb_mismatches"] == 1
    assert report["transparent_screen_mismatches"] == 0


def test_changed_background_ring_invalidates_scene_even_with_accurate_sprite():
    normal, bg, indexed, palette = _fixture()
    off = (159 * 256 + 101) * 3
    bg[off:off + 3] = bytes.fromhex("010203")
    report = compare_region_with_bounds(
        bytes(normal), bytes(bg), 256, 240,
        indexed, palette, bbox=(100, 160, 104, 164)
    )
    assert report["status"] == "unverified_different_background_context"
    assert report["control_ring_mismatches"] == 1


def test_same_screen_refused_as_background_evidence():
    bg = bytes.fromhex("000000") * (256 * 240)
    palette = bytearray(32)
    palette[0x13] = 0x0F
    # Black indexed pixel and black background are indistinguishable. A
    # "background-only" render that shows no differences proves nothing.
    report = compare_region_with_bounds(
        bg, bg, 256, 240, {(100, 160): (0, 3)}, bytes(palette),
        bbox=(100, 160, 104, 164),
    )
    assert report["status"] == "ambiguous_no_evidence_sprite_display_was_disabled"
    assert report["sprite_visible_rgb_diff_from_reference"] == 0


@pytest.mark.parametrize(
    "bad_bbox", [
        (-1, 10, 10, 20),
        (10, 10, 10, 20),
        (10, 20, 20, 20),
        (254, 230, 257, 240),
    ]
)
def test_invalid_coordinates_explicitly_rejected(bad_bbox):
    normal, bg, indexed, palette = _fixture()
    with pytest.raises(ValueError, match="out of bounds"):
        compare_region_with_bounds(
            bytes(normal), bytes(bg), 256, 240,
            indexed, palette, bbox=bad_bbox,
        )


def test_unsupported_nes_palette_code_is_rejected():
    normal, bg, indexed, palette = _fixture()
    palette = bytearray(palette)
    palette[0x11] = 0x12
    with pytest.raises(ValueError, match="unsupported"):
        compare_region_with_bounds(
            bytes(normal), bytes(bg), 256, 240,
            indexed, bytes(palette), bbox=(100, 160, 104, 164),
        )


def test_unsupported_native_geometry_and_malformed_buffers():
    normal, bg, indexed, palette = _fixture()
    with pytest.raises(ValueError, match="Native 256x240"):
        compare_region_with_bounds(
            bytes(normal), bytes(bg), 255, 240,
            indexed, palette, bbox=(100, 160, 104, 164)
        )
    with pytest.raises(ValueError, match="dimensions"):
        compare_region_with_bounds(
            bytes(normal)[:-3], bytes(bg), 256, 240,
            indexed, palette, bbox=(100, 160, 104, 164)
        )


def test_pair_analyzer_requires_matching_replay_state_and_reads_real_rgb(tmp_path, monkeypatch):
    import hashlib
    import json
    from research.mesence import verify_background_composite as module
    from research.mesence.sprite_components import decode_component
    from research.mesence.analyze_render_capture import index_layer
    from research.mesence.nes_palette_reference import sprite_rgba_from_default_reference

    oam = bytearray([0] * 256)
    for i in range(64):
        oam[4 * i] = 248
    oam[40:44] = bytes((159, 7, 0, 100))
    oam[44:48] = bytes((159, 5, 0, 108))
    ppu = bytearray(8192)
    ppu[0x1060] = 0x80
    ppu[0x1040] = 0x80
    palette = bytearray(32)
    palette[0x11:0x14] = bytes((0x16, 0x36, 0x0F))
    offsets = [262160 + 1024 * i for i in range(8)]
    comps = [
        decode_component(bytes(oam), bytes(ppu), bytes(palette), i,
                         physical_rom_offsets=offsets)
        for i in (10, 11)
    ]
    indexed = index_layer(comps)
    normal_rgb = bytearray(bytes.fromhex("223344") * (256 * 240))
    bg_rgb = bytearray(normal_rgb)
    for (x, y), (slot, idx) in indexed.items():
        rgb = sprite_rgba_from_default_reference(bytes(palette), slot, idx)
        off = (y * 256 + x) * 3
        normal_rgb[off:off + 3] = bytes(rgb[:3])

    files = []
    fake_reports = {}
    for variant, rgb in (("visible", bytes(normal_rgb)), ("hidden", bytes(bg_rgb))):
        folder = tmp_path / variant
        folder.mkdir()
        manifest_path = folder / f"render_0000000500_123456789{0 if variant == 'visible' else 1}.json"
        names = {"oam": "oam.bin", "ppu_pattern": "ppu.bin", "palette": "palette.bin"}
        for name, blob in (("oam", bytes(oam)), ("ppu", bytes(ppu)), ("palette", bytes(palette))):
            (folder / f"{name}.bin").write_bytes(blob)
        (folder / "rgb.bin").write_bytes(rgb)
        manifest_path.write_text(json.dumps({
            "phase_captures": [{}, {}, {"files": names},
                               {"files": {"screen_rgb": "rgb.bin"}}]
        }), encoding="utf-8")
        start = {
            "event": "startFrame", "frame_count": 500, "master_clock": 100,
            "ppu_scanline": -1, "ppu_cycle": 0,
            "sprite_height": 16,
            "sha256": {
                "oam": hashlib.sha256(bytes(oam)).hexdigest(),
                "ppu_pattern": hashlib.sha256(bytes(ppu)).hexdigest(),
                "palette": hashlib.sha256(bytes(palette)).hexdigest(),
            },
            "model": {"matches_full_8k_ppu": True,
                      "source_rom_offsets_per_ppu_slot": offsets},
        }
        end = {
            "event": "endFrame", "frame_count": 500, "master_clock": 200,
            "ppu_scanline": 240, "ppu_cycle": 0,
            "sha256": {
                **start["sha256"],
                "screen_rgb": hashlib.sha256(rgb).hexdigest(),
            },
            "screen_width": 256, "screen_height": 240,
        }
        fake_reports[manifest_path.resolve()] = {
            "capture_tool": "spritemine-mesence-render-capture-v1",
            "mapper_model_status": "matches_known_boundaries",
            "rom_sha256": "a" * 64,
            "snapshots": [{}, {}, start, end],
            "session_id": manifest_path.stem,
        }
        files.append(manifest_path)

    monkeypatch.setattr(module, "verify_phase_session", lambda path, *args, **kwargs:
                        fake_reports[Path(path).resolve()])
    report = module.analyze_two_renders(files[0], files[1], tmp_path / "rom.ne s")
    assert report["comparison"]["status"] == (
        "region_exact_conditional_on_sprites_disabled_reference"
    )
    assert report["matched_source_ppu_oam_palette_and_frame_clock"] is True
    assert report["comparison"]["opaque_expected"] == 2
    assert report["comparison"]["transparent_expected"] == 254
    assert report["comparison"]["transparent_screen_equals_background"] == 254
    assert report["comparison"]["sprite_visible_rgb_diff_from_reference"] == 2
    assert report["frame_count"] == 500
    assert report["foreground_rgb_sha256"] != report["background_reference_rgb_sha256"]

    # A nearby-looking but different frame may NOT be called a matched replay.
    fake_reports[files[1].resolve()]["snapshots"][2]["frame_count"] = 501
    with pytest.raises(ValueError, match="frame/clock-aligned"):
        module.analyze_two_renders(files[0], files[1], tmp_path / "unused-rom")
