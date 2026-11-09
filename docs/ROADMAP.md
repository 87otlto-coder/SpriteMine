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
