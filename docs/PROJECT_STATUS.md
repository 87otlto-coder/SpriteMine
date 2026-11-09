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

## 2026-11-09 — MesenCE Lua research probe (research branch only)

- Added `research/mesence/spritemine_frame_probe.lua`, a two-frame NES endFrame capture experiment for OAM (256 B), palette RAM (32 B), PPU pattern read space (8,192 B), and video-filtered RGB screen.
- Added `research/mesence/verify_capture.py` with strict filename, dimension, size and frame-identity validation, plus optional SMB3 PRG1 ROM SHA-256 confirmation. Never emits or commits captured pixel data.
- Lua syntax checking with stock Lua 5.4 and all synthetic validator tests passed on GitHub Actions; normal Python matrix passed too.
- **Still unverified:** any real MesenCE file export, exact memory mapping, screen-buffer/frame alignment, input replay, MMC3 bank provenance, and semantic Mario reconstruction. Lua I/O needs explicit user permission.
- Runtime instructions: `research/mesence/README.md`. This branch is experimental; do not merge into `main` as finished integration.

### Mocked Lua capture execution — verified 2026-11-09

GitHub Actions [run 42585418488](https://github.com/87otlto-coder/SpriteMine/actions/runs/42585418488) successfully executed the original Lua probe against a synthetic stand-in for MesenCE's Lua `emu` API, emitted two complete frame capture sets (100 and 101), and structurally validated the binary payloads and manifests. Seven independent Python validator tests also passed. The normal cross-platform tests passed separately. **This is software/mock validation, not an actual emulator observation.** The next required evidence is an on-device MesenCE capture and playback/snapshot comparison.
