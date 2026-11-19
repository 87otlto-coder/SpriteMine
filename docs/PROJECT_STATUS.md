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

## Headless SMB3 PRG1 implementation (PR #21; draft, unmerged)

**Acceptance as of 2026-11-19:** Gate A passed for the three canonical Small Mario ROM recipes (138/174/194 opaque pixels; all six indexed/alpha SHA-256 fingerprints), and Gate B passed for 24 captured frames 448385–448408 under fresh A/B/A observations. Gate C passed for **7,528 distinguishable native pipe-mask overlap pixels, zero mismatch, across 56 frames**; 644 additional overlaps were ambiguous under RGB comparisons and excluded, so this is **not** whole-frame sprite validation. Gate D passed for **864/864 first-entry bonus-room logical Tile_Mem bytes**, SHA-256 `c57b72c77899d596745065c90878327993f9a25e6289c0b22d960c58021b088a`; background quadrant→pattern, palette attribute and final rendered-pixel validation are **not yet established**.

The original PRG1 controller-only route acquires Mushroom and Leaf, fills P-Meter, flies to the elevated World 1-1 screen-8 pipe, and enters the bonus room. On that route OAM pipe masks use actual 1-KiB CHR page `$04` in PPU window 5 and are 128/128 opaque; the older 88/128 figure is conditional on *hypothetically* mapping page `$53` to window 5. The 2,590 controller poll bytes, savestate/ROM/emulator provenance, bounded replay frames, verified comparisons and limits appear in [native Raccoon pipe report](research/SMB3_NATIVE_RACCOON_PIPE.md). Earlier blocked approach is preserved in [native pipe approach](research/SMB3_NATIVE_PIPE_APPROACH.md).

**CI:** current PR #21 commit `1846557529b62dbf4276c9e2b0509721c97065db` passed Windows Python 3.11 and 3.12 in [workflow 44475932602](https://github.com/87otlto-coder/SpriteMine/actions/runs/44475932602). Private native comparisons were executed and documented by the Windows worker, not reproducible in public CI. PR #21 remains draft and unmerged. The next feature branch should deliver testable background expansion and capture-time PPU comparison without altering the accepted replay route.
