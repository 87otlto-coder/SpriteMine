# SpriteMine project status

**M1 OWNER-ACCEPTED — 2026-11-23.** The project owner has accepted the working creative-production milestone: a 2,816×432 stationary World 1-1 panorama and 144-frame / 5.76-second looping export, with 51 background animation tracks, the original goal roulette, three Piranha Plants and 11 other enemy actors (66 tracks total). Rebuilds and GIF-to-PNG frame equivalence were verified privately; Windows CI on merged PRs #28, #29 and #31–#34 passed. **This is creative acceptance, not exhaustive native pixel verification.** Randomized clouds, certain renderer approximations, native-per-region validation and exact enemy behavior remain optional fidelity improvements. Historical sections below reflect progress at their original dates and may say "not accepted"; this current owner decision supersedes that status. **Next active milestone: M2 SMB3 audio capture/preview/trim/loop/export.**

**Current verified branch status (2026-11-23):** PRs #29 (compositor), #31 (World 1-1 source compiler) and #32 (ROM-derived roulette) have been merged into `main` with successful Windows checks. Full-width 2,816×432 original-source GIF export is working and was tested on the user's private ROM; **M1 remains unaccepted** due to unresolved random clouds, broad native validation and enemy animation. [Full M1 acceptance](creative/SMB3_WORLD11_FULL_LEVEL_M1_ACCEPTANCE.md) defines the goal; PR #27 remains only an older bounded prototype. Prior sections below chronicle development and may refer to those PRs as draft.

**Updated: 2026-11-22 — owner-approved creative production realignment.** GitHub is authoritative. This file distinguishes merged code, unmerged evidence and actual creative outputs.

## CURRENT PRIORITY — M2 original SMB3 music and sound-effect capture/export

SpriteMine is now a **creative asset extraction/composition/animation/audio production kit**. The first deliverable is an **owner-accepted, full 176×27-cell two-dimensional World 1-1 panorama and independently animated GIF**, constructed from usable SMB3 assets with independently moving elements and an editable/reproducible composition recipe. Browse, extract/capture, compile, animate, preview and export **headlessly before UI**. See [product direction](PRODUCT_DIRECTION.md) and [new creative roadmap](ROADMAP.md). This supersedes historical research-first or UI-first orders below.

**Milestone 1 status: COMPLETE BY OWNER ACCEPTANCE (2026-11-23).** The first full-width ROM-derived scene was extended to include all documented World 1-1 enemies and its original roulette; the final private export has 144 temporal frames. Some parts remain creatively approximated and full native equivalence is not claimed.

**Then:** milestone 2 audio capture/trim/loop/export WAV (music + SFX); milestone 3 reusable asset/project catalog and additional exports; milestone 4 Windows PySide6 UI wrapping proven workflows.

