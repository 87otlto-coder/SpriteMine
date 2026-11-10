"""Synthetic regression tests for endFrame RGB vs 8x16 OAM pixel classes.

No copyrighted graphics; fitted RGB class colors only, not authentic NES colors.
"""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from research.mesence.analyze_render_capture import (
    _early_chr_changes,
    compare_color_groups,
    index_layer,
)


def component(*, oam_index=10, x=100, y=161, palette_slot=0, pixels=None):
    return SimpleNamespace(
        oam_index=oam_index, x=x, y=y,
        sprite_palette_slot=palette_slot,
        pixels=(pixels if pixels is not None else bytes([1, 2, 3, 0] * 32)),
    )


def rgb_test_screen(indexed, *, w=256, h=240):
    screen = bytearray(b"\x11\x11\x11" * (w * h))
    colors = {
        (0, 1): bytes.fromhex("AABBCC"),
        (0, 2): bytes.fromhex("112233"),
        (0, 3): bytes.fromhex("DDEEFF"),
        (1, 1): bytes.fromhex("776655"),
    }
    for (x, y), pair in indexed.items():
        screen[(y * w + x) * 3:(y * w + x) * 3 + 3] = colors[pair]
    return bytes(screen)


def test_full_indexed_color_consistency_and_transparent_pixels():
    comp = component()
    layer = index_layer([comp])
    assert len(layer) == 96  # Three opaque columns in each group of four.
    assert (103, 161) not in layer
    result = compare_color_groups(rgb_test_screen(layer), 256, 240, layer)
    assert result["pixels_sampled"] == 96
    assert result["modal_agreement_fraction"] == 1.0
    assert result["out_of_bounds"] == 0
    assert [v["inferred_modal_rgb"] for v in result["inferred_color_classes"]] == [
        "#AABBCC", "#112233", "#DDEEFF"
    ]


def test_overlapping_hardware_entries_use_lower_oam_index_only_in_diagnostic():
    comp_a = component(oam_index=10, pixels=bytes([1] * 128))
    comp_b = component(oam_index=11, pixels=bytes([2] * 128))
    layer = index_layer([comp_b, comp_a])
    assert len(layer) == 128
    assert set(layer.values()) == {(0, 1)}


def test_two_palette_slots_are_not_merged():
    a = component(oam_index=10, x=100, pixels=bytes([1] * 128))
    b = component(oam_index=11, x=108, palette_slot=1, pixels=bytes([1] * 128))
    layer = index_layer([a, b])
    report = compare_color_groups(rgb_test_screen(layer), 256, 240, layer)
    assert report["modal_agreement_fraction"] == 1.0
    assert len(report["inferred_color_classes"]) == 2
    assert [row["palette_slot"] for row in report["inferred_color_classes"]] == [0, 1]


def test_registered_shift_more_consistent_than_one_pixel_offset():
    import random
    rng = random.Random(121)
    comp = component(pixels=bytes(rng.randrange(4) for _ in range(128)))
    layer = index_layer([comp])
    screen = rgb_test_screen(layer)
    registered = compare_color_groups(screen, 256, 240, layer)
    displaced = compare_color_groups(screen, 256, 240, layer, dx=1)
    assert registered["modal_agreement_fraction"] == 1.0
    assert displaced["modal_agreement_fraction"] < 1.0


def test_out_of_bounds_excluded_without_wraparound():
    layer = {(255, 239): (0, 1)}
    data = bytes(256 * 240 * 3)
    result = compare_color_groups(data, 256, 240, layer, dx=1)
    assert result["pixels_sampled"] == 0
    assert result["out_of_bounds"] == 1
    assert result["modal_agreement_fraction"] is None


def test_rejects_rgb_buffer_size_mismatch():
    with pytest.raises(ValueError, match="dimensions"):
        compare_color_groups(bytes(80), 256, 240, {(100, 100): (0, 1)})


