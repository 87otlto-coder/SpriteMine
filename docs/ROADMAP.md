# SpriteMine — Creative Production Roadmap (owner realignment: 2026-11-22)

**North star:** browse SMB3 resources, extract/capture usable assets, **compile and animate compositions**, preview real results and export wallpapers, animations and audio. Deliver **finished creative files** before deepening ROM reconstruction. See [product direction](PRODUCT_DIRECTION.md) and [AGENTS.md](../AGENTS.md).

**Owner M1 revision (2026-11-22) overrides the earlier section-GIF criteria below:** a complete **11-screen × 27-row main World 1-1** panorama (nominal **2,816×432** logical pixels), including vertical world/scroll coverage, correct art/placement and no texture defects, must precede animation. The entire level is one stationary scene (no repeated sections); Mario none or one; **enemies last**. Existing enemy object records are already documented in `W101O` research, but not in GIF code. See [full-level acceptance](creative/SMB3_WORLD11_FULL_LEVEL_M1_ACCEPTANCE.md).

**Active target:** **Super Mario Bros. 3 — USA PRG1 / Revision A** only. **Headless-first, output-first**: a functional CLI plus generated preview is fine before PySide6. The previous eight-phase research/level-decoding/UI-first ladder is retired as the *product development order*; its verified work is retained as reusable technical evidence.

| Order | Creative milestone | Required user-visible deliverable | Acceptance gate |
| --- | --- | --- | --- |
| **1 — NOW** | **Complete 2D World 1-1 panoramic stage** | **2,816×432 nominal logical-coordinate static PNG**, then seamless **full-scene animated GIF**; source dimensions subject to viewport/world-offset verification | All main-stage horizontal/vertical regions, correct terrain, blocks, clouds/pipes, no substituted textures or crops; separately controlled animations; Mario absent or once; enemies last; editable JSON and reproducible QA |
| **2** | **SMB3 audio production** | Playable music loop and one distinct SFX exported to WAV; optional FLAC | Capture/extract, listen, trim and specify loop points; audible QA; source/timing metadata; deterministic or clearly documented recording reproducibility |
| **3** | **Reusable asset/project workbench** | Browseable library and a **second composition** reusing assets from M1/M2; additional animation/wallpaper formats | Meaningful asset labels, editable compositions, provenance, search/tags; real exports verified, e.g. PNG sheets/GIF/APNG and MP4/WebM when practical |
| **4** | **Windows desktop creative kit** | Usable PySide6 app for ROM import → asset browse → composition → preview → export | Working headless services integrated into UI; Windows native interaction, errors, exports and packaging checked |

## Milestone 1 — build order (full 2D world, before audio/UI)

1. **Source-grounded two-dimensional map:** parse and/or capture the full main World 1-1, 11 horizontal screens by 27 logical rows. Track world X/Y, source, overwritten/missing cells and camera-offset alignment. Do not duplicate a scene panel or crop to the first visible 192/240 vertical pixels.
2. **Native-size static panorama:** place authentic scenery at correct world positions, including upper and lower regions, source-correct ground/pits, pipes, blocks, goal and clouds. Exclude Mario/enemies while auditing terrain; render without HUD. Reject unknown or invalid textures and visibly flag missing data.
3. **Screen and height QA:** compare selected regions across both horizontal and vertical scroll positions against actual gameplay; verify CHR mapping, palette, layer order, dimensions, clip bounds and coherent joins.
4. **Animate genuinely placed objects:** independent question blocks/coins and appropriate effects, fixed scenery, seamless GIF, editable JSON composition and hashes. Mario absent or exactly once if chosen.
5. **Enemy pass LAST:** reuse existing source-derived `W101O` placement records (14 enemies plus one end-level card) and associated runtime spawn research; add actual sprite graphics and coherent motion only after the stage and its animated background are accepted.
6. **Final acceptance:** one complete static PNG, one complete full-width/full-height GIF, per-screen/per-row QA, private reproducible outputs under `OUTPUT`, and visual approval by owner. No audio or UI before M1.

Do not mistake 27 rows of logical/PPU staging for 432 pixels concurrently visible in the emulator; account for vertical camera travel and omit HUD contamination. The separate two-screen bonus room may be exported as its own linked scene later, not spliced into the main panorama. [Detailed acceptance](creative/SMB3_WORLD11_FULL_LEVEL_M1_ACCEPTANCE.md).
## Evidence and scope

- Preserve ROM hashes, bank offsets and exact source names where relevant, but optimize the workflow for usable assets rather than a theoretical complete decoder.
- Label `raw` vs `captured` vs `decoded` vs `composed/edited` in manifests. A stitched screenshot can be a creative background; do not label it a fully decoded level.
- **Visual/audio output gates take precedence over emulator internals.** Investigate internals only for a specific blocked or visibly incorrect deliverable, after simpler extract/capture/manual approaches.
- Existing research PRs #21–#25 include source-accurate CHR, CPU/CIRAM and 13-frame World 1-1 bonus RGB evidence; reuse what helps produce the GIF and **do not launch another renderer-forensics sprint as a prerequisite**.
- No GUI-first sprint: open PySide6 PR #4 remains valuable for M4 but is not the immediate Milestone 1.
- Never alter originals or commit copyrighted ROMs, derived art/audio, captures or save states to public GitHub. Follow Windows-only CI; keep outputs local under `F:\Dev\ROMMAGE\OUTPUT`.
- Track actual delivered assets and output quality. Comprehensive reverse-engineering coverage is **not** a milestone or release criterion.

## Before beginning any new research branch

Link the blocked creative output, explain why capture/raw extraction/manual arrangement cannot solve it, state the smallest experiment and its stop condition, and describe what improved GIF/audio export it will produce. If these are missing, return to the active production pipeline.


**Implementation update (2026-11-23):** The complete-width source-driven preview and looping GIF are now implemented on `main` through PRs #29, #31 and #32. Their existence does not imply complete native validation. Continue M1 with original-source enemy animations, per-region visual QA and final owner acceptance; the goal roulette is already implemented.
