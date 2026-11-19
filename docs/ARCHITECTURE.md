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

## Headless SMB3 reconstruction (PR #21; not merged)

The PR #21 code extends the immutable ROM/CHR reader with game-specific player recipes, a pure indexed 8×16 sprite/OAM compositor, independent 24-frame native A/B/A comparison, and a deterministic World 1-1 bonus-room logical tile decoder. MesenCE Lua and Python replay helpers remain **optional research instrumentation**, not a runtime package dependency.

The verified native World 1-1 flight enters the upper screen-8 pipe with genuine controller-only input. Its four early-OAM pipe masks use actual PPU window-5 CHR page `$04` and behind-background priority. Native comparison matches **7,528 distinguishable occlusion samples** with zero errors; 644 ambiguous RGB samples are excluded, and the entire screen is **not** certified. The first-entry bonus-room `$89A0` post-layout capture matches the model for **864/864 logical Tile_Mem bytes**. Refer to [SMB3_NATIVE_RACCOON_PIPE.md](research/SMB3_NATIVE_RACCOON_PIPE.md), which preserves the state/input hashes, timing and private acceptance evidence. These results are valid for the recorded scenario and not generic SMB3 coverage.

## Next headless background boundary

`source layout record -> validated logical 16x16 tiles -> Plains four-quadrant 8x8 pattern references -> 8-pixel scrolling strips -> PPU attribute bytes -> frame/scanline-specific MMC3 CHR-ROM pages -> 2bpp indexed background pixels -> active PPU palette -> optional filtered RGB comparison`.

Keep logical tile memory, staged game scroll buffers, current physical PPU nametable memory, mapper register history and final RGB separately versioned. Do not infer final native pixels from the validated 864-byte logical tile map or from post-IRQ CHR mappings. The standard horizontal code prepares 54-byte pattern strips (30+24 split between `$20xx`/`$28xx`) and 14-byte attribute strips. Exact native strip, attribute, current-page and rendered-pixel validation is the next milestone, with tests backed by synthetic fixtures and private ROM/hash expectations.


## Native Plains producer probes (unmerged, headless)

A separate optional research observer samples CPU Scroll_PatStrip
($0382-$03B7) and Scroll_AttrStrip ($03BA-$03C7) immediately after their
respective producers complete, using read-only debugger reads. It records the
two explicit attribute source columns chosen by scroll direction/parity,
rather than assuming consecutive columns. Exact comparisons are conditional
on native first-entry bonus Tile_Mem fingerprints and the A/B/A replay
integrity report. These data are **CPU staging state**, not proof of final
PPU nametable, fetch-time CHR mapping, or rendered pixels. See
[staging guide](research/SMB3_BACKGROUND_NATIVE_STAGING.md).