def test_detects_chr_bank_data_write_in_sprite_rows():
    begin = {"master_clock": 100}
    end = {"master_clock": 1000}
    manifest = {
        "writes": [
            {"master_clock": 150, "address": 0x8000, "value": 0x42,
             "ppu_scanline": 160, "ppu_cycle": 10},
            {"master_clock": 155, "address": 0x8001, "value": 53,
             "ppu_scanline": 160, "ppu_cycle": 25},
            {"master_clock": 400, "address": 0x8000, "value": 0x46,
             "ppu_scanline": 193, "ppu_cycle": 10},
            {"master_clock": 405, "address": 0x8001, "value": 10,
             "ppu_scanline": 193, "ppu_cycle": 40},
        ]
    }
    flagged = _early_chr_changes(manifest, begin, end, max_sprite_y=178)
    assert [(row["register"], row["value"]) for row in flagged] == [(2, 53)]


def test_mmc3_bit7_inversion_mode_switch_is_flagged():
    manifest = {
        "writes": [
            {"master_clock": 50, "address": 0x8000, "value": 0x46,
             "ppu_scanline": 247, "ppu_cycle": 50},
            {"master_clock": 150, "address": 0x8000, "value": 0xC6,
             "ppu_scanline": 50, "ppu_cycle": 50},
        ]
    }
    flagged = _early_chr_changes(
        manifest, {"master_clock": 100}, {"master_clock": 200}, 177
    )
    assert [(row["register"], row["value"]) for row in flagged] == [(-1, 0xC6)]


def test_independent_mesen_default_2c02_reference_exact_rgb_without_fitting():
    from research.mesence.analyze_render_capture import compare_independent_reference_palette
    palette = bytearray(32)
    palette[0x11:0x14] = bytes((0x16, 0x36, 0x0F))
    indexed = {
        (2, 3): (0, 1), (3, 3): (0, 2), (4, 3): (0, 3),
        (4, 4): (0, 1),
    }
    screen = bytearray(bytes(8 * 8 * 3))
    for (x, y), color in {
        (2, 3): "B53120",
        (3, 3): "FECCC5",
        (4, 3): "000000",
        (4, 4): "B53120",
    }.items():
        start = (y * 8 + x) * 3
        screen[start:start + 3] = bytes.fromhex(color)
    actual = compare_independent_reference_palette(
        bytes(screen), 8, 8, indexed, bytes(palette)
    )
    assert actual["status"] == "reference_opaque_pixels_exact"
    assert actual["pixels_expected"] == 4
    assert actual["pixels_exact"] == 4
    assert actual["exact_fraction"] == 1.0
    assert [r["reference_rgb"] for r in actual["sprite_palette_entries"]] == [
        "#B53120", "#FECCC5", "#000000"
    ]
    # One incorrect observed pixel must fail, not be absorbed by modal fitting.
    wrong = bytearray(screen)
    start = (3 * 8 + 3) * 3
    wrong[start:start + 3] = bytes.fromhex("111111")
    result = compare_independent_reference_palette(
        bytes(wrong), 8, 8, indexed, bytes(palette)
    )
    assert result["status"] == "reference_opaque_pixels_mismatch"
    assert result["pixels_exact"] == 3
    assert result["pixels_mismatched"] == 1
    assert result["sample_mismatch_positions"] == [{"x": 3, "y": 3}]


def test_independent_default_palette_unavailable_for_unresearched_nes_codes():
    from research.mesence.analyze_render_capture import compare_independent_reference_palette
    palette = bytearray(32)
    palette[0x11:0x14] = bytes((0x12, 0x36, 0x0F))
    result = compare_independent_reference_palette(
        bytes(4 * 4 * 3), 4, 4, {(1, 1): (0, 1)}, bytes(palette)
    )
    assert result["status"] == "unsupported_palette_codes_for_restricted_reference"
    assert result["unrecognized_codes"] == ["0x12"]
    assert result["exact_fraction"] is None
    assert result["pixels_compared"] == 0
    assert not result["pixels_exact"]


def test_independent_palette_rejects_partial_buffers_and_invalid_slots():
    from research.mesence.analyze_render_capture import compare_independent_reference_palette
    with pytest.raises(ValueError, match="screen dimensions"):
        compare_independent_reference_palette(bytes(2), 4, 4, {}, bytes(32))
    with pytest.raises(ValueError, match="exactly 32"):
        compare_independent_reference_palette(bytes(48), 4, 4, {}, bytes(31))
    with pytest.raises(ValueError, match="palette slot/index"):
        compare_independent_reference_palette(
            bytes(48), 4, 4, {(1, 1): (4, 1)}, bytes(32)
        )
