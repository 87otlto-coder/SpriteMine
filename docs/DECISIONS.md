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
