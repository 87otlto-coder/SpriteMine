# SpriteMine project status

**Updated: 2026-11-19.** GitHub is authoritative. This file distinguishes code merged to main from research implemented and checked on other branches.

## Merged baseline — main

**Phase 0 foundation: implemented, tested and merged via PR #1 (2026-11-09).**

- Read-only iNES 1.0 .nes and single-ROM ZIP parsing, mapper and PRG/CHR checks.
- ROM SHA-256, PRG/CHR offsets, deterministic manifests, raw 2bpp 8x8 tiles and 8 KiB CHR bank exports.
- Synthetic Python tests and an opt-in user-local SMB3 PRG1 ROM integration test.
- GitHub Actions main Tests workflow is Windows-only (Python 3.11/3.12), most recently passing in run 43105552063. No copyrighted game data is present.

Verified private ROM ZIP SHA-256: 4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579. Mapper 4, 256 KiB PRG / 128 KiB CHR, 16 CHR banks / 8,192 raw tiles. Raw tiles do not automatically identify game actors.

**Not on main yet:** desktop browser, live emulator adapter, character/sprite inspector, animation workspace, reconstructed level or audio catalog.

## Unmerged code and independently reported evidence

| Work | Where it lives | Evidence and remaining limit |
|---|---|---|
| Static CHR explorer | [PR #4](https://github.com/87otlto-coder/SpriteMine/pull/4) -> main | PySide6 ROM/CHR bank/tile browser and export; native UI validation is not fully recorded in the PR |
| Emulator capture feasibility | research/smb3-emulator-feasibility (research base) | Real PRG1 CHR/OAM/palette/MMC3 phase probes, RGB reference tests; no stable production adapter |
| Three-pose A/B/A graphics proof | [PR #5](https://github.com/87otlto-coder/SpriteMine/pull/5) merged into research/smb3-emulator-feasibility, **not main** | On owner's Windows MesenCE slot 1: standing 138+118, walking-right 138+118, rising-jump 194+62 out of 256 pixels per pose; repeated enabled RGB and CPU input verification |
| Contiguous short timeline | [PR #6](https://github.com/87otlto-coder/SpriteMine/pull/6), merged into research/smb3-emulator-feasibility (not main) | Three real consecutive frames 448385–448387, same 16x16 Mario RGBA pose held for three frames. A complete walk/jump cycle is not yet proven |

The real graphics observations are supported by locally held source state, captures, comparison reports and hashes and are **not reproduced in public GitHub CI**. They should be preserved outside this public repository. Do not claim all sprites, all animations, hardware priority/overflow, level decoding or audio are complete.

## Repository health and CI policy

- [PR #7](https://github.com/87otlto-coder/SpriteMine/pull/7) merged 2026-11-11: storage/evidence retention guidance and removal of redundant feature/research push test triggers.
- [PR #8](https://github.com/87otlto-coder/SpriteMine/pull/8) merged 2026-11-11: Actions incident record and **Windows-only** hosted CI policy.
- Incident source was primarily accumulated browser-build artifacts in another repository (mk-dos-archive); SpriteMine main Tests currently has no artifact upload.
- Research Windows CI migration [PR #9](https://github.com/87otlto-coder/SpriteMine/pull/9) and full-Lua syntax follow-up #12 passed hosted Windows and merged into the research base. Graphics #5 and animation #6 inherited the same Windows policy (maintenance PRs #13/#14), preserving synthetic Lua/MMC3/CHR/RGB tests. GUI #4 inherited Windows-only Qt checks (maintenance PR #11) and is mergeable but remains open for remaining native UI acceptance.
- An old duplicate artifact-policy workflow run is queued even though later authoritative main runs succeeded; do not conflate the stale queue with current main CI failure.

## Current headless engineering decisions (2026-11-19)

1. Keep development **headless** until the underlying SMB3 decoder and original-emulator validation gates have defensible, reproducible results. The earlier 2026-11-12 UI-first/three-frame worklist is superseded by these results; historical details remain in older research branches.
2. PR #21 (draft, unmerged) is now the reviewable source of the 81 player recipes, three canonical poses, 24-frame native A/B/A decoder, authentic upper-pipe occlusion subset and native bonus-room **logical tile** acceptance. Do not treat these as merged main features.
3. Continue with World 1-1 bonus **logical tile to PPU patterns, attributes, palette and scanline CHR mapping**, each independently compared with MesenCE. Extend to the stochastic main level only after the deterministic bonus area is validated through pixel rendering.
4. PR #19 and #20 are separate long-running research histories with substantial divergence from current main. Review/cherry-pick relevant tested functionality rather than merging either branch indiscriminately. No Qt GUI work in this headless milestone.
5. Preserve immutable source ROMs and private native captures under F:\\Dev\\ROMMAGE\\FIXTURE; keep Windows-only synthetic CI and distinguish private Windows acceptance from hosted tests.

## Headless World 1-1 background staging (stacked draft PR #22, 2026-11-19)

**Unmerged and headless.** New `spritemine.background` parses the verified PRG1 Plains tile-layout table (four 256-entry UL/LL/UR/LR quadrants), constructs a deterministic **54-byte** per-half vertical pattern strip and **14-byte** per-pair attribute strip with the row-14/15 boundary rule, models vertical PPU write targets and MMC3 CIRAM aliases, and decodes selected 16×16 indexed background pixels from **explicit fetch-time CHR-page vectors**. New `reconstruct-background`/ `validate-background` CLI operations report source-modeled fingerprints and compare optional private MesenCE 54/14-byte dumps. The model consumes the PR #21 **native-validated logical** bonus-room Tile_Mem output; it does **not** claim native PPU or final RGB matching.

The private original ROM ZIP was independently inspected read-only in this session, confirming the Plains 1,024-byte table SHA-256 `c19dfefb08bfdebaa2be3bce01abc590865da46f804ccd36f4b9d96db1bf9362`, the 864-byte logical map fingerprint, and three modeled column pattern/attribute digest pairs. Synthetic Windows CI on PR #22 passed on Python 3.11/3.12 at [run 44479250342](https://github.com/87otlto-coder/SpriteMine/actions/runs/44479250342). **Private ROM pytest was not run through Windows in this increment; native MesenCE staging, PPU/scanline bank timing, screenshot and indexed-background comparisons remain open.** See [implementation and next gate](research/SMB3_HEADLESS_BACKGROUND_STAGE.md). PR #22 targets PR #21 (not `main`) to preserve a readable stacked diff.

## Headless SMB3 PRG1 implementation (PR #21; draft, unmerged)

**Acceptance as of 2026-11-19:** Gate A passed for the three canonical Small Mario ROM recipes (138/174/194 opaque pixels; all six indexed/alpha SHA-256 fingerprints), and Gate B passed for 24 captured frames 448385–448408 under fresh A/B/A observations. Gate C passed for **7,528 distinguishable native pipe-mask overlap pixels, zero mismatch, across 56 frames**; 644 additional overlaps were ambiguous under RGB comparisons and excluded, so this is **not** whole-frame sprite validation. Gate D passed for **864/864 first-entry bonus-room logical Tile_Mem bytes**, SHA-256 `c57b72c77899d596745065c90878327993f9a25e6289c0b22d960c58021b088a`; background quadrant→pattern, palette attribute and final rendered-pixel validation are **not yet established**.

The original PRG1 controller-only route acquires Mushroom and Leaf, fills P-Meter, flies to the elevated World 1-1 screen-8 pipe, and enters the bonus room. On that route OAM pipe masks use actual 1-KiB CHR page `$04` in PPU window 5 and are 128/128 opaque; the older 88/128 figure is conditional on *hypothetically* mapping page `$53` to window 5. The 2,590 controller poll bytes, savestate/ROM/emulator provenance, bounded replay frames, verified comparisons and limits appear in [native Raccoon pipe report](research/SMB3_NATIVE_RACCOON_PIPE.md). Earlier blocked approach is preserved in [native pipe approach](research/SMB3_NATIVE_PIPE_APPROACH.md).

**CI:** current PR #21 commit `1846557529b62dbf4276c9e2b0509721c97065db` passed Windows Python 3.11 and 3.12 in [workflow 44475932602](https://github.com/87otlto-coder/SpriteMine/actions/runs/44475932602). Private native comparisons were executed and documented by the Windows worker, not reproducible in public CI. PR #21 remains draft and unmerged. The next feature branch should deliver testable background expansion and capture-time PPU comparison without altering the accepted replay route.


## Native Plains staging observer — accepted subset (2026-11-19)

**PASS for first-entry World 1-1 bonus-room CPU pattern/attribute staging.**
The owner's clean Windows `SpriteMine-Background-Validation` worktree at
`58fe97aca8f7a99771e98dc0e2bbc53acc71c033` ran the complete
private-ROM pytest suite: **40 passed, 0 failed, 0 skipped**. The corrected
comparator also rechecked the original failed private run:
**B: 0 genuine differences; A2: 0 genuine differences**.

A fresh 2,590-input-poll MesenCE replay at frames **450778–450881**
reported `neutral: true`. Its read-only B-leg observer recorded **66**
Plains producer events, of which **32 pattern strips × 54 bytes (1,728)**
and **32 attribute strips × 14 bytes (448)** used the matching native
first-entry bonus logical map. The resulting **2,176/2,176 CPU staging bytes
matched**, with **zero byte mismatches and zero destination metadata
mismatches**. **Two events were excluded**, not counted as matches, because
their map state was not the accepted bonus layout.

Source fingerprints, event-log hash, private `F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-hb6hmzft`
location, correction history and scope are documented in
[native staging acceptance](research/SMB3_BACKGROUND_NATIVE_STAGING_ACCEPTANCE_20261119.md).
These are **owner-observed Windows test results recorded from shell output**;
the binary capture was not independently rerun for this documentation update.
PR #23 is still **draft and unmerged**, stacked on PR #22/21.

**Next:** verify PPU writes and CIRAM mapping, fetch-time MMC3 CHR pages and
palette state, and ultimately compare actual background pixels. CPU staging
acceptance does **not** establish full visible World 1-1 reconstruction.

## World 1-1 bonus PPU register and physical CIRAM gate — draft PR #24 (2026-11-19)

PR #24 is stacked on draft PR #23 and **has not passed native validation**.
The previous owner-observed CPU staging acceptance remains **2,176/2,176 bytes
matched**; this result is preserved separately and is NOT a claim of PPU
nametable or pixel equality.

The next headless increment instruments the pinned MesenCE CPU $2000/$2005/
$2006/$2007 PPU register write path, records prewrite PPU address and MMC3
mirroring state, and captures physical 2 KiB CIRAM at bounded start/end
frames. Its independent verifier correlates 54-byte/14-byte first-entry
producers with real $2007 writes, tests nametable changes under actual
mirroring, and compares the complete 4 KiB PPU debug nametable view to physical
CIRAM aliases.

Critical source correction: ordinary nametable writes do NOT invoke the
MesenCE NesPpuMemory ProcessPpuWrite Lua callback; that notification is present
on the palette path. PR #24 therefore uses CPU register callbacks and
post-write physical RAM, and handles the $2007 delayed-write semantics
conservatively. Synthetic hosted Windows CI passed on Python 3.11/3.12
(**43 passed, 4 private-fixture skips** per version) at
https://github.com/87otlto-coder/SpriteMine/actions/runs/44600719808.
The private Windows PPU observer and verifier are **not yet run**. See
[PPU/CIRAM runbook](research/SMB3_NATIVE_PPU_WRITE_CIRAM.md).

### PPU native B-leg timeout diagnosis — 2026-11-19

The first private Windows PR #24 native capture **did not complete**:
discovery/A reached 2,590/2,590 input polls, but heavily instrumented B
stopped at poll **2,499**, frame **450814**, after approximately 30 seconds.
The trace had 2,121 PPU register observations and 74 physical CIRAM
boundary records; no runtime error text was found in the searched log.
Pinned MesenCE TestRunner.cs returns `-1` on its 30-second timeout,
matching the observed unsigned Windows exit code `4294967295`.
The root cause is therefore strongly consistent with B's execution limit.
A2 never began, so **PPU native acceptance remains pending**.

A bounded fix extends only B's instrumented Mesen timeout to 180 seconds
and Python watchdog to 210 seconds; discovery/A/A2 and older CPU-staging
behavior retain their previous limits. The new regression test ensures
only B receives the extension. Private evidence remains under
`F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-c62ca5ca`;
see [PPU native runbook](research/SMB3_NATIVE_PPU_WRITE_CIRAM.md).

### Original-ROM native PPU archive revalidation — 2026-11-21

The owner provided a complete private `B.zip` from the previously
successful 2,590-poll, frames 450778–450881, World 1-1 bonus-room A/B/A
replay. Independent offline analysis of this ZIP and the user-supplied
original USA PRG1 ROM establishes **314/314 matching common evidence
hashes per A/B/A leg**, **32 source-modeled pattern + 32 attribute CPU
producer strips (2,176/2,176 original-ROM-derived bytes)**, and **64/64
corresponding nonoverlapping CPU $2007 upload sequences with exact
addresses, values and increment modes**. Three uploads genuinely span
frame boundaries (events 15, 34, 63).

Applying **5,491** logged nametable write requests under the observed
MMC3 mapping reproduced **104/104 physical 2 KiB CIRAM end-frame
snapshots, 212,992/212,992 byte comparisons**, with **0 differences**.
The 4 KiB PPU debug nametable view agreed with CIRAM mirroring for
**425,984/425,984 bytes** across the same 104 frames.

The independent reanalysis is detailed in
[2026-11-21 PPU/CIRAM archive evidence](research/SMB3_NATIVE_PPU_CIRAM_ARCHIVE_REVALIDATION_20261121.md).
The **raw ZIP, ROM and buffers stay private**. These are original owner
MesenCE observations rechecked offline, not another emulator replay.
The corrected formal standalone verifier still requires an actual
post-fix invocation against the existing F: capture. PR #24 remains
**draft/unmerged**. Individual PPU-cycle write timing, per-write
rendering-mask state, CHR fetch mapping and final RGB pixels are
**not** established.

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
