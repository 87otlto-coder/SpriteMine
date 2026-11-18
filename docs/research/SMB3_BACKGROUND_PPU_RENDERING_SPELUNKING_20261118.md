# SMB3 PRG1 — Expedition 13: logical tiles, PPU columns, CHR bank animation and the status-bar split

Date: 2026-11-18. Target: **Super Mario Bros. 3 (USA) PRG1 / Revision A**, World 1-1 first. This is an original interpretation of read-only source code, not a game asset.

## Evidence and authority

- **Source-derived:** Southbird disassembly at pinned commit [`09b1bd81a788de8ceec664a34094e84ddb463117`](https://github.com/captainsouthbird/smb3/tree/09b1bd81a788de8ceec664a34094e84ddb463117), especially [PRG030](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm), [PRG026](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm), [PRG031](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm), [Plains tile layout PRG015](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg015.asm).
- **Independently cross-checked emulator implementation:** [MesenCE 2.2.1 `MMC3.h`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h#L84-L141) pinned commit `20ba206cef5ba207c21203176d02cb9f43dda9fb`, and [NESdev MMC3](https://www.nesdev.org/wiki/MMC3) / [Programming MMC3](https://www.nesdev.org/wiki/Programming_MMC3) hardware documentation.
- **Not performed this expedition:** re-reading the private PRG1 ROM, native Windows MesenCE capture, real PPU memory trace, actual PNG/pixel comparison, A/B/A, or running SpriteMine tests. Earlier original-ROM fingerprints and the candidate 864-byte World 1-1 secret-room logical map are documented in [Expedition 12](SMB3_WORLD1_1_BONUS_AND_RANDOM_CLOUDS_20261117.md). Those earlier checks are **not** newly reproduced here. No copyrighted ROM data or game assets enter this repository.

## Findings 113–130

### 113 — One 16×16 logical tile expands to four ordered 8×8 pattern references

[Plains `Tile_Layout_TS1`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg015.asm#L8-L85) contains four independent 256-entry quadrants, in **upper-left, lower-left, upper-right, lower-right** order (source's layout schematic `02 / 13`). [`Scroll_DoColumn`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L5120-L5247) selects the left (`0,1`) or right (`2,3`) pair based on the 8-pixel offset. SpriteMine must not confuse those quadrant references with a single 16×16 pixel tile or assume a conventional row-major quadrant table.

### 114 — The horizontal scroller reads 27 logical rows per candidate column

In `Scroll_DoColumn`, a counter initialized to 26 is decremented through zero, generating **27 logical 16×16 tiles**. It writes **two 8×8 pattern indices per logical row** into `Scroll_PatStrip`, exactly **54 bytes** ($0382–$03B7), corresponding to a 432-pixel-high logical column footprint. This is a *prepared strip across a multi-nametable staging surface*, not a claim that 432 vertical pixels are all visible at once.

### 115 — Horizontal scroll PPU writes split 54 pattern bytes as 30+24

[`Scroll_Commit_Column`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L3341-L3410) uses PPU increment-by-32 (vertical), writes the **first 30 bytes** into a column rooted at `$20xx`, and the **remaining 24 bytes** into a column rooted at `$28xx`. It then clears `Scroll_ToVRAMHi`. The split corresponds to 30 8×8 nametable tile rows in the first PPU page and 24 in the second. Reproducing only a single 32×30 nametable would discard 24 prepared rows.

### 116 — Verified interpretation of MMC3 `$A000` *mirroring* versus *arrangement*

An ambiguity arises from Southbird's [`smb3.asm` register comments](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm#L314-L318), which label `$A000` bit 0 as '0 horizontal / 1 vertical mirroring'. MesenCE's [`UpdateMirroring`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h#L84-L89) explicitly sets **bit 0 = 0 to conventional vertical mirroring** and **bit 0 = 1 to conventional horizontal mirroring**. The NESdev MMC3 documentation uses 'horizontal/vertical *arrangement*' for its physical A10/A11 selection, which can appear reversed versus conventional mirroring terminology. Therefore prefer the **actual nametable alias map** over prose labels:

| `$A000 & 1` | Physical 2-KiB CIRAM nametable arrangement (top row / bottom row) | Conventional mirroring |
| --- | --- | --- |
| `0` | `A B / A B` | vertical |
| `1` | `A A / B B` | horizontal |

The standard horizontal gameplay path in [PRG030](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L1638-L1666) writes `$01` to `$A000`, so the source's `$2000` and `$2800` pattern-column targets map to **distinct physical nametable RAM**. Its vertical-level path writes `$00`. This is **hardware/emulator code verified**, not experimentally observed in this PRG1 run. It resolves a dangerous potential implementation error without depending on inconsistent terminology.

### 117 — MMC3 `$8000` bit 6 is PRG mode, bit 7 is CHR inversion

[`PT2_Full_CHRROM_Switch`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm#L3452-L3465) writes command values `$40..$45` to `$8000`, then the six selectors in `PatTable_BankSel` to `$8001`. [MesenCE MMC3 `UpdateState`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h#L136-L141) confirms `$40` sets **PRG mode 1**, *not* CHR inversion: CHR mode depends on bit `$80`, which remains zero in these commands. In CHR mode 0, R0/R1 are the 2-KiB pages at PPU `$0000-$0FFF`, and R2..R5 the four 1-KiB pages at `$1000-$1FFF`. This is an important distinction for PPU → CHR-ROM offset reconstruction.

### 118 — Palette attributes come from the logical tile ID, not from CHR pattern indices

[`Scroll_Do_AttrColumn`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L5259-L5359) masks each logical tile ID with `$C0`, generating 2-bit palette-group selectors 0..3. The resulting `Scroll_ColorStrip` holds **54 bytes**, two neighboring logical tile columns of 27 rows each. This explains how tiles with different logical IDs and identical 8×8 graphic references can draw in different colors. The level header's background palette select chooses the actual set of color values later; neither high tile bits nor the CHR bytes are direct RGB.

### 119 — Four logical palette groups are packed into one PPU attribute byte

The `Scroll_Do_AttrColumn` shift/OR sequence packs the palette group for **top-left into bits 0–1, top-right into 2–3, bottom-left into 4–5, bottom-right into 6–7**. It produces **14 attribute bytes per updated strip** in `Scroll_AttrStrip` ($03BA–$03C7), with a special `AND #$0F` when producing entry index 7 (the split boundary). A naïve two-column palette renderer must reproduce the game's neighbor-column selection, alignment, and split handling, not just tileID `>>6`.

### 120 — Scrolled pattern and attribute updates are distinct queued PPU operations

`Scroll_DoColumn` sets `Scroll_ToVRAMHi = $20`; `Scroll_Do_AttrColumn` sets `Scroll_ToVRAMHA = $23` and `Scroll_LastAttr`. [`Scroll_Commit_Column`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L3341-L3447) selects pattern *or* attribute processing based on the outstanding flag and clears the flag it consumed. The routine is invoked in both full-screen dirty updates and NMI paths, but a single invocation is not equivalent to applying the entire game logical map to PPU VRAM.

### 121 — Full dirty redraw is exactly 32 column-render passes for a horizontal scene

[`Scroll_Dirty_Update`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L4899-L4950) decrements `Scroll_Cols2Upd`, initially set to 32 in level setup. Each pass computes an 8-pixel pattern column and, as applicable, the associated attribute data, then commits them before advancing. Thus the 256-pixel-wide viewport is populated incrementally even at initial load. This is **source-derived setup behavior**, not measured first-display frame latency.

### 122 — Normal gameplay scrolling has asymmetric 8-pixel update thresholds

[`Scroll_Update`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L5034-L5105) compares the 8-pixel-aligned horizontal scroll position to the last updated position, and in a fresh update cycle applies different low-three-bit thresholds for each direction: `>=2` for rightward and `<5` for leftward movement. This is evidence that the game renders ahead of the visible scroll instead of simply committing whenever the camera moves one pixel; the full scheduler, scroll direction state, and exact native timing remain unverified.

### 123 — World 1-1 uses **two 2-KiB background CHR-ROM windows** with distinct provenance

In normal Plains gameplay, [`Level_BG_Pages1/2`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L4079-L4129) initializes `PatTable_BankSel[0] = $08` and `[1] = $60` (unless P-Switch overrides the second). [MesenCE MMC3 `UpdateChrMapping`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h#L91-L114) explicitly maps each of these register values as **two adjacent 1-KiB CHR pages**. For CHR mode 0, with 16 bytes per NES 8×8 2-bpp tile, an 8-bit pattern index 0..127 uses physical CHR window `R0`; indices 128..255 use `R1`, after subtracting 128 within that 2-KiB window. A pattern **index** does not itself identify a unique physical ROM tile without the bank at the time of PPU fetch.

### 124 — Regular gameplay animation swaps the entire second background 2-KiB window

[`PT2_Anim`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L2297-L2311) contains `$60,$62,$64,$66`. The Level_MainLoop's regular-level branch indexes it with `(Counter_1 & $18) >> 3`, nominally changing page every **eight counter increments**, repeating every 32. Hence PPU pattern IDs in the second 2-KiB half can display different underlying CHR-ROM pixels without any logical tile RAM or nametable change. **Eight increments are not independently established as eight displayed frames during every pause/transition state.** The first Plains window remains `$08` through this normal animation branch.

### 125 — P-Switch changes more than the collision overlay

When `Level_PSwitchCnt` is active, both level setup and the Plains regular animation branch force second background CHR page `$3E` instead of the rotating `$60/$62/$64/$66`. Earlier [Expedition 11](SMB3_BLOCK_INTERACTION_SPELUNKING_20261117.md) also traced virtual tile substitutions in collision queries. Accordingly the effective logical collision tile, stored tile RAM, nametable pattern indices, and the **physical graphics bank** must be captured as separate state. A pre-switch static CHR screenshot can never establish the P-Switch appearance.

### 126 — The HUD is an in-frame **CHR-bank and scroll-context transition**

The normal [NMI setup](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm#L1570-L1603) loads MMC3 IRQ latch `192` for the subsequent status-bar split. The [standard IRQ handler](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm#L2176-L2305) changes PPU address/scroll and remaps both background banks for the status-bar area. `192` is the **programmed counter**, not a measured exact output scanline or cycle for PRG1/MesenCE; no runtime IRQ trace was performed.

### 127 — HUD bank IDs differ radically from World 1-1 gameplay banks

The standard [IRQ mapping constants](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm#L1953-L1969) select **background R0=$5C and R1=$5E** for the HUD, compared with **gameplay R0=$08 and R1=$60/$62/$64/$66** for the Plains main/bonus areas. The same PPU pattern index can therefore refer to a completely different physical CHR tile above and below the split.

### 128 — SMB3 suppresses sprites over the status bar using blank CHR banks, not only OAM

The standard IRQ routine sets MMC3 1-KiB sprite registers R2..R5 to `$7E`, identified in source as the blank-graphics bank. This does **not** delete OAM entries or prove which individual sprite OAM records would otherwise overlap the HUD. It demonstrates a *hardware mapping-based visual suppression mechanism*. A SpriteMine sprite extractor must distinguish OAM-presence from visible pixels, particularly when comparing a late-scanline or end-of-frame sprite capture.

### 129 — One end-of-frame mapper snapshot cannot reconstruct all gameplay pixels

`PT2_Full_CHRROM_Switch` in the NMI writes six `PatTable_BankSel` pages for gameplay; the later IRQ can overwrite them with HUD/blank pages **within the same frame**. Thus an emulator dump taken after the HUD IRQ may accurately describe the then-current physical mapper registers yet **not describe the banks used earlier to display Mario and the level**. This is a critical, testable failure mode: source-derived plus MesenCE mapper semantics, **not yet demonstrated on a specific screenshot**. Capture bank state *at the relevant scanline or fetch*, or combine an immutable frame/cycle-specific PRG trace with the visible framebuffer.

### 130 — Tile-specific PPU edits are a third rendering path and can race other updates

[`TileChng_VRAMCommit`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L3520-L3557) writes a 2×2 group of 8×8 nametable pattern indices: two bytes at the base VRAM address, two at base+32, and clears its single pending high-address flag. It runs alongside `Scroll_Commit_Column` and `Video_Misc_Updates` under the normal NMI update path. Therefore **logical tile changes**, **scroll reconstruction**, **tile-change overlay updates** and **actual PPU-visible nametable content** are not interchangeable. Unverified: whether a particular game event can overwrite a pending edit or produce an observable late/partial frame; use native timestamps rather than inferring a glitch.

## Prioritized verification — minimal, reproducible

1. **Mirroring truth-table gate:** On MesenCE 2.2.1 with immutable PRG1, record writes to MMC3 `$A000`, actual physical PPU nametable aliases at `$2000/$2400/$2800/$2C00`, and `Level_7Vertical`. Do **not** assume disassembly comment labels match Mesen's mirroring terminology.
2. **CHR-bank split gate:** In World 1-1 and its bonus room, record MMC3 register R0/R1 and R2–R5 mapping **before vs after the HUD IRQ** in the same frame; correlate with PPU fetch scanline and screenshot. Confirm anticipated game `$08,$60/$62/$64/$66` versus HUD `$5C,$5E` plus sprite `$7E` on the standard path, rather than inferring from a one-shot RAM dump.
3. **Animation and P-Switch gate:** Record `Counter_1`, `Level_PSwitchCnt`, `PatTable_BankSel[0..1]`, physical MMC3 registers, and fixed-scanline CHR patterns across 32 consecutive full-play frames and switch activation/expiry. Explicitly account for pause/transition and NMI timing.
4. **World 1-1 bonus pattern/attribute gate:** Use the **864-byte candidate logical tile map**, but recompute the exact 54-byte pattern strip and 14-byte attribute strip for sample columns. Compare with `Scroll_PatStrip`, `Scroll_ColorStrip`, `Scroll_AttrStrip`, then with physical PPU VRAM and the screenshot **independently**. Do not promote the existing candidate map hash as a verified source/game RAM hash.
5. **PPU staging gate:** Monitor pending scroll pattern/attribute flags and 2×2 tile-change flags at gameplay update and NMI commit boundaries. Correlate source action PC, logical RAM mutation, NMI PPU writes and pixels.

Record original ROM identity/hash, MesenCE binary hash, save-state hash, exact inputs, frame/scanline/cycle, PRG bank PC, SRAM snapshot, PPU nametables and attribute RAM, CHR physical bank mapping, palette RAM, and screenshot hash. Store copyrighted fixtures under `F:\Dev\ROMMAGE\FIXTURE\SMB3` only.

## Architecture takeaway

The background decoder must be a **time-indexed, provenance-preserving rendering pipeline**:
`original construction record → logical 16×16 Tile_Mem ID → four 8×8 pattern references → 2-bit logical palette quadrant → staged scroll/tile update → current physical PPU nametable/attribute → active MMC3 CHR bank at scanline → 2-bpp pixel and palette → framebuffer`.

Never certify a background frame from a raw Tile_Mem dump and a single post-frame CHR bank vector. Distinguish static original-ROM interpretation, source-backed emulator predictions, and experimentally verified actual PRG1 pixels.
