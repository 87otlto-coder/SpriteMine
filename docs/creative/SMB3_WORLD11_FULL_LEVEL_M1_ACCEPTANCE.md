# Milestone 1 acceptance — complete two-dimensional World 1-1

**Owner revision: 2026-11-22.** This supersedes the earlier 'recognizable section' GIF acceptance in older roadmap text and PR #27. The existing artist-composed 48-frame GIF is a useful **prototype**, not a completed M1 deliverable.

## Target geometry and source evidence

- The original US PRG1 main World 1-1 header reports **11 horizontal screens**, each **16 logical tile columns** wide. The game prepares **27 logical rows** of 16×16 tiles per horizontal screen. The **nominal main-area tile canvas** is therefore **176 columns × 27 rows = 2,816 × 432 native pixels**. This is a logical construction/staging coordinate space, **not proof that every pixel in the 432-pixel height is visible simultaneously** or that the final output must show a HUD.
- Source pointers: the main area header begins at ROM file offset `0x1FB92` and its 264-byte source layout stream at `0x1FB9B`. The code in `Scroll_DoColumn` stages 54 eight-pixel patterns for the 27 logical rows; a normal 256×240 viewport observes only part of that vertical world, potentially after vertical scrolling. Preserve world X **and world Y**, camera offsets, per-row completeness and source provenance.
- There is a **separate two-screen bonus area** connected via a pipe. Treat it as a distinct composition/scene with a world-coordinate link, not extra main-area columns or a pasted strip. Include an optional bonus-room export later, without making it a prerequisite for the complete **main** World 1-1.
- Ground runs, gaps, pipes, blocks and the goal are determined by ordered construction records, sometimes with overwrites. Clouds use an RNG-dependent original generator; preserve captured seed/state or explicit source-derived provenance before claiming their placement is native.

## Implementation gates (ordered)

1. **Two-dimensional static world map:** derive or reliably capture **all 176×27 logical cells**, not only the portion visible at Mario's default height. Keep `world_x`, `world_y`, `source_command`, `palette/CHR_mapping`, `coverage`, `confidence` and overwrite order. Detect missing data and conflicts; **do not repeat the same vignette** to fill the width. Assert the exact expected logical dimensions and source stream boundaries.
2. **Full-size static native PNG:** compose the complete main-level plane at its validated world X/Y bounds, ideally initially **2,816×432 native pixels** without rescaling. No Mario and no enemies. Do not crop to 256×192 gameplay or 256×240 emulator viewport; do not bake HUD pixels into level scenery. Test known high objects (e.g., upper pipe entrance at source column 141, row 7) as well as the lower ground around rows 25–26 so the vertical extent is meaningful.
3. **Texture and geometry audit:** remove PR #27's hand-drawn clouds, repeated dirt IDs, artificial grass, repeated hill/bush motifs and cropped pipe constructions. Use correct ROM-derived or source-grounded captured art with palette, bank and alpha metadata. Validate **vertical** anchoring and layer priority as carefully as X positions, including tops of pipes, suspended blocks, slopes/holes and possible scroll/overlap boundaries.
4. **Reference comparison:** compare stitched source/capture observations at several world X **and Y** positions against appropriate MesenCE gameplay images, accounting for camera offsets, gameplay/HUD split and the fact that PPU update buffers and final visible frames differ. Report mismatches/missing cells per screen and vertical row. Do not claim pixel equality where not tested.
5. **Placed animation:** attach independent, correct animation sources/timing to the genuine world objects (e.g., question blocks and coins) while keeping the entire world background fixed. Export a full-world stationary looping GIF and regenerate from JSON. No duplicate Mario: default **none**, optional **exactly one** in the whole scene. A contact sheet of time-sampled frames is not a stage panorama.
6. **Enemies last:** reuse the existing **W101O** source list in PRG bank 6: **15 placement records, 14 enemies plus one end-level card**. Its records and scroll-based spawning mechanisms have already been researched, but the current GIF compositor does not integrate them. Add enemy imagery, bounds, placement and looping motion only after the static map and world animations pass. Source placement does not prove simultaneous active/visible sprites.

## Acceptance outputs

- A validated **full two-dimensional static panorama**, without corrupt/duplicated/missing textures, wrong crops, displaced or incorrect graphics, and with the top and bottom of the actual level preserved.
- A **complete level** seamlessly looping animated GIF with fixed scenery, coherent correctly positioned animations and accurate transparency/palette.
- An editable scene recipe with source/decoder/capture IDs, 2D dimensions, animation tracks and hashes; a completeness manifest, per-screen/per-row visual QA and Windows reproducibility commands.
- The first milestone is **not complete** until the owner accepts the full native scene and animated result. Audio and the UI remain on hold. The separate bonus area and other levels do not delay the initial **main 1-1** gate.

## What is already known (avoid rework)

- PR #27 implements a headless GIF writer and independent animation schedules, **but its stage geometry is manually composed**. It repeats scenery and crops local screenshot regions, and it does not expose a native full-level tile layout.
- World 1-1 research has verified the header/stream fingerprint and statically interpreted many generator placements, including the source enemy object list and camera-dependent spawning. This is source-level evidence, **not a finished whole-main-area ROM decoder or native full-area render**.
- PR #25's 638,976 exact pixels were from a **bounded bonus-room background**, not a whole 11-screen by 27-row main-area match.

See the source-derived [World 1-1 reconstruction research](https://github.com/87otlto-coder/SpriteMine/blob/research/smb3-rom-spelunking-20261116/docs/research/SMB3_WORLD1_1_RECONSTRUCTION.md), [background PPU row staging research](https://github.com/87otlto-coder/SpriteMine/blob/research/smb3-rom-spelunking-20261116/docs/research/SMB3_BACKGROUND_PPU_RENDERING_SPELUNKING_20261118.md), and [PR #27 prototype](https://github.com/87otlto-coder/SpriteMine/pull/27).

**Scope:** No game mechanics beyond what visibly supports this export, no UI/audio, and no copyrighted ROMs, screenshots or derived graphics in public GitHub. Source and tests in `F:\Dev\ROMMAGE\SOURCE`; local ROMs/captures in `FIXTURE`; generated panorama/GIF under `OUTPUT`; QA under `REPORTS`.
