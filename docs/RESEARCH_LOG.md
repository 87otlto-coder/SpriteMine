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

## 2026-11-19 — Owner native bonus-room producer staging accepted (PR #23)

**Observed via owner-supplied Windows replay and verification output**, not an
independent re-execution of raw private captures for this documentation update.
After the B-only diagnostic-file signature filter correction, the previously
failed capture `pipe-replay-ih9zjv6r` had **0 genuine A/B and A/A2
differences**. Windows pytest on commit `58fe97a` passed **40/40** using
the private original SMB3 PRG1 ROM.

Fresh 2,590-poll MesenCE A/B/A replay recorded `neutral: true`, frames
**450778–450881**, and **66** detailed producer events in private capture
`F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-hb6hmzft`.
For eligible native bonus-room logical-map events, **32 × 54-byte
Scroll_PatStrip = 1,728 bytes**, plus **32 × 14-byte Scroll_AttrStrip = 448
bytes**, matched the source-modeled original ROM output. **2,176 bytes
checked, zero byte/metadata discrepancies**; two events were excluded for
non-bonus/modified map state, not promoted to passes.

**Acceptance is CPU staging only**; no hardware PPU VRAM, CHR fetch-time,
palette or visible framebuffer claim. Preserved source hashes, event log
hash, private capture location and next steps:
[2026-11-19 native staging acceptance](research/SMB3_BACKGROUND_NATIVE_STAGING_ACCEPTANCE_20261119.md).

## 2026-11-19 — Native PPU commit hook identified (source-backed, not yet captured)

Pinned MesenCE 2.2.1 NesPpu::WriteRam and UpdateState show that CPU
$2007 writes are latched and applied after a short PPU-cycle delay.
Ordinary nametable writes call mapper WriteVram without firing
ProcessPpuWrite (NesPpuMemory), so a naive PPU memory callback would
miss the very writes being validated. For palette $2007 writes,
ProcessPpuWrite is present. Actual $2007 bus trace and physical CIRAM
changes have **not yet been observed in a new native run**.

Draft PR #24 adds a passive register observer and independent offline
verification of the original 54/14-byte staging producers against CPU
$2007 data-write sequences, frame-boundary physical nametable RAM, and
mirrored PPU debugger nametable pages. Observations are bounded to the
established 2,590-poll World 1-1 upper-pipe replay. Source:
https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp;
MMC3 mirroring state:
https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h.
Synthetic CI: 43 passed / 4 private skips on Python 3.11 and 3.12 in
https://github.com/87otlto-coder/SpriteMine/actions/runs/44600719808.
**Native result: pending.** See
[PPU/CIRAM runbook](research/SMB3_NATIVE_PPU_WRITE_CIRAM.md).

## 2026-11-19 — PR #24 native PPU observer timeout isolated

Owner's first private Windows test passed **47/47 local pytest** and
reproduced the 2,590-poll input SHA-256. Discovery and A reached the final
poll; B advanced to poll **2499** / frame **450814** before returning
`4294967295`, and A2 did not start. The B trace contained 2,121 register
observations, 74 physical CIRAM boundary observations and 2 staging
events. Updated B files spanned approximately 30 seconds; searching its
emulator log found no explicit Lua or fatal error. Source examination of
MesenCE `UI/Utilities/TestRunner.cs` established `-1` is its normal
timeout return value. This is strong evidence of a 30-second instrumented
B-leg timeout, rather than altered controller gameplay.

Only B when `--ppu-commits` is requested now uses a longer, still
bounded emulator/Python timeout (180 / 210 seconds). No ROM, controller,
save-state, callback semantics, or verifier acceptance criterion changed.
A fresh native capture remains necessary; the prior partial capture is
**not** a passing native PPU verification.

## 2026-11-21 — Independently matched original-ROM producer → $2007 → CIRAM

Reviewed the owner-uploaded complete private `B.zip`, replay
`pipe-replay-xbhs6ijw`, plus the original user-supplied ROM image.
SHA-256 of the raw ROM matched PRG1 and Plains table fingerprint;
314 common evidence files in each of A, B and A2 matched. The original
Plains source model independently generated **2,176 byte-identical
pattern/attribute staging bytes** for 64 eligible producer events;
2 nonbonus logical-map events were excluded. All 64 producer uploads
matched nonoverlapping observed $2007 requests and original-ROM-derived
PPU targets. Three uploads cross a frame boundary (15, 34, 63).

