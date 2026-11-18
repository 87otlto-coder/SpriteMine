# Architecture and provenance

## Boundaries

```text
.nes / single-ROM ZIP
    -> read-only ROM loader (format, size, mapper, fingerprints)
    -> raw CHR 2bpp extractor -> PNGs + manifest
    -> [future] emulator capture adapter (MesenCE candidate)
    -> [future] semantic sprite / animation / SMB3 level decoders
    -> [future] SQLite project catalog + PySide6 user interface
```

Parsing and export code in `src/spritemine/` must remain independent of Qt. A capture adapter must be replaceable, and should return immutable typed observations, not UI objects. No NES code execution or live emulator behavior exists in Phase 0.

## Evidence classes

- `raw`: ROM content decoded directly, with exact input checksums and file offsets. A 2bpp tile is graphics data, **not** a named character.
- `captured`: observations from a particular emulator build, state, frame/scanline and input sequence; record ROM hash and replay information.
- `decoded`: SMB3 game-specific interpreted structures with decoder version and explicit validation evidence.

## Current export manifest v1

`manifest.json` includes `schema_version`, `provenance_type`, `rom_sha256`, `mapper`, `chr_rom_offset`, `decoder`, `palette`, and ordered `entries`. Each entry contains output name, absolute ROM offset, relative CHR offset, source byte length, and PNG hash; tile exports include tile index and bank coordinates. Manifest ordering and key formatting are deterministic. No local paths or timestamps are embedded.

## Planned captured frame contract

A capture session should record ROM hash, emulator binary/version, mode/region, save-state checksum, controller input history, frame/scanline timestamp, PPU mapping, OAM, palette memory, scroll, screenshot and audio sample interval. Memory snapshots without scanline information may be insufficient on MMC3. Hardware sprite reconstruction and visible rendered sprite observations must remain distinct.

## Unsupported on purpose

NES 2.0 headers are detected but not parsed. CHR-RAM has no static CHR-ROM atlas. No authentic palette is inferred from raw CHR bytes. Full levels, animations and source music sequences require further research and tests.

## Headless SMB3 reconstruction on PR #21

The package uses the existing immutable ROM loader and CHR bitplane decoder. The player reader owns game-specific recipes and canonical render provenance. The sprite compositor consumes supplied fetch-time CHR pages and indexed background data for one raster line. The optional MesenCE research runner owns replay, observations and native comparisons. The World 1-1 bonus decoder returns a source model and separately compares a caller-supplied Tile_Mem dump. See [headless validation](research/SMB3_HEADLESS_VALIDATION.md).

## World 1-1 native pipe replay

The optional native pipe replay runner consumes immutable controller poll masks and records CPU-cycle-stamped events and private emulator snapshots. It keeps detailed capture in leg B and compares common evidence across three independent runs. See [native pipe approach](research/SMB3_NATIVE_PIPE_APPROACH.md).
