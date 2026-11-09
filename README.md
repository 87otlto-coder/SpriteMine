# SpriteMine

**SMB3 first.** A local, Windows-first toolkit for investigating, reconstructing and exporting audiovisual assets from NES games. The first milestone targets **Super Mario Bros. 3 (US PRG1 / Revision A)**. This repository is a development workbench, not yet a desktop application.

## Current state — Phase 0 foundation

- Read-only `.nes` and single-ROM `.zip` input with iNES 1.0 validation, hashes, mapper, PRG/CHR boundaries and trainer handling.
- NES CHR-ROM 2bpp decoder; grayscale 8×8 tiles and 8 KiB bank atlas PNG export.
- Deterministic JSON manifest with ROM fingerprint, bank, tile offsets and PNG checksum.
- Pure synthetic tests and optional local SMB3 integration validation. ROMs are never checked into GitHub.
- **Not implemented:** desktop UI, live emulator capture, authentic runtime palettes, semantic sprites, animations, level reconstruction, and audio extraction.

The grayscale previews are **not authentic game palettes**. NES 2.0 parsing and CHR-RAM graphics capture are explicitly not supported yet.

## Windows setup (PowerShell)

Install Python 3.11+ and Git. The commands below clone into `$HOME\SpriteMine`; if you already have a clone, use your existing folder instead.

```powershell
Set-Location -Path $HOME
git clone https://github.com/87otlto-coder/SpriteMine.git "$HOME\SpriteMine"
Set-Location -Path "$HOME\SpriteMine"
git fetch origin
git switch feature/foundation-rom-chr
py -3.11 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
& ".\.venv\Scripts\python.exe" -m pytest -q
```

The `git switch` line is temporary until the foundation PR is merged into `main`.

To inspect a local, legally obtained ROM (replace the example path):

```powershell
Set-Location -Path "$HOME\SpriteMine"
& ".\.venv\Scripts\python.exe" -m spritemine inspect "C:\Games\Super Mario Bros. 3.zip"
& ".\.venv\Scripts\python.exe" -m spritemine chr-export "C:\Games\Super Mario Bros. 3.zip" --output "$HOME\SpriteMine-exports\smb3-chr"
```

Expected: JSON metadata, then 16 PNG bank images and `manifest.json` in the export folder for the verified SMB3 PRG1 ROM. To export one 8×8 tile: add `--tile 0`; to export a single bank: add `--bank 0`.

## Source ROM verification

Expected user-supplied SMB3 PRG1 `.nes` SHA-256: `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`; PRG CRC32 `A0ED7D20`, CHR CRC32 `C2928C49`. Never distribute the ROM or generated graphics.

## Project references

- [Instructions for development agents](AGENTS.md)
- [ChatGPT project instruction summary](docs/PROJECT_INSTRUCTIONS.md)
- [Current status](docs/PROJECT_STATUS.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture and provenance](docs/ARCHITECTURE.md)
- [Technical decisions](docs/DECISIONS.md)
- [Research log](docs/RESEARCH_LOG.md)
- [Validation procedures](docs/TESTING.md)

Development uses `feature/*` branches and PRs to `main`. Use `research/*` for experiments. See [CONTRIBUTING.md](CONTRIBUTING.md).
