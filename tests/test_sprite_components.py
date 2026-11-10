"""Synthetic tests for NES 8x16 hardware sprite components, not character IDs."""

import pytest

from research.mesence.sprite_components import (
    collect_components, decode_component, preview_image,
)


def fixture(*, tile=7, attributes=0, y=160, x=100):
    oam = bytearray(256)
    for i in range(64):
        oam[4 * i] = 248  # Hardware Y 248 is off-screen.
    oam[40:44] = bytes((y, tile, attributes, x))
    ppu = bytearray(8192)
    base = 0x1000 if tile & 1 else 0
    top = base + (tile & 0xFE) * 16
    # First pixel of the upper 8x8 tile has palette index 1.
    ppu[top] = 0x80
    # First pixel of the lower 8x8 tile has palette index 2.
    ppu[top + 16 + 8] = 0x80
    palette = bytes(range(32))
    return bytes(oam), bytes(ppu), palette


def test_hardware_component_8x16_bank_address_and_alpha():
    oam, ppu, palette = fixture()
    components = collect_components(oam, ppu, palette)
    assert len(components) == 1
    c = components[0]
    assert c.oam_index == 10
    assert (c.x, c.y) == (100, 161)
    assert c.ppu_tile_addresses == (0x1060, 0x1070)
    assert c.pixels[0] == 1
    assert c.pixels[8 * 8] == 2
    assert c.pixels[1] == 0
    assert c.pixels.count(0) == 126
    assert c.sprite_palette_ram_bytes == (17, 18, 19)
    img = preview_image(c)
    assert img.size == (8, 16)
    assert img.getpixel((0, 0)) == (85, 85, 85, 255)
    assert img.getpixel((1, 0))[3] == 0
    assert img.getpixel((0, 8)) == (170, 170, 170, 255)


def test_horizontal_flip_keeps_rows_and_vertical_flip_swaps_halves():
    oam, ppu, palette = fixture(attributes=0xC2)
    c = decode_component(oam, ppu, palette, 10)
    assert c.flip_horizontal and c.flip_vertical
    assert c.sprite_palette_slot == 2
    assert c.pixels[15 * 8 + 7] == 1
    assert c.pixels[7 * 8 + 7] == 2
    assert c.pixels[0] == 0
    assert c.sprite_palette_ram_bytes == (25, 26, 27)


def test_hardware_priority_and_mask_bits():
    oam, ppu, palette = fixture(attributes=0x20 | 0x08 | 0x03)
    c = decode_component(oam, ppu, palette, 10)
    assert c.behind_background is True
    assert c.sprite_palette_slot == 3
    assert c.attributes == 43
    assert c.sprite_palette_ram_bytes == (29, 30, 31)


def test_even_tile_uses_lower_ppu_pattern_table():
    oam, ppu, palette = fixture(tile=6)
    c = decode_component(oam, ppu, palette, 10)
    assert c.ppu_tile_addresses == (0x0060, 0x0070)
    assert c.pixels[0] == 1
    assert c.pixels[64] == 2


def test_source_rom_offsets_are_per_mapped_one_kibibyte_slot():
    oam, ppu, palette = fixture()
    rom_offsets = [262160 + i * 1024 for i in range(8)]
    c = decode_component(oam, ppu, palette, 10, physical_rom_offsets=rom_offsets)
    assert c.source_rom_tile_offsets == (262160 + 4 * 1024 + 0x60,
                                         262160 + 4 * 1024 + 0x70)
    d = c.metadata()
    assert d["source_rom_tile_offsets"] == list(c.source_rom_tile_offsets)
    assert d["evidence"] == "captured_hardware_sprite_component_not_character"


def test_no_source_bank_mapping_is_invented():
    oam, ppu, palette = fixture()
    c = decode_component(oam, ppu, palette, 10)
    assert c.source_rom_tile_offsets is None


def test_y_coordinate_screen_filter_is_only_candidate_test():
    oam, ppu, palette = fixture(y=239)
    assert collect_components(oam, ppu, palette) == []
    all_components = collect_components(oam, ppu, palette, potentially_on_screen_only=False)
    assert len(all_components) == 64
    assert all_components[10].y == 240


@pytest.mark.parametrize("index", [-1, 64])
def test_invalid_oam_index_rejected(index):
    oam, ppu, palette = fixture()
    with pytest.raises(IndexError):
        decode_component(oam, ppu, palette, index)


