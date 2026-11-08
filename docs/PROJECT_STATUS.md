# Project status

Updated: 2026-11-08. Source of truth: GitHub code and checks; this snapshot is refreshed with major work.

## Active milestone

**SMB3 PRG1 Phase 0 — foundation.** Feature branch `feature/foundation-rom-chr` contains the initial implementation. Merge requires PR review and any pending CI verification.

## Implemented in foundation branch

- Legacy iNES ROM/ZIP read-only parser; checksums, mapper, bank boundaries, trainer offsets and explicit errors.
- CHR-ROM 2bpp tile decoder and synthetic grayscale tile/bank PNG exporter with deterministic manifest.
- Automated synthetic parsing, bitplane, ZIP safety, provenance and CLI tests.
- GitHub Actions matrix for Windows and Ubuntu, Python 3.11/3.12; workflow status pending GitHub execution.
- Project governance and engineering docs.

## Validated locally on 2026-11-08

- 12 synthetic Python unit tests passed; the optional SMB3 integration test passes when supplied with the ROM (13 total).
- User-provided SMB3 ZIP: iNES, mapper 4, PRG 256 KiB, CHR 128 KiB, whole-ROM SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`.
- PRG/CHR CRC32 `A0ED7D20`/`C2928C49`; combined CRC32 `2E6301ED`.
- 16 exported 8 KiB CHR bank PNGs represent 8,192 tiles. Grayscale values are synthetic.

## Not yet implemented / verified

- No PySide6 interface or user-facing installer.
- No MesenCE integration, OAM/palette capture, animations, decoded levels or audio.
- No emulator state synchronization experiment or tested native Windows desktop UI.
- Coverage beyond raw CHR tile count has not been assessed.
- GitHub CI and native Windows validation are separate gates and must not be assumed passed.

## Next steps

1. Review and merge the foundation PR after checks.
2. Use the `research/smb3-emulator-feasibility` branch to prove synchronized capture of OAM, palettes, CHR mapping and rendered pixels at known frame boundaries.
3. Only then settle the emulator adapter boundary and start the static PySide6 explorer.
