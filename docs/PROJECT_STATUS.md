# SpriteMine project status

**Updated: 2026-11-12.** GitHub is authoritative. This file distinguishes code merged to main from research implemented and checked on other branches.

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
| Contiguous short timeline | [Draft PR #6](https://github.com/87otlto-coder/SpriteMine/pull/6) -> updated research base; still draft | Three real consecutive frames 448385–448387, same 16x16 Mario RGBA pose held for three frames. A complete walk/jump cycle is not yet proven |

The real graphics observations are supported by locally held source state, captures, comparison reports and hashes and are **not reproduced in public GitHub CI**. They should be preserved outside this public repository. Do not claim all sprites, all animations, hardware priority/overflow, level decoding or audio are complete.

## Repository health and CI policy

- [PR #7](https://github.com/87otlto-coder/SpriteMine/pull/7) merged 2026-11-11: storage/evidence retention guidance and removal of redundant feature/research push test triggers.
- [PR #8](https://github.com/87otlto-coder/SpriteMine/pull/8) merged 2026-11-11: Actions incident record and **Windows-only** hosted CI policy.
- Incident source was primarily accumulated browser-build artifacts in another repository (mk-dos-archive); SpriteMine main Tests currently has no artifact upload.
- Research Windows CI migration [PR #9](https://github.com/87otlto-coder/SpriteMine/pull/9) and full-Lua syntax follow-up #12 passed hosted Windows and merged into the research base. Graphics #5 and animation #6 inherited the same Windows policy (maintenance PRs #13/#14), preserving synthetic Lua/MMC3/CHR/RGB tests. GUI #4 inherited Windows-only Qt checks (maintenance PR #11) and is mergeable but remains open for remaining native UI acceptance.
- An old duplicate artifact-policy workflow run is queued even though later authoritative main runs succeeded; do not conflate the stale queue with current main CI failure.

## Next engineering decisions

1. Keep the approved Windows-only CI policy across main, GUI and research branches, with no redundant push+PR runs; already verified on hosted Windows runners.
2. Complete native PySide6 GUI acceptance in PR #4 before merging to main. Retain the A/B/A graphics harness on its now-consolidated research base and keep animation draft PR #6 separate until its next gameplay transition gate.
3. Merge the accepted static GUI and research features through reviewable PRs, recording the exact production integration contract.
4. Continue Phase 4 with a longer deterministic Mario sequence to observe a real pose transition and its held-frame durations; the verified three-frame hold is not a full animation.
5. Maintain SMB3 scope and original ROM immutability, then integrate sprite inspection, animation exports, level decoding and audio into a usable Windows application.

See README.md, docs/ROADMAP.md, docs/ACTIONS_INCIDENT_2026-11-11.md and research runbooks on their respective branches.


## PR #4 static GUI — source and partial native Windows acceptance (2026-11-12)

This feature branch implements the first PySide6 ROM and CHR viewer on top
of main's foundation. The dedicated **Windows-only** Qt offscreen smoke suite
and the Python 3.11/3.12 suites passed after GUI maintenance PR #11.

The owner previously provided native Windows screenshots confirming the
application starts, accepts the verified SMB3 US PRG1 ZIP, displays bank 0 of
the 16 CHR banks / 8,192 raw tiles, and reports tile 19 at bank 0 coordinate
(3,1), CHR offset 0x00130, absolute ROM offset 0x40140, 16-byte source
length. The image files remain private.

**Native acceptance still pending:** bank 15 selection, actual palette
switching behavior, tile/bank/all-bank exports and JSON manifests, malformed
ROM handling, zoom/resize and packaged Windows release. Qt offscreen CI
does not replace this manual UI validation.

The runtime SMB3 graphics A/B/A research under PR #5 is now merged to its
research branch; it is not integrated into this static UI. Draft PR #6
animation timeline remains separate. This document records code available
on this feature branch; do not misrepresent it as merged to main until PR #4
is reviewed and accepted.
