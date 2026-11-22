# SpriteMine — Creative Production Direction (authoritative, 2026-11-22)

**Owner M1 revision (2026-11-22) overrides the earlier section-GIF criteria below:** a complete **11-screen × 27-row main World 1-1** panorama (nominal **2,816×432** logical pixels), including vertical world/scroll coverage, correct art/placement and no texture defects, must precede animation. The entire level is one stationary scene (no repeated sections); Mario none or one; **enemies last**. Existing enemy object records are already documented in `W101O` research, but not in GIF code. See [full-level acceptance](creative/SMB3_WORLD11_FULL_LEVEL_M1_ACCEPTANCE.md).

**Owner-approved pivot:** SpriteMine is a **Windows-first creative extraction and production kit**, starting exclusively with **Super Mario Bros. 3, US PRG1 / Revision A**. Its purpose is to **browse, extract, assemble, animate, preview, and export** usable game-derived backgrounds, sprites, and sound — especially looping stage GIFs, desktop wallpapers, sprite animations and audio files.

**It is not a project to reverse engineer every SMB3 mechanic or achieve exhaustive, pixel-/cycle-perfect emulator reconstruction.** Understanding ROM structures is a means to usable creative output, not the product.

This direction supersedes the research-first / full-level-decoder-before-UI interpretation in older roadmaps, issue descriptions, research notes and draft PRs. Preserve prior evidence; do not delete it or misrepresent its limited validity. If instructions conflict, use this document and [AGENTS.md](../AGENTS.md) before historical research plans.

## Product loop

**Browse → Extract/capture → Compile/compose → Animate → Preview → Export → Reopen/reproduce.**

Every development sprint must advance a working output on this path. Prefer incremental, playable deliverables over expanding explanation of game internals. Headless CLIs, contact sheets and HTML previews are acceptable before the desktop UI.

### Milestone 1 — complete World 1-1 main-area panoramic animation (FIRST; active)

Owner's 2026-11-22 acceptance now requires **the entirety of main World 1-1 as one coherent two-dimensional scene**. The 11×16 logical columns by 27 logical rows give a **nominal 2,816×432 source-coordinate canvas**, though camera offsets and the gameplay/HUD split must be verified. A recognizable subsection or 12-panel animation contact sheet does not pass.

**Production sequence:** source-grounded static main map across both X and Y → correct and audit ROM/captured ground, clouds, pipes, blocks, foreground/background, palette, crops and joins → add independent animations to genuinely placed objects → optionally include Mario **once** (default omitted) → add enemy layer **last** using known source placement research. The separate bonus room is a linked, independently exportable scene, not extra main-stage width.

**Acceptance:** full native scene without repeated placeholder vignettes, visible texture/crop/placement errors or lost vertical regions; full-scene looping GIF, fixed scenery, authentic/clearly labelled motion, editable deterministic recipe, accurate source/capture provenance and screen/row visual QA. Use targeted capture or decoding to fix concrete visual errors; do not require full gameplay reimplementation or expand UI/audio yet. See [full-level acceptance](creative/SMB3_WORLD11_FULL_LEVEL_M1_ACCEPTANCE.md).
### Milestone 2 — Practical SMB3 audio extraction

After the animated-stage GIF is accepted, capture or extract representative SMB3 music and sound effects, browse/listen, trim and choose loop boundaries, and export useful **WAV** files (FLAC where straightforward), with playback verification and source/time metadata. Native music sequence decoding, complete APU reverse engineering and every sound identity are optional research, **not prerequisites**.

**Acceptance:** at least one usable music loop and one distinct sound-effect file are playable, appropriately trimmed/looped where relevant and reproducibly exported with provenance.

### Milestone 3 — Reusable creative asset collection

Organize background sections, sprite animations, effects and audio as reusable **project assets**. Add search/tags/categories and composition recipes. Enable additional creative exports (sprite sheets, GIF/APNG, wallpaper video such as MP4/WebM when practical) according to actual user needs. Do not build a generic asset database before outputs exist.

**Acceptance:** previous GIF/audio assets can be found, reused in a second composition, and re-exported without starting extraction research over.

### Milestone 4 — Windows creative UI

Only after the headless workflows demonstrate value, integrate or adapt the existing PySide6 CHR explorer and expose browsing, composition, timeline previews, audio and exports through a practical Windows interface. The GUI is a front end for already working extraction/composition/rendering services, not a substitute for them.

**Acceptance:** a Windows user can import verified SMB3, select existing assets, change a stage composition, preview and export a GIF and audio without manually running scripts.

## Research and engineering decision gate

Before new ROM/emulator investigation, record all four answers in the active issue/PR:
1. **Which concrete asset/output is blocked?** Link its intended output and current preview or error.
2. **What is the simplest alternative?** Check raw CHR/palette extraction, MesenCE capture, saved-state playback, editing/stitching and manual assembly before writing a new decoder.
3. **What is the minimum unknown to resolve?** Prefer a small targeted experiment with a clear stopping criterion; avoid exhaustive all-level/all-sprite coverage.
4. **What visible/audible improvement will the research deliver?** If the result cannot be demonstrated in the current milestone output, defer it.

Do not start new research branches for PPU cycle timing, precise game physics, arbitrary game logic, full World 1-1 programmatic level decoding, original music sequencers or comprehensive asset classification without a specific production blocker. The previously accepted original-ROM evidence in PRs #21–#25 remains **reusable engineering evidence**, not a mandate for deeper research or a requirement to merge the entire stack before a GIF can be produced.

**Output fidelity rule:** Be correct in the things the user can see/hear and that affect reuse — source palette, transparency, visible alignment/priority, duration, audio quality, loop continuity, provenance. An artist-edited or captured result need not match every original PPU write or ROM object rule; explicitly label what is `raw`, `captured`, `decoded`, or `composed/edited`. Never present an approximate composition as a fully native-decoded original scene.

## Scope and custody

Keep SMB3 PRG1 the only active game until these creative workflows work end to end. Never modify the input ROM. Do not publish copyrighted ROMs, original extracted graphics/audio, save states, captures or third-party material with incompatible licenses. Keep the code, tests and license-safe documentation on GitHub; private game fixtures and outputs remain under `F:\Dev\ROMMAGE`. Use `SOURCE` for code, `TOOLS` for emulators/supporting utilities, `FIXTURE` for original inputs and private validation data, `OUTPUT` for generated wallpapers/GIFs/audio, and `REPORTS` for local QA/progress summaries.

## At the start of every future development conversation

1. Read [AGENTS.md](../AGENTS.md), this product direction, [ROADMAP.md](ROADMAP.md) and [PROJECT_STATUS.md](PROJECT_STATUS.md); inspect active branches/PRs and the most recent **actual rendered outputs**.
2. Identify the active creative milestone and the **next visible deliverable**, not the next unresolved ROM detail.
3. Reuse accepted research only where it shortens the creative output path.
4. Prefer writing/running composition and export code over another explanatory research report.
5. Report what output files were actually produced, opened/visually checked, what remains flawed and how the next change improves the finished asset.
