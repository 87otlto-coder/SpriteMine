"""Synthetic tests for read-only hardware sprite diagnostics."""

from research.mesence.diagnose_capture import analyze_frame


def _oam_with_hidden_slots() -> bytearray:
    data = bytearray(256)
    for slot in range(64):
        data[4 * slot] = 0xF8
    return data


def test_8x16_tile_bank_selection_flags_and_blank_warning():
    oam = _oam_with_hidden_slots()
    oam[40:44] = bytes((161, 7, 0x40, 114))  # tile 7 uses 0x1000 bank
    oam[44:48] = bytes((161, 5, 0x60, 122))
    pattern = bytes(8192)
    result = analyze_frame(bytes(oam), pattern, 16)
    assert result["possible_on_screen_oam_count"] == 2
    assert result["blank_pattern_entry_count"] == 2
    entries = result["possible_on_screen_oam_entries"]
    assert entries[0]["oam_index"] == 10
    assert entries[0]["ppu_pattern_table"] == 1
    assert entries[0]["ppu_pattern_base"] == 0x1060
    assert entries[0]["y"] == 162
    assert entries[0]["flip_horizontal"] is True
    assert entries[1]["behind_background"] is True
    assert "verify mapper state" in result["warning"]


def test_nonblank_patterns_have_no_blank_warning():
    oam = _oam_with_hidden_slots()
    oam[:4] = bytes((0, 7, 0, 13))
    pattern = bytearray(8192)
    pattern[0x1060] = 0x80
    result = analyze_frame(bytes(oam), bytes(pattern), 16)
    assert result["blank_pattern_entry_count"] == 0
    assert result["pattern_bytes_nonzero_upper_4k"] == 1
    assert result["warning"] is None


def test_8x8_does_not_invent_pattern_table():
    oam = _oam_with_hidden_slots()
    oam[:4] = bytes((0, 3, 0, 12))
    result = analyze_frame(bytes(oam), bytes(8192), 8)
    entry = result["possible_on_screen_oam_entries"][0]
    assert entry["ppu_pattern_table"] is None
    assert entry["blank_pattern_at_capture"] is None
    assert result["blank_pattern_entry_count"] == 0
