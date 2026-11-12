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

## ADR-007: Headless-first research sequencing (2026-11-12)

Decision: pause expansion of the desktop interface while completing reproducible SMB3 sprite, animation, catalog, level and audio capabilities. The existing PySide6 static CHR prototype remains reviewable under PR #4, with native Windows acceptance still outstanding. The desktop interface remains essential to the eventual release, but it is not the near-term research dependency.

Consequences:
- Keep parsers, capture validators, timeline assemblers and export logic independent of Qt; run them through PowerShell/Python.
- Where useful, emit inspectable PNG/spritesheet/HTML/WAV previews alongside versioned, checksum-bearing JSON records; do not mistake preview timing for verified frame timing.
- Preserve immutable ROMs, private MesenCE state/captures and A/B/A evidence under F:\\Dev\\ROMMAGE\\FIXTURE, never public GitHub.
- Validate a real Mario pose transition before claiming a full animation; independently prove a second character before generalizing sprite grouping.
- Resume UI integration only for demonstrated capabilities. This decision changes task order, not the SMB3-first scope or release acceptance requirements.
