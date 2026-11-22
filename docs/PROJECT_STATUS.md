# SpriteMine project status

## Supporting utility — passive recorder (2026-11-22)

The optional standalone [MesenCE flight recorder](research/MESENCE_FLIGHT_RECORDER.md)
captures bounded NES RAM/PPU deltas, available state and optional CPU-event bursts.
Native SMB3 A/B/A and independent memory checks passed; its largest change
interval bracketed known bonus-area entry. See [validation scope](research/MESENCE_FLIGHT_RECORDER_VALIDATION.md).
This supporting proof of concept does not change the creative milestone or
claim extraction, complete tracing or automatic area recognition.

**Updated: 2026-11-22 — owner-approved creative production realignment.** GitHub is authoritative. This file distinguishes merged code, unmerged evidence and actual creative outputs.

## CURRENT PRIORITY — compiled World 1-1 animated GIF, not further reverse engineering

SpriteMine is now a **creative asset extraction/composition/animation/audio production kit**. The first deliverable is a **visually reviewed, playable, seamlessly looping GIF** of a recognizable World 1-1 section, constructed from usable SMB3 assets with independently moving elements and an editable/reproducible composition recipe. Browse, extract/capture, compile, animate, preview and export **headlessly before UI**. See [product direction](PRODUCT_DIRECTION.md) and [new creative roadmap](ROADMAP.md). This supersedes historical research-first or UI-first orders below.

**Milestone 1 status: NOT YET COMPLETE.** The repository has ROM/CHR extraction and significant accepted rendering research, but **no finished compiled animated World 1-1 stage GIF has been demonstrated or visually accepted**. Do not substitute a screenshot, frame-matched RGB test, hypothetical demo or a report for that file.

**Then:** milestone 2 audio capture/trim/loop/export WAV (music + SFX); milestone 3 reusable asset/project catalog and additional exports; milestone 4 Windows PySide6 UI wrapping proven workflows.

**Relevant unmerged code:** [PRs #21–#25](https://github.com/87otlto-coder/SpriteMine/pull/25) include headless Mario/sprite and World 1-1 background/PPU research. On 2026-11-22 the owner reported **61 local tests passed** on PR #25's accepted implementation and the actual offline verifier returned **13 frames / 638,976 native RGB gameplay pixels / zero mismatches** for a bounded World 1-1 bonus room; prior CPU/CIRAM validation passed 104 frames. These results are genuine but narrow technical evidence, **not a rendered animated stage** and **not merged main features**. Use whichever tested modules shorten the GIF-production path; do not deepen PPU or full-level research without a specific creative blockage. [Static PySide6 PR #4](https://github.com/87otlto-coder/SpriteMine/pull/4) is also unmerged and intentionally deferred until the production pipeline is proven.

**Next engineering output:** make the **first complete stage GIF** with a reproducible recipe. Review the GIF itself for composition, alpha, authentic palette, independent motion and seamless loop; save private local files under `F:\Dev\ROMMAGE\OUTPUT` and QA under `REPORTS`. Preserve original ROMs/captures under `FIXTURE`.

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

## Next engineering decisions (current, supersedes earlier research/UI-first plans)

1. Build a **headless browse → extract/capture → stage composition → animated-GIF renderer** using existing CHR and native art/frames. Create the smallest recognizable World 1-1 section with a fixed camera and two independent animated objects.
2. **Open and inspect the actual GIF.** Fix visual issues, alpha, palette and loop seam; preserve a deterministic editable composition recipe, source labels and private output hashes. Milestone 1 is not done until this is successful.
3. Start **music/SFX audio extraction** only after stage GIF acceptance; deliver playable WAV outputs and a looped music example.
4. Build reusable asset/project organization from proven creative exports; then finish native GUI acceptance/integration for PR #4 and build the Windows application.
5. Keep Windows-only CI, source immutability and copyright safeguards. Review/test and integrate only the useful portions of unmerged research PRs #21–#25. New deep ROM/PPU research requires a specific GIF/audio output blocker and a smaller alternative check.

See README.md, docs/ROADMAP.md, docs/ACTIONS_INCIDENT_2026-11-11.md and research runbooks on their respective branches.
