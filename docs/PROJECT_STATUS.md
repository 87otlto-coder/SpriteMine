# SpriteMine project status

**Owner M1 revision (2026-11-22) overrides the earlier section-GIF criteria below:** a complete **11-screen × 27-row main World 1-1** panorama (nominal **2,816×432** logical pixels), including vertical world/scroll coverage, correct art/placement and no texture defects, must precede animation. The entire level is one stationary scene (no repeated sections); Mario none or one; **enemies last**. Existing enemy object records are already documented in `W101O` research, but not in GIF code. See [full-level acceptance](creative/SMB3_WORLD11_FULL_LEVEL_M1_ACCEPTANCE.md).

**Updated: 2026-11-22 — owner-approved creative production realignment.** GitHub is authoritative. This file distinguishes merged code, unmerged evidence and actual creative outputs.

## CURRENT PRIORITY — complete 2D World 1-1 static panorama, then full-scene animated GIF

SpriteMine is now a **creative asset extraction/composition/animation/audio production kit**. The first deliverable is a **full 11-screen × 27-row main World 1-1 static panorama** correctly assembled in both world X and Y, followed by a **playable, seamlessly looping GIF** of that same world with independently animated correctly placed objects. Mario is omitted by default or appears once; enemies are last. Browse, extract/capture, compile, animate, preview and export **headlessly before UI**. See [product direction](PRODUCT_DIRECTION.md) and [new creative roadmap](ROADMAP.md). This supersedes historical research-first or UI-first orders below.

**Milestone 1 status: NOT COMPLETE.** Unmerged [PR #27](https://github.com/87otlto-coder/SpriteMine/pull/27) produced a real artist-composed 48-frame 1024×576 prototype GIF using selected ROM graphics and captures, with deterministic regeneration and hosted Windows synthetic tests, but **not the complete native stage**. The contact sheet shows time samples, not successive world positions. The exact 2,816×432 source-model panorama, authentic all-region scenery, per-row vertical coverage and full-level GIF **have not been produced or validated**.

**Then:** milestone 2 audio capture/trim/loop/export WAV (music + SFX); milestone 3 reusable asset/project catalog and additional exports; milestone 4 Windows PySide6 UI wrapping proven workflows.

**Relevant unmerged code:** [PRs #21–#25](https://github.com/87otlto-coder/SpriteMine/pull/25) include headless Mario/sprite and World 1-1 background/PPU research. On 2026-11-22 the owner reported **61 local tests passed** on PR #25's accepted implementation and the actual offline verifier returned **13 frames / 638,976 native RGB gameplay pixels / zero mismatches** for a bounded World 1-1 bonus room; prior CPU/CIRAM validation passed 104 frames. These results are genuine but narrow technical evidence, **not a rendered animated stage** and **not merged main features**. Use whichever tested modules shorten the GIF-production path; do not deepen PPU or full-level research without a specific creative blockage. [Static PySide6 PR #4](https://github.com/87otlto-coder/SpriteMine/pull/4) is also unmerged and intentionally deferred until the production pipeline is proven.

**Next engineering output:** a source-grounded **2,816×432 nominal full X/Y static main World 1-1 panorama** (no Mario/enemies) with vertical coverage, completeness and texture audits; then coherent animation and enemies last. The 15 `W101O` source entries are known from November 16 research, but have not been connected to the creative GIF composer. Review the GIF itself for composition, alpha, authentic palette, independent motion and seamless loop; save private local files under `F:\Dev\ROMMAGE\OUTPUT` and QA under `REPORTS`. Preserve original ROMs/captures under `FIXTURE`.

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

## Next engineering decisions

1. Build **complete static main World 1-1** across world X and Y, not a repeated scenic section, using existing original-ROM layout findings and legitimate captures. Identify missing tiles or RNG/cloud state explicitly.
2. Remove synthetic art and incorrect crops; validate the entire scene against emulator views at multiple camera/vertical positions, with HUD excluded.
3. Animate correctly placed scene objects, keep the world stationary, allow Mario none or one, and inspect the exported full-scene GIF.
4. **Last:** add enemies from the already-documented `W101O` source object placements and validate images/motion; do not infer simultaneous visibility from source records.
5. Preserve private ROM/capture/output custody, Windows-only CI, provenance and accepted evidence; no audio or UI before visual M1 acceptance.
See README.md, docs/ROADMAP.md, docs/ACTIONS_INCIDENT_2026-11-11.md and research runbooks on their respective branches.