Replaying the **5,491 observed nametable CPU write intentions**
reproduced all **104 captured physical 2 KiB CIRAM end-frame
snapshots** with **zero byte differences** (212,992 compared).
All 425,984 PPU debug nametable alias-byte comparisons also matched
observed MMC3 mirroring. The captured CPU PPU register trace has
10,430 records.

The original post-capture Python verifier failed only because direct
script invocation lacked the repository root on `sys.path`.
The new code fixes that and corrects its false assumptions that
hardware-valid writes must be in VBlank and that uploads cannot straddle
frame boundaries. Hosted Windows synthetic CI passed **46 tests, 4
private-fixture skips** per Python 3.11/3.12, run 44906486710.

This establishes **offline source/CPU-bus/physical-CIRAM frame-end
agreement**, not complete on-scanline PPU write timing or final
rendered graphics. Complete hashes, scope, limits and private
reproduction path in
[archive revalidation](research/SMB3_NATIVE_PPU_CIRAM_ARCHIVE_REVALIDATION_20261121.md).

### 2026-11-21 — Owner Windows native PPU/CIRAM CLI acceptance: PASS

Windows clean detached checkout `a375cd09a6aa19dd2cebce6df37cfcba8cd5ab14`
executed **51 passed, 0 failed** private-ROM pytest tests, then independently
ran the corrected `verify_ppu_commit_trace.py` against the already completed
private replay `pipe-replay-xbhs6ijw` without restarting the emulator.
The verifier returned **`passed: true`**, with:

- `pattern_matched: 32`, `attribute_matched: 32`; `matched_bytes: 2176`
- `frame_spanning_transfers: 3`; `excluded_non_bonus_map: 2`
- `nametable_writes: 5491`
- `frames_checked: 104` (`frames_with_nametable_writes: 42`)
- `bytes_checked: 212992`, `physical_mismatches: 0`
- `alias_samples: 425984`, `alias_mismatches: 0`

Private JSON evidence:
`F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-xbhs6ijw\ppu-verification-postfix.json`.
The owner provided complete console output; the private JSON file is
**not committed to GitHub**, and it was not remounted for a second code
execution during this documentation change.

**Gate accepted for the sampled World 1-1 bonus-room CPU write requests and
end-frame physical CIRAM.** This does **not** establish per-dot PPU timing,
fetch-time CHR selection, palette/RGB rendering, complete World 1-1 terrain,
other areas, or finished GUI functionality. PR #24 remains draft/unmerged.

## 2026-11-22 — Original-ROM independent visible World 1-1 bonus-background RGB

Using the private, complete `pipe-replay-xbhs6ijw` owner MesenCE A/B/A
capture and original USA PRG1 ROM, independently reconstructed
**13 consecutive frames 450869–450881** at **256×192 visible gameplay
pixels per frame** (**638,976/638,976 exact RGB pixels, zero differences**).
The first narrow result was **47,616/47,616** on frame 450880
(columns 8–255), followed by a complete gameplay viewport including
left-edge masking. This was **offline private original-ROM analysis**, not a
new MesenCE emulator run.

Source inputs: original ROM CHR, *physical* 2 KiB CIRAM start-frame
snapshots and MMC3 mirroring, register-replayed `$8000/$8001` CHR bank
mapping (8,9,96,97,0,4,34,79 for these 13 frame starts), PPU scrolling
register X=8 / Y=239 and native palette RAM. Bank assignments were
compared independently against mapped PPU debug CHR snapshots, but those
mapped snapshots were not used to draw the modeled RGB pixels. Palette
RGB conversion used a separately held pinned MesenCE 2C02 default table,
not an extracted screenshot or built-in proprietary code table.

ROM/CHR/CIRAM source modeling matched the native screen RGB exactly
under this scoped viewport; the HUD/IRQ split starts at scanline 192,
and per-dot timing/other areas were not tested. The implementation,
negative synthetic tests and private offline Windows CLI are in
[draft PR #25](https://github.com/87otlto-coder/SpriteMine/pull/25).
The committed CLI was **subsequently accepted** by the owner on Windows
PowerShell 5.1 at `a462499`: **61 passed**, then
`verify_visible_background.py` returned **`passed: true`**,
13 frames, 638,976 compared RGB pixels, **0 mismatches**.
Private report: `F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-xbhs6ijw\visible-background-verification.json`.
The capture was reused without another emulator replay. Read the
[RGB gate](research/SMB3_VISIBLE_BACKGROUND_NATIVE_GATE.md).
