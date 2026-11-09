# SpriteMine

**SMB3 first.** A local, Windows-first toolkit for investigating, reconstructing and exporting audiovisual assets from NES games. The first milestone targets **Super Mario Bros. 3 (US PRG1 / Revision A)**. The desktop explorer is an early static-only prototype.

## Current capabilities

- Read-only `.nes` and single-ROM `.zip` input with iNES 1.0 validation, hashes, mapper, PRG/CHR boundaries and trainer handling.
- NES CHR-ROM 2bpp decoding, grayscale 8×8 tiles, 8 KiB bank atlas PNG export.
- Deterministic JSON manifest with ROM fingerprint, CHR/ROM offsets, bank and tile indices, PNG checksums.
- **Experimental PySide6 desktop explorer** on `feature/static-chr-explorer`: scrollable CHR atlas, tile picker, bank selection, pixel-perfect zoom, synthetic palette previews, source offsets, grayscale exports.
- Synthetic unit tests, opt-in local SMB3 validation, and Windows/Ubuntu CI.

**Important:** Static CHR bytes do not include the original NES palette assignments or semantic sprite identities. Synthetic preview colors are not authentic SMB3 colors. NES 2.0 and CHR-RAM static extraction are currently unsupported. Runtime capture, character reconstruction, animations, levels and audio are future milestones.

## Windows installation (PowerShell)

Install Python 3.12 and Git, then use the commands below. Python 3.11 is also supported; the example uses 3.12 because the Windows setup was validated with that version. To list installed Python runtimes, run `py -0p`:

```powershell
Set-Location -Path $HOME
git clone https://github.com/87otlto-coder/SpriteMine.git "$HOME\SpriteMine"
Set-Location -Path "$HOME\SpriteMine"
git fetch origin
git switch feature/static-chr-explorer
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev,gui]"
& ".\.venv\Scripts\python.exe" -m pytest -q
& ".\.venv\Scripts\python.exe" -m spritemine.desktop
```

Expected: a SpriteMine window with a ROM/ZIP Open command, CHR atlas, controls and tile inspection panel. This is a **prototype**, not a packaged installer. The `git switch` step is temporary until the desktop explorer PR is merged.

To verify the command-line extractor, replace the example ROM path with your locally stored, legally obtained file:

```powershell
Set-Location -Path "$HOME\SpriteMine"
& ".\.venv\Scripts\python.exe" -m spritemine inspect "C:\Games\Super Mario Bros. 3.zip"
& ".\.venv\Scripts\python.exe" -m spritemine chr-export "C:\Games\Super Mario Bros. 3.zip" --output "$HOME\SpriteMine-exports\smb3-chr"
```

Expected: JSON metadata and 16 PNG bank previews plus `manifest.json` for the verified ROM. For a single bank add `--bank 0`; for a tile add `--tile 0`. Reusing an output directory overwrites its `manifest.json`.

## Primary ROM verification

The known user-supplied SMB3 PRG1 ROM has SHA-256:
`4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`.
PRG CRC32: `A0ED7D20`; CHR CRC32: `C2928C49`.
Do not commit the ROM, emulator states, or generated copyrighted assets.

## Project documentation

- [Developer/agent instructions](AGENTS.md)
- [ChatGPT Project Instructions summary](docs/PROJECT_INSTRUCTIONS.md)
- [Live status](docs/PROJECT_STATUS.md)
- [Roadmap](docs/ROADMAP.md)
- [Architecture and provenance](docs/ARCHITECTURE.md)
- [Technical decisions](docs/DECISIONS.md)
- [Research log](docs/RESEARCH_LOG.md)
- [Testing and Windows validation](docs/TESTING.md)

Use `feature/*` development branches, `research/*` experiments, and pull requests to `main`. Read [CONTRIBUTING.md](CONTRIBUTING.md).
