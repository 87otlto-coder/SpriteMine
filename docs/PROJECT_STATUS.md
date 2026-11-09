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

## Local environment alignment — 2026-11-09

The owner confirmed `F:\Dev\ROMMAGE\SOURCE\SpriteMine` was refreshed successfully, and `F:\Dev\ROMMAGE\TOOLS\SpriteMine-research` already holds the up-to-date research branch. MesenCE is installed in `TOOLS`. The Lua probe now defaults to `F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE` for local capture output (the folder must exist). CI uses `SPRITEMINE_CAPTURE_DIR` to override the path. No real emulator captures have been verified yet. See `research/mesence/README.md`.

## 2026-11-09 — Real SMB3 capture received and structurally verified

The owner provided a MesenCE capture ZIP with **two real SMB3 PRG1 frames** (29276–29277, 10 files). The Python structural validator passed and ROM SHA-1/SHA-256 identities match the locally supplied verified ROM. This completes the first *real capture creation and file-integrity* gate, **not** the synchronization or sprite-reconstruction gate.

Important: OAM shows two potentially on-screen 8×16 entries corresponding spatially to Mario; their odd tile IDs select PPU `0x1000–0x1FFF` in 8×16 mode. The captured upper pattern table contains only zero bytes. The endFrame snapshot **cannot reconstruct these visible Mario tiles**. Hypotheses: a different MMC3 CHR bank mapping at the rendering scanline, or unexpected debug read behavior. Neither is confirmed. Screen buffers change by 3 pixels while OAM/palette/pattern snapshots remain identical. The next task is a time-separated PPU mapping experiment. See `docs/RESEARCH_LOG.md`.

Only metadata findings are stored in GitHub. All game asset bytes remain out of the repository.