def test_invalid_ppu_palette_and_mapping_rejected():
    oam, ppu, palette = fixture()
    with pytest.raises(ValueError, match="256 OAM"):
        decode_component(oam[:-1], ppu, palette, 10)
    with pytest.raises(ValueError, match="256 OAM"):
        decode_component(oam, ppu[:-1], palette, 10)
    with pytest.raises(ValueError, match="eight nonnegative"):
        decode_component(oam, ppu, palette, 10, physical_rom_offsets=[0] * 7)


def test_research_cli_session_preview_and_metadata(tmp_path, monkeypatch):
    import hashlib
    import json
    from research.mesence import sprite_components as component_module

    session = "phase_0000265171_1794292304"
    manifest = tmp_path / f"{session}.json"
    oam, ppu, palette = fixture()
    files = {}
    for key, data in (("oam", oam), ("ppu_pattern", ppu), ("palette", palette)):
        name = f"{session}_3_startFrame_{key}.bin"
        (tmp_path / name).write_bytes(data)
        files[key] = name
    manifest.write_text(json.dumps({
        "phase_captures": [{}, {}, {"files": files}, {}]
    }), encoding="utf-8")
    offsets = [262160 + 1024 * index for index in range(8)]
    snapshot = {
        "frame_count": 265172, "event": "startFrame", "sprite_height": 16,
        "sha256": {
            "oam": hashlib.sha256(oam).hexdigest(),
            "ppu_pattern": hashlib.sha256(ppu).hexdigest(),
            "palette": hashlib.sha256(palette).hexdigest(),
        },
        "model": {
            "matches_full_8k_ppu": True,
            "source_rom_offsets_per_ppu_slot": offsets,
        },
    }
    monkeypatch.setattr(
        component_module, "verify_phase_session",
        lambda *args: {
            "mapper_model_status": "matches_known_boundaries",
            "session_id": session,
            "snapshots": [None, None, snapshot, None],
            "rom_sha256": "a" * 64,
        },
    )
    target = tmp_path / "private_previews"
    result = component_module.inspect_session(
        manifest, tmp_path / "unused-rom.nes", sample_number=3, output_dir=target
    )
    assert result["result"] == "captured_8x16_hardware_components_only"
    assert result["potentially_on_screen_count"] == 1
    assert result["components"][0]["oam_index"] == 10
    assert result["components"][0]["source_rom_tile_offsets"][0] == offsets[4] + 0x60
    assert result["local_preview_exports"][0]["file"] == "hardware_oam_10_frame_265172.png"
    from PIL import Image
    with Image.open(target / "hardware_oam_10_frame_265172.png") as image:
        assert image.mode == "RGBA"
        assert image.size == (8, 16)
        assert image.getpixel((1, 0))[3] == 0
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        component_module.inspect_session(
            manifest, tmp_path / "unused-rom.nes", output_dir=target
        )


def test_preview_output_inside_git_repo_is_blocked(tmp_path, monkeypatch):
    import hashlib
    import json
    from research.mesence import sprite_components as module

    oam, ppu, palette = fixture()
    session = "phase_0000265171_1794292304"
    manifest = tmp_path / f"{session}.json"
    names = {}
    for key, data in (("oam", oam), ("ppu_pattern", ppu), ("palette", palette)):
        name = f"{session}_3_startFrame_{key}.bin"
        (tmp_path / name).write_bytes(data)
        names[key] = name
    manifest.write_text(json.dumps({
        "phase_captures": [{}, {}, {"files": names}, {}]
    }), encoding="utf-8")
    dummy = {"frame_count": 12, "event": "startFrame", "sprite_height": 16,
             "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in
                        (("oam", oam), ("ppu_pattern", ppu), ("palette", palette))},
             "model": {"matches_full_8k_ppu": True,
                       "source_rom_offsets_per_ppu_slot": [1234] * 8}}
    monkeypatch.setattr(module, "verify_phase_session", lambda *args: {
        "mapper_model_status": "matches_known_boundaries",
        "session_id": session, "snapshots": [None, None, dummy, None],
        "rom_sha256": "a" * 64,
    })
    checkout = tmp_path / "repo"
    checkout.mkdir()
    (checkout / ".git").mkdir()
    with pytest.raises(ValueError, match="inside a Git checkout"):
        module.inspect_session(manifest, tmp_path / "unused", output_dir=checkout / "art")
