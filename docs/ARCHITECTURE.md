# Architecture and provenance

## Creative production pipeline (current objective)

```text
immutable SMB3 PRG1 ROM / private MesenCE capture
     |
     +--> browse/discover (tile atlas, contact sheets, asset manifest)
     |
     +--> extract/capture (PNG frames, palettes, audio; source provenance)
     |
     +--> compose (fixed-camera scene, layers, actors, editable JSON recipe)
     |
     +--> animate (independent frame timing, alpha, positions, loop schedule)
     |
     +--> render/preview (real frame outputs and loop QA)
     |
     +--> export (first: animated stage GIF; next: WAV/FLAC/audio; later video)
     |
     +--> reusable asset library --> PySide6 interface once proven headlessly
```

The product is a **creative kit**. A stage composition assembled from real game graphics, captured frames and manually arranged layers is valid output; it need **not** reproduce SMB3 game-logic internals. Label all authored placements, invented motion and edited assets as `composed/edited` instead of claiming they were decoded verbatim from ROM data.

Keep extraction, composition and rendering as separately callable, testable headless services. Keep PySide6 out of decoding and export logic; emulator integration is replaceable and used only where capture materially improves creative output. Do **not** build a full emulator, scene-graph framework or exhaustive World 1-1 level decoder before the first GIF works. See [current product contract](PRODUCT_DIRECTION.md) and [creative roadmap](ROADMAP.md).

## Evidence classes

- `raw`: ROM content decoded directly, with exact input checksums and file offsets. A 2bpp tile is graphics data, **not** a named character.
- `captured`: observations from a particular emulator build, state, frame/scanline and input sequence; record ROM hash and replay information.
- `decoded`: SMB3 game-specific interpreted structures with decoder version and explicit validation evidence.
- `composed/edited`: authored arrangement, artist-adjusted asset, stitched/captured backdrop or timed animation assembled for creative use; preserve source references plus edit/placement instructions. This is valid for wallpaper production, but **not** proof of a native original-game level layout.

## Current export manifest v1

`manifest.json` includes `schema_version`, `provenance_type`, `rom_sha256`, `mapper`, `chr_rom_offset`, `decoder`, `palette`, and ordered `entries`. Each entry contains output name, absolute ROM offset, relative CHR offset, source byte length, and PNG hash; tile exports include tile index and bank coordinates. Manifest ordering and key formatting are deterministic. No local paths or timestamps are embedded.

## Proposed Milestone 1 composition recipe contract (implementation target)

An editable private JSON recipe should describe canvas width/height, fixed stage camera, static background/foreground layers, positioned objects, references to original extracted or captured frame assets, per-object animation durations, total loop length and export settings. Store a `recipe_version`, export/tool version, source image hashes, source ROM fingerprint, asset `raw/captured/decoded/composed` labels, and any manual edits. **Do not lock into a universal schema before the first GIF is built and reviewed.**

Acceptance is observable: regenerate from the same recipe/assets, open the GIF, verify alpha/color/placement and the last-to-first transition, and record the output hash and QA notes. Test reports alone are not a completed creative deliverable.

## Planned captured frame contract

A capture session should record ROM hash, emulator binary/version, mode/region, save-state checksum, controller input history, frame/scanline timestamp, PPU mapping, OAM, palette memory, scroll, screenshot and audio sample interval. Memory snapshots without scanline information may be insufficient on MMC3. Hardware sprite reconstruction and visible rendered sprite observations must remain distinct.

## Unsupported or deferred on purpose

NES 2.0 headers are detected but not parsed. CHR-RAM has no static CHR-ROM atlas. No authentic palette is inferred from raw CHR bytes. Exhaustive level/object disassembly, complete PPU cycle recreation, full game physics and structured music sequence decoding are **not prerequisites to creative output**; research them only when a concrete GIF or audio export demonstrably needs it. The current main branch still contains the merged Phase 0 importer/exporter; the stage compositor is a planned feature, not an implemented main feature.