**Relevant unmerged code:** [PRs #21–#25](https://github.com/87otlto-coder/SpriteMine/pull/25) include headless Mario/sprite and World 1-1 background/PPU research. On 2026-11-22 the owner reported **61 local tests passed** on PR #25's accepted implementation and the actual offline verifier returned **13 frames / 638,976 native RGB gameplay pixels / zero mismatches** for a bounded World 1-1 bonus room; prior CPU/CIRAM validation passed 104 frames. These results are genuine but narrow technical evidence, **not a rendered animated stage** and **not merged main features**. Use whichever tested modules shorten the GIF-production path; do not deepen PPU or full-level research without a specific creative blockage. [Static PySide6 PR #4](https://github.com/87otlto-coder/SpriteMine/pull/4) is also unmerged and intentionally deferred until the production pipeline is proven.

**Next engineering output:** extend the existing full-stage GIF with real source-derived enemy motion, beginning with Piranha Plants, and run broad-scene visual QA. Review the GIF itself for composition, alpha, authentic palette, independent motion and seamless loop; save private local files under `F:\Dev\ROMMAGE\OUTPUT` and QA under `REPORTS`. Preserve original ROMs/captures under `FIXTURE`.

## Merged baseline — main

**Phase 0 foundation: implemented, tested and merged via PR #1 (2026-11-09).**

- Read-only iNES 1.0 .nes and single-ROM ZIP parsing, mapper and PRG/CHR checks.
- ROM SHA-256, PRG/CHR offsets, deterministic manifests, raw 2bpp 8x8 tiles and 8 KiB CHR bank exports.
- Synthetic Python tests and an opt-in user-local SMB3 PRG1 ROM integration test.
- GitHub Actions main Tests workflow is Windows-only (Python 3.11/3.12), most recently passing in run 43105552063. No copyrighted game data is present.

Verified private ROM ZIP SHA-256: 4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579. Mapper 4, 256 KiB PRG / 128 KiB CHR, 16 CHR banks / 8,192 raw tiles. Raw tiles do not automatically identify game actors.

**Still not accepted or merged on main:** desktop browser, live emulator adapter, character/sprite inspector and audio catalog. The source-level compiler, 2D composition engine and first full-width GIF builder were merged through PRs #29, #31 and #32, but M1 visual acceptance remains open.

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

## Headless composition engine candidate

The local composition branch adds a recipe-driven PNG/GIF renderer and
terrain-aware motion tracks. Windows verification covers synthetic inputs and
exports. See the [scene composition guide](creative/SCENE_COMPOSITION.md).
[World 1-1 acceptance](https://github.com/87otlto-coder/SpriteMine/pull/28) remains open.

## First source-driven World 1-1 main-area build (draft PR #31)

[Draft PR #31](https://github.com/87otlto-coder/SpriteMine/pull/31), based on
PR #29, adds a private-ROM-only headless compiler for the full 176 × 27 logical
World 1-1 canvas, a frame-local PPU/palette-aware metatile renderer, version-1
private scene recipes, source provenance and visual reference tests. The ROM,
extracted artwork and independent game captures stay out of GitHub.

Local private verification on 2026-11-22: 15 Python tests passed; a bounded
pipe-floor screenshot crop matched 7,680 / 7,680 displayed pixels; a compressed
recording of the late-pipe scene put 45,758 / 46,176 compared pixels within 50
RGB units per channel (mouse excluded); the goal black/sky silhouette matched
4,960 / 4,960 classified pixels. **Only the first result is an exact screenshot
pixel check.** The video-derived checks are approximate and must **not** be
counted as lossless native RGB24 coverage. The game's black zigzag goal edge and
outlined black goal scene are authentic, not rendering corruption.

The model executes 84 / 86 parsed commands, with randomized-cloud placement
unresolved. Big-block shadows and goal geometry are still provisional until
lossless native map validation. Dynamic CHR mapping, animation, enemy tracks,
bonus-room composition and final complete GIF acceptance remain open. This
milestone is **not complete**. See
[the compiler runbook](../tools/m1_world11/README.md) and
[scene composition documentation](creative/SCENE_COMPOSITION.md).


## Original goal-card roulette and animated full-stage preview (draft PR #32)

[Draft PR #32](https://github.com/87otlto-coder/SpriteMine/pull/32) (stacked on
[PR #31](https://github.com/87otlto-coder/SpriteMine/pull/31), then
[PR #29](https://github.com/87otlto-coder/SpriteMine/pull/29)) adds the
headless source-backed 4-phase World 1-1 background animation and the original
3-symbol end-level roulette. The result is a **private, full-width looping GIF**
(2,816 × 432; 12 distinct frames; 130 ms per frame; 1,560 ms combined loop),
plus numbered PNGs, editable recipe and deterministic SHA-256 manifests.

The card uses original ROM OAM 8x16 pattern indices $51/$53/$55 (mirrored
second half), captured sprite palettes 1/2/1, and source placement (2688,336)
from object record $41,$A8,$15. Original disassembly routine
`EndLevelCard_Untouched` changes the card every 8 game ticks (~133.1 ms
NTSC). These assets are **decoded privately from the user's original PRG1 ROM**,
not copied from the compressed gameplay recording or hand-drawn.

On 2026-11-22: 9 local targeted tests passed with private source data; the
12-frame GIF and corresponding PNG RGB pixels matched exactly, and two exports
produced the same GIF SHA-256. GitHub CI is synthetic, with private integration
tests skipped. The owner H.264 recording demonstrates the same mushroom,
flower and star visually, but is not a lossless native-frame validation.

**M1 is not yet accepted:** full-level geometry and dynamic CHR coverage are
provisional; randomized clouds, enemy/object motions and the collected card
fanfare / end sequence remain open. The completed private output is an
animation-preview milestone, not a fully verified final World 1-1 scene.
Runbook: [goal roulette](../tools/m1_world11/GOAL_ROULETTE.md).

## First original-source World 1-1 Piranha wallpaper pass (draft PR #33)

[Draft PR #33](https://github.com/87otlto-coder/SpriteMine/pull/33) adds the
three original World 1-1 pipe plants (Venus Fire Trap, standard green, green
fire) to the complete-width source-backed scene. Sprite OAM tiles and palettes
come from the verified owner's PRG1 ROM and frame 450840 MesenCE snapshot;
placement comes from W101O records at ROM file offset 0xC537. Only source code,
regression tests and instructions are public. Private visual preview: 2,816×432,
144 PNG time slots at 40ms, 5.76s looping GIF. The GIF may merge identical
frames, but decoded cumulative timing agrees pixel-for-pixel with all 144 PNGs.

**Explicit limits:** motion cycles and pipe occlusion are authored wallpaper
approximations, not exact native OAM masks, player-proximity gating or fireball
behavior. Goal-card and CHR animation rates are ~120ms vs original ~133ms in this
higher-rate exported preview. All three source positions are reproduced, but
full stage native pixel QA, clouds and remaining enemy movement are open.
**M1 is not complete.** See [Piranha wallpaper runbook](../tools/m1_world11/PIRANHA_WALLPAPER.md).

## Full source-placement enemy wallpaper pass (draft PR #34)

[Draft PR #34](https://github.com/87otlto-coder/SpriteMine/pull/34)
adds the 11 remaining World 1-1 source enemy entries: four Goombas,
two red Koopas, one green Koopa, a Paragoomba, and three hopping green
Paratroopas. Source graphics are OAM components reconstructed from CHR-ROM
and a verified frame-450840 MesenCE palette/CHR snapshot. All 15 W101O
entries are now represented as source positions in the private scene:
14 enemies plus one untouched goal roulette. This artistic wallpaper displays
them simultaneously; runtime enemy activation is not represented.

Private local output: one fixed **2,816×432**, **144-frame**, **5.76-second**
looping GIF and matching numbered PNGs, with **66 independently controlled
tracks** (51 original background, 1 goal, 3 plants, 11 additional enemies).
The decoded GIF matched all 144 private PNGs exactly in RGB space, and a
second private build produced identical new assets/recipe. Original source
sprite artwork and capture are not checked into the public repo.

**Limitations:** enemy motion, terrain-contact adjustments, OAM piece
alignment and simultaneous presentation are authored wallpaper choices, not
verified emulator gameplay. Random clouds, per-region native pixel
acceptance and visual approval of the complete animated stage remain open.
M1 is not yet accepted. Runbook:
[ground actors](../tools/m1_world11/GROUND_ACTORS_WALLPAPER.md).

## M2 first captured-audio workbench pass (draft PR #36)

[Draft PR #36](https://github.com/87otlto-coder/SpriteMine/pull/36)
provides a headless **captured audio → inspect/edit recipe → PCM16 WAV export**
workbench. It requires no music sequence decoding or APU simulation. Input can be
signed PCM16 WAV directly, or a video/audio container converted to PCM16 with
optional FFmpeg. Versioned JSON clip edits, SHA-256 source/output provenance,
frame-accurate trim intervals, sample-continuous overlap loops and SFX fades
are implemented. Tests are synthetic only on public CI.

The first private source was the owner's 2026-11-22 MesenCE SMB3 PRG1 gameplay
recording (H.264/AAC, 23.232s, 48kHz stereo, SHA-256
`2706294c870f0851c6559c1a7a73201728b6350e38a993538866ff0c8fa5cebc`).
First private deliverables: **6.10s provisional bonus-room music loop**, **3.27s
provisional main-stage music loop** and **1.45s captured goal-card pickup audio**.
All three WAV outputs reproduced byte-for-byte in a second export; 16 synthetic
unit tests pass locally. The private WAVs, video and capture metadata remain
outside public GitHub.

**M2 remains in progress.** The AAC soundtrack includes music and SFX mixed
together; editorial loop boundaries are not verified native song markers.
Audio quality and musical seams need owner listening review. Next: capture a
clean original WAV directly from MesenCE 2.2.1 (separate music and effect takes),
then tune the trims and verify again. Runbook:
[audio capture and export](audio/M2_AUDIO_CAPTURE_AND_EXPORT.md).
