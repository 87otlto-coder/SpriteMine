# SMB3-first roadmap and acceptance checks

Current progress: Phase 0 merged; Phase 2 static explorer prototype in progress; Phase 1 emulator feasibility still an unproven gate for runtime functionality.

| Phase | Deliverable | Demonstrable acceptance |
|---|---|---|
| 0. Foundation | ROM parser, 2bpp CHR export, tests | Correct user ROM hashes; 16 bank images / 8,192 tiles; deterministic offsets; CI — **passed** |
| 1. Emulator feasibility | Replaceable capture adapter proof | At a reproducible frame, captured OAM/palettes/CHR mapping agree with actual output; state + input replay works — **unproven** |
| 2. Static explorer | PySide6 ROM, bank, tile, palette views | Load verified ROM; inspect, zoom, preview and export any tile with provenance — **implementation pending GUI validation** |
| 3. Sprite inspector | Reconstruct hardware components and visible sprites | Reconstruct Mario from verified OAM components with correct alpha/flip/priority behavior |
| 4. Animations | Capture, align, preview and export | Mario walk plus one enemy animation export with durations/origins, no background contamination |
| 5. Level decoder | SMB3 World 1-1 interpreted data | Decode complete World 1-1 layout and object list; compare scrolling sections against emulator |
| 6. Audio | Captured music and sound effects | Reproducible WAV/FLAC with intervals and limitations; sequence decoding explicitly optional |
| 7. Windows release | Integrated desktop build + coverage report | Windows launch, import, sprite/animation/level/audio workflows, regression checks and provenance |

## Dependency gates

The emulator adapter is the highest architectural risk: test it before building live sprite UI on MesenCE internals. The static ROM/CHR viewer is independent and can proceed in parallel. Distinguish OAM sprite entries from actual rendered pixels. Do not infer complete levels from screenshot stitching. The default audio milestone is recorded PCM output, not guaranteed original sequences.

## Coverage

Maintain independent counts for raw discovered resources, captured occurrences and validated game-specific decoded assets. Unknowns are not silently counted as completed assets.
