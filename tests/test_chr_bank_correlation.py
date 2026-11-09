"""Synthetic ROM/trace fixtures: no copyrighted assets committed."""

import pytest
from research.mesence.correlate_chr_banks import (
    expected_mmc3_pages, inspect_pattern, trace_chr_mappings,
)


def test_mode_zero_uses_r0_r1_on_lower_4k():
    regs = {0: 92, 1: 94, 2: 126, 3: 126, 4: 126, 5: 126}
    assert expected_mmc3_pages(regs, 0) == [92, 93, 94, 95, 126, 126, 126, 126]
    assert expected_mmc3_pages(regs, 1) == [126, 126, 126, 126, 92, 93, 94, 95]


def test_exact_matching_and_ambiguous_identical_banks():
    physical = [bytes([i]) * 1024 for i in (1, 2, 3, 4, 0, 0)]
    pattern = b"".join(physical[:5] + [physical[4]] * 3)
    windows = inspect_pattern(b"".join(physical), pattern)
    assert [item["ppu_start"] for item in windows] == [1024 * i for i in range(8)]
    assert windows[0]["physical_1k_chr_bank_matches"] == [0]
    assert windows[4]["physical_1k_chr_bank_matches"] == [4, 5]
    assert windows[4]["unique_match"] is False
    assert windows[4]["nonzero_bytes"] == 0


def test_chr_mode_is_bit_7_not_bit_6():
    rows = []
    clock = 1000
    for reg, value in enumerate((92, 94, 126, 126, 126, 126)):
        rows.append({"master_clock": clock, "address": 0x8000, "value": 0x40 | reg,
                     "frame": 10, "ppu_scanline": 193, "ppu_cycle": 10})
        clock += 3
        rows.append({"master_clock": clock, "address": 0x8001, "value": value,
                     "frame": 10, "ppu_scanline": 193, "ppu_cycle": 13})
        clock += 3
    trace = {"tool": "spritemine-mmc3-register-trace-v1", "dropped_writes": 0, "writes": rows}
    layouts = trace_chr_mappings(trace)
    assert layouts[-1]["modeled_ppu_chr_bank_slots"] == [92, 93, 94, 95, 126, 126, 126, 126]
    assert layouts[-1]["chr_mode_bit7"] == 0
    with pytest.raises(ValueError, match="truncated"):
        trace_chr_mappings({**trace, "dropped_writes": 1})


def test_invalid_snapshot_size():
    with pytest.raises(ValueError, match="8192"):
        inspect_pattern(bytes(8192), bytes(8191))
