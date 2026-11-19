# Research log

Record date, question, source/experiment, observation, confidence and next action. Link each major result to the exact code commit, emulator version and (where possible) test fixture.

## 2026-11-08 — Source ROM identity

Observation: the supplied SMB3 ZIP contains one valid iNES file with mapper 4, 256 KiB PRG-ROM, 128 KiB CHR-ROM and matching PRG1 hash/CRC values. Verified locally against bytes, not inferred solely from filename. Confidence: high for this supplied file.

## 2026-11-08 — Static CHR

Observation: all 16 CHR-ROM banks can be decoded to 8×8 2bpp tiles (8,192 total), exported in grayscale. No game-accurate palette identification. Confidence: high for raw 2bpp interpretation; asset identity unresolved.

## 2026-11-08 — MesenCE integration candidate

Source code contains debugger-oriented tilemap/sprite/palette access and emulator state save/load capabilities. Open question: how to expose a synchronized, reproducible capture API, with an acceptable GPLv3-compatible distribution approach. **Not yet experimentally validated.** See research branch `research/smb3-emulator-feasibility`.

## Source references

- https://www.nesdev.org/wiki/PPU_programmer_reference
- https://github.com/nesdev-org/MesenCE
- https://github.com/TASEmulators/fceux
- https://github.com/captainsouthbird/smb3 (research reference; licensing review needed before reuse)

## 2026-11-18 — Headless implementation and native player replay

Verified all six original-ROM pose fingerprints, revalidated 24 archived A/B/A windows and ran a fresh observer-neutral MesenCE replay. Runtime $EE identifies the recipes at start of frame. The new bitmap decoder reproduced 24 archived RGBA hashes and matched 4,032 native opaque RGB samples. The bonus layout matches the 864-byte model fingerprint. Native pipe and Tile_Mem evidence remain open. See [headless validation](research/SMB3_HEADLESS_VALIDATION.md).

## World 1-1 native pipe replay

Native screen-8 Tile_Mem confirms an enterable upper mouth at row 7 and blocked openings at rows 19 and 23. The captured Down attempt left pipe and junction state at zero. See [native pipe approach](research/SMB3_NATIVE_PIPE_APPROACH.md).

## 2026-11-19 — Native Raccoon pipe occlusion and bonus-room logical map

A legitimate **2,590-poll controller-only PRG1 World 1-1 replay** acquired Super Mushroom and Super Leaf, filled P-Meter, flew to the upper screen-8 pipe, triggered the pipe transition and captured the first bonus-room layout immediately after construction. A/B/A timing/controller/tile/RGB snapshots agreed for the bounded native replay. The pipe-mask compositor independently matched **7,528 distinguishable overlapping pixels / zero differences** in 56 compared frames; 644 additional overlap samples were RGB-indistinguishable and excluded. Actual mask pattern `$77` in PPU window 5 used physical CHR page `$04` (128/128 opaque pixels), correcting the older hypothetical `$53` assumption for this native route.

The source-derived bonus-room model matched **864/864** first-entry native logical Tile_Mem bytes. See [reproducible native report](research/SMB3_NATIVE_RACCOON_PIPE.md) and PR #21 at `1846557529b62dbf4276c9e2b0509721c97065db`; [Windows CI](https://github.com/87otlto-coder/SpriteMine/actions/runs/44475932602) passed on Python 3.11 and 3.12. Confidence: high for this captured native route/sample subset and logical Tile_Mem comparison, **not** complete framebuffer, arbitrary pipe routes, original IRQ bank-by-pixel history or background PPU tile/attribute reconstruction. Next: implement independently testable Plains quadrant/pattern/attribute mapping and compare against a bounded first-entry MesenCE strip/PPU capture. Public GitHub excludes original ROM and extracted graphical assets.

## 2026-11-19 — Plains background staging implementation (stacked PR #22)

The new headless ROM-backed decoder reads four Plains 256-byte quadrant tables (UL/LL/UR/LR) from immutable original PRG1 file offset `0x1E010`, SHA-256 `c19dfefb08bfdebaa2be3bce01abc590865da46f804ccd36f4b9d96db1bf9362`. Source-derived pattern strips are 54 bytes (first 30 PPU $20xx, then 24 $28xx); 14 attributes group adjacent logical columns with a row14/15 special upper-nibble-only entry, then restart at row15 for the second nametable. Optional private 54/14-byte dump comparator and explicit mapped-CHR indexed tile decoder do not synthesize undocumented runtime states. Independently recomputed first-entry bonus source-model digests are recorded in [SMB3_HEADLESS_BACKGROUND_STAGE.md](research/SMB3_HEADLESS_BACKGROUND_STAGE.md). No copyrighted graphical data was committed.

Synthetic Windows CI on PR #22 [run 44479250342](https://github.com/87otlto-coder/SpriteMine/actions/runs/44479250342) passed on Python 3.11 and 3.12; the private-ROM pytest on owner's F: drive and native MesenCE producer/PPU capture were **not run** in this increment. Confidence: exact original ROM table hash and independent source-model strip hash calculation, not observed PPU output. Next acceptance: instrument `Scroll_DoColumn` and `Scroll_Do_AttrColumn` producer completion with grounded PRG bank, compare true `$0382-$03B7` and `$03BA-$03C7` captures, then trace NMI commits and fetch-time mapped CHR/palette.


## 2026-11-19 — Owner static suite passed; passive native producer observation prepared

The owner executed PR #22 in a clean dedicated Windows worktree and verified
the imported package path pointed to that checkout. The private original-ROM
background tests were 7/7; the complete Python suite was **33/33**, no skips.
The source-model fingerprints matched accepted PRG1 data. This is local static
regression evidence and not a new MesenCE measurement.

Source review for the next native increment confirmed the attribute producer
may select a nonadjacent logical column depending on parity and
Scroll_LastDir. A new source-derived ordered-column helper, passive
producer-completion Lua hook and independent private staging verifier are
preserved on `feature/smb3-world11-staging-capture`. No actual staging
capture has been reported yet. The new acceptance gate and exact Windows
commands are in [native staging guide](research/SMB3_BACKGROUND_NATIVE_STAGING.md).
