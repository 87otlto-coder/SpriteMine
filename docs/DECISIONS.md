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

## ADR-007: Creative production replaces exhaustive ROM reconstruction as the goal (2026-11-22)

**Status: accepted by project owner. Supersedes the research-first/level-decoding-first *priority order* in earlier roadmaps and open research branches, not the validity of prior evidence.**

**Problem:** Research repeatedly expanded into long emulator/ROM-forensics loops with no corresponding wallpaper, animated stage, sprite animation or audio file that a user could play or use.

**Decision:** SpriteMine is a **creative extraction and assembly kit**. Headless pipelines must browse/extract or capture original graphics, compile scenes, animate independent elements, preview and export finished assets. **Milestone 1 is a real, seamless looping World 1-1 stage GIF** with at least two independently animated elements and a reproducible editable composition recipe. **Milestone 2 is practical music/SFX capture and WAV export**. A reusable asset library follows; PySide6 desktop UI comes **after** core creative outputs are proven.

**Alternatives considered:** continue physical PPU cycle verification, exhaustive level/object disassembly, generic emulation, or build the GUI now. Rejected as initial prerequisites: none directly produces the first desired creative asset. A small, targeted investigation remains valid if a particular output is blocked and simpler raw extraction/emulator capture/manual composition cannot solve it.

**Consequences:**
- Keep accepted PR #21–#25 ROM/graphics evidence as reusable source modules; stop extending the research pipeline without a concrete creative-output need.
- A scene constructed from real captured graphics and manually arranged layers is valid **creative output**; do not mislabel it a fully decoded native game level.
- Measure completion with playable GIF, quality review and seamless loop, deterministic editable recipe and file provenance. Passing tests or matching emulator pixels alone cannot complete a creative milestone.
- Preserve immutable ROMs and proper palette/transparency/timing fidelity where visually/audibly important. Preserve raw/captured/decoded/composed distinctions.
- Keep original SMB3 PRG1 scope, Windows-first workflow, private copyrighted assets and source/TOOLS/FIXTURE/OUTPUT/REPORTS separation.
- Update AGENTS.md, PROJECT_INSTRUCTIONS.md, README, ROADMAP and PROJECT_STATUS for subsequent agents. The canonical specification is [PRODUCT_DIRECTION.md](PRODUCT_DIRECTION.md).
