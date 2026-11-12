# SMB3-first roadmap and acceptance checks

Status is recorded in [PROJECT_STATUS.md](PROJECT_STATUS.md). Work remains **SMB3 PRG1 / Revision A only**.

| Phase | Deliverable | Demonstrable acceptance |
|---|---|---|
| 0. Foundation | ROM parser, 2bpp CHR export, tests | Correct user ROM hashes; 16 bank images / 8,192 tiles; deterministic offsets; CI |
| 1. Emulator feasibility | Replaceable capture adapter proof | At a reproducible frame, captured OAM/palettes/CHR mapping agree with actual output; state + input replay works |
| 2. Static explorer | PySide6 ROM, bank, tile, palette views | Load verified ROM, inspect and export any tile with provenance |
| 3. Sprite inspector | Reconstruct hardware components and visible sprites | Reconstruct Mario from verified OAM components with correct alpha/flip/priority behavior |
| 4. Animations | Capture, align, preview and export | Mario walk plus one enemy animation export with durations/origins, no background contamination |
| 5. Level decoder | SMB3 World 1-1 interpreted data | Decode complete World 1-1 layout and object list; compare scrolling sections against emulator |
| 6. Audio | Captured music and sound effects | Reproducible WAV/FLAC with intervals and limitations; sequence decoding explicitly optional |
| 7. Windows release | Integrated desktop build + coverage report | Windows launch, import, sprite/animation/level/audio workflows, regression checks and provenance |

## Dependency gates

The emulator adapter is the highest architectural risk: test it before tying UI design to MesenCE internals. Distinguish OAM sprite entries from actual rendered pixels. Do not infer complete levels from screenshot stitching. Default audio milestone is recorded output, not guaranteed original sequences.

## Coverage

Maintain independent counts for raw discovered resources, captured occurrences and validated game-specific decoded assets. Unknowns are not silently counted as completed assets.

## Execution priority: research-first, shell-driven (2026-11-12)

This is the **working order**, not a change to the final SMB3 milestone or to the original phase definitions above. The existing PySide6 prototype in PR #4 stays intact, but new UI scope is deferred while we validate extraction/reconstruction. Do not mark its pending native Windows acceptance complete or merge it solely because the UI has been deprioritized.

1. **Mario animation evidence (active).** Extend the verified right-input sequence from emulator frames 448385–448387 (one identical 16x16 RGBA pose held for three video frames) by reusing its immutable warmup-8/9/10 A/B/A archives and capturing warmups 11–19. First gate: an independently verified distinct RGBA pose with the exact transition frame, OAM/CHR/palette provenance and control checks. Then validate a full cycle and timing separately. Twelve frames are not automatically a full animation.
2. **Second-character reconstruction.** Choose an observed SMB3 enemy, prove component grouping and rendered RGB/background agreement at multiple reproducible states; distinguish OAM components from visible objects. Unsupported overlap, priority, eight-sprites-per-scanline effects and per-scanline bank changes remain explicit.
3. **Headless asset pipeline.** Make validated raw/captured/decoded records searchable and exportable with immutable source identities, decoder version, precise offsets/frame clocks, checksums and validation states. Start with deterministic JSON; introduce SQLite only once real catalog queries justify it.
4. **World 1-1 reconstruction.** Decode ROM-backed layout/object structures, map physical offsets and bank selection, then compare scrolling sections and object placement with emulator evidence. A stitched screenshot is not decoded level data.
5. **Audio capture.** Produce reproducible, sourced recordings and intervals before investigating game-specific music sequence decoding.
6. **Desktop integration.** Resume the static explorer acceptance and connect the verified headless capabilities. A complete Windows desktop app remains the release goal.

### Headless deliverable contract

Each implemented feature should expose a shell-usable command (or callable Python module) and, where appropriate, generate: (a) a directly inspectable preview (PNG, spritesheet, HTML or WAV), (b) a machine-readable provenance/report JSON, and (c) the original, reproducible capture/decoder inputs identified by checksum. Save any copyrighted output only under `F:\\Dev\\ROMMAGE\\FIXTURE`. Store code/docs in `SOURCE` and tools in `TOOLS`; preserve ROMs and prior evidence. Do not commit images/audio derived from the game, source ROMs, save states, or private capture buffers.

Use Windows-only CI with synthetic fixtures, no unnecessary artifact uploads, and no claim that CI replaces the owner's private MesenCE observation. See [animation runbook](../docs/research/SMB3_ANIMATION_TIMELINE.md) on the consolidated `research/smb3-emulator-feasibility` branch. That branch holds the graphics and animation research; neither is yet part of production `main`.
