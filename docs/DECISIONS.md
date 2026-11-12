# Architectural decisions

## ADR-001: SMB3 PRG1 only (2026-11-08)

Decision: prioritize end-to-end correctness for SMB3 US PRG1 / Revision A before broad NES compatibility. Consequence: reject unsupported input modes explicitly rather than pretending they work.

## ADR-002: Python core separate from desktop UI (2026-11-08)

Decision: parsing, extraction and provenance are headless and testable independently. PySide6 is for presentation. Consequence: foundational CLI is not the final product.

## ADR-003: Emulator capture is an experiment first (2026-11-08)

Decision: inspect MesenCE C++ facilities but do not assume a stable external capture API; prove same-frame OAM, palette, mapping and rendering access before committing to an adapter. Consequence: dedicated `research/smb3-emulator-feasibility` branch.

## ADR-004: Immutable data and evidence levels (2026-11-08)

Decision: never modify source ROMs; distinguish `raw`, `captured`, `decoded`, and track reversible provenance. Consequence: export grayscale banks as visualizations, not authentic SMB3 sprites.

## ADR-005: Separate test data from copyrighted content (2026-11-08)

Decision: automated CI uses synthetic ROM bytes only. User-provided SMB3 is tested locally via an opt-in integration fixture. No ROMs, save states or extracted art in GitHub.

## ADR-006: Explicit unsupported headers (2026-11-08)

Decision: only legacy iNES parsing is implemented in Phase 0; detect/reject NES 2.0 rather than silently misinterpreting bank sizes or RAM fields.

## ADR-007: Lua-first emulator capture feasibility probe (2026-11-09, provisional)

Try MesenCE's documented Lua scripting facilities for a **research-only** two-frame capture before constructing a C++ interop shim. Use the `endFrame` event and local script data folder with explicitly enabled file I/O; save the original game assets outside GitHub. Validate the byte-stream structure and source identity independently in Python. This does not establish coherent PPU state, final rendered visibility, or physical MMC3 bank provenance. If Lua cannot provide synchronized observations, return to a small C++ instrumentation adapter; do not silently treat the Lua probe as production integration.


## ADR-008: Verify SMB3 sprite RGB against a narrow upstream palette reference (2026-11-10, provisional)

The ROM-backed hardware OAM candidate has shown 138/138 consistent rendered RGB pixels using **screen-fitted** dominant palette-index colors. This is strong spatial evidence but not independent RGB verification. For the current small-Mario research stage, check saved same-session NES palette RAM codes and compare each opaque sprite pixel to a **fixed, independently documented** MesenCE built-in 2C02 default RGB reference, not to a fitted color or guessed generic NES palette. Reference values used: NES 0x16 -> #B53120; 0x36 -> #FECCC5; 0x0F -> #000000 (MesenCE Core/NES/NesDefaultVideoFilter.cpp, commit 4b8a196e299b3de297b204fd1208d2981562c89b).

Implementation keeps only these three researched factual RGB values; it does **not** copy MesenCE's complete GPL palette source or pretend to support unrelated game palettes. Unsupported palette codes produce explicit diagnostic failures. Palette variants, user settings, grayscale/emphasis, native/NTSC filter effects and 118 transparent-background pixels remain outside the claim. Use optional colorized PNGs as local FIXTURE research previews only, preserving alpha 0 for source pixel index zero. Do not mark pixel-perfect reconstruction complete until the independently predicted colors have been compared with the actual captured RGB bytes and the transparent/background region has its own reference.


## ADR-009 — Build first animation timeline from independently verified A/B/A target frames (2026-11-10)

**Decision (experimental):** Preserve the known-good slot-1 MesenCE graphics harness and construct short SMB3 animation timelines using consecutive warmup-offset A/B/A runs. Each run supplies one independently mapped, full-pixel verified **second** frame. Reject gaps, source/build changes, different controller plans or stale reports. Keep repeated RGBA frames as separate timing events; output per-frame emulated frame identifiers and PPU master clocks. Do not infer NTSC milliseconds, clip identity/loop period, or frame holds by deduplication. Export private 16x16 PNGs/spritesheets and metadata only to FIXTURE.

**Rationale:** Building a new continuous capture backend before verifying sequential reproducibility risks incorrectly attributing CHR banks at initial callback state, overlooking sprite-hidden background mismatches, or inventing animation timing. This approach reuses the proven A/B/A gate at the cost of three emulator launches per accepted frame. A future optimized recorder may replace it once a real contiguous SMB3 sample passes. ROM/save-state/game imagery never leaves FIXTURE.
