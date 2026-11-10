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
