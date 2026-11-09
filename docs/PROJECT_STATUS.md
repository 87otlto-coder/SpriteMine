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

This phase can progress independently while the MesenCE adapter feasibility is investigated.

## Runtime research: unproven

Branch `research/smb3-emulator-feasibility` has an experiment plan for synchronized OAM, palette, MMC3 CHR mapping, frame/scanline, screenshot, state replay and audio capture. **No emulator integration has been demonstrated.** Issue #2 tracks this gate.

## Pending

- Desktop CI passed; test GUI interactively on the owner's Windows computer, then review and merge PR #4.
- Prove same-frame MesenCE state acquisition before live sprite tools.
- Correct runtime palettes, transparent sprite reconstruction, animation capture, World 1-1 decoding and audio remain unimplemented.
- No Windows installer or evidence-based SMB3 decoded asset coverage report yet.

## Next

1. Review PR #4, which has passing CI; get first actual Windows GUI run.
2. Continue MesenCE research issue #2 on research branch; validate synchronization before coupling live UI.
3. Record user-observed results and acceptance in this file.
