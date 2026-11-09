# Project status

Updated: 2026-11-09. GitHub implementation and test results take precedence over conversations.

## Foundation: merged

PR #1 merged into `main` (commit `117362e447bf2555c990898dc135b80032328835`).

- Read-only legacy iNES ROM/ZIP loader, checksums, mapper/bank/trainer inspection and explicit unsupported-format errors.
- Deterministic CHR-ROM 2bpp decoding, grayscale bank/tile PNG exports and JSON provenance.
- Synthetic tests and optional private SMB3 PRG1 validation.
- Four foundation CI jobs passed: Python 3.11/3.12, Windows and Ubuntu.
- Previously verified supplied SMB3 ZIP: mapper 4, PRG 256 KiB, CHR 128 KiB, 16 CHR banks / 8,192 raw 8×8 tiles; known ROM SHA-256 and PRG/CHR CRCs in README.

## Active work: Phase 2 prototype (PR pending)

Branch `feature/static-chr-explorer` implements a **static-only PySide6 CHR browser**:

- ROM import and verification notice.
- Select any 8 KiB CHR bank, inspect and zoom its 512 raw tiles.
- Select tiles; show global index, bank coordinates, ROM and CHR byte offsets.
- Choose synthetic grayscale, green or amber palette previews. These are **not** authentic SMB3 palettes.
- Export selected tile, bank or all banks in grayscale with deterministic manifest.
- Synthetic rendering tests and offscreen Qt smoke tests; **all six CI jobs passed** on Windows and Ubuntu (Python 3.11/3.12 core matrix plus two Qt smoke jobs). The GUI export regression test also passed in the latest six-job CI run (PR #4, commit `537e446e6dfc142004e0259d352c6f1a3d9e8108`).

### Native Windows observation — partial acceptance (2026-11-09)

The project owner supplied screenshots of the actual SpriteMine Windows desktop application. These show:
- The application launches and renders its empty-ROM state without an apparent startup error.
- Loading `Super Mario Bros. 3.zip` displays **Verified SMB3 US PRG1 / Revision A**.
- Bank 0 renders as a scrollable grayscale CHR atlas; the status bar reports **16 CHR-ROM banks / 8,192 raw tiles**.
- Selecting tile **19** displays bank **0**, coordinates **(3, 1)**, CHR offset **0x00130**, ROM offset **0x40140**, and source length **16 bytes**. This is consistent with the expected offset math.
- Both screenshots were supplied in the ChatGPT conversation and are intentionally **not committed** (copyrighted graphical content).

**Not yet observed interactively:** switching to bank 15, changing preview palettes, exporting tiles/banks and checking manifests, handling a malformed ROM, or resizing/zooming behavior. Native Windows testing is therefore **partially passed, not complete**.

This phase can progress independently while the MesenCE adapter feasibility is investigated.

## Runtime research: unproven

Branch `research/smb3-emulator-feasibility` has an experiment plan for synchronized OAM, palette, MMC3 CHR mapping, frame/scanline, screenshot, state replay and audio capture. **No emulator integration has been demonstrated.** Issue #2 tracks this gate.

## Pending

- Desktop CI passed and initial Windows launch/import/tile-selection checks were observed; complete bank switching, preview palette, export and invalid-file checks before declaring PR #4 fully validated.
- Prove same-frame MesenCE state acquisition before live sprite tools.
- Correct runtime palettes, transparent sprite reconstruction, animation capture, World 1-1 decoding and audio remain unimplemented.
- No Windows installer or evidence-based SMB3 decoded asset coverage report yet.

## Next

1. Finish the remaining native Windows acceptance checks in PR #4; the initial launch, SMB3 import, atlas and provenance views have been observed.
2. Continue MesenCE research issue #2 on research branch; validate synchronization before coupling live UI.
3. Record user-observed results and acceptance in this file.
