# SpriteMine

**SMB3 first.** SpriteMine is a Windows-first tool for inspecting, reconstructing, and eventually exporting audiovisual resources from **Super Mario Bros. 3 (US PRG1 / Revision A)**. The project is still under active development; the integrated desktop milestone is not finished.

## What is actually on main

The currently merged foundation provides:

- Read-only .nes and single-ROM .zip import with iNES 1.0 parsing, verified fingerprints, mapper and bank offsets.
- NES 2bpp CHR-ROM tile decoding and deterministic grayscale PNG exports for 8x8 tiles and 8 KiB banks.
- Source provenance, JSON manifests, CLI and synthetic regression tests.

**Not yet integrated into main:** PySide6 static CHR browser (PR #4), MesenCE graphics research harness (PR #5), contiguous animation timeline (draft PR #6), complete Sprite Inspector, level decoding, audio workbench, asset catalog and Windows installer. These features must not be presented as merged merely because they work on research branches.

## Research that has already been validated

Research PR #5 documents three real SMB3 MesenCE slot-1 A/B/A replay samples, each with the complete 16x16 Mario region matched against the default 2C02 palette and an independent sprites-disabled background (256/256 pixels for standing, walking-right and rising jump). These **three sampled poses** are not exhaustive actor coverage.

Draft PR #6 documents a consecutive three-frame capture (emulator frames 448385–448387). All three local sprite images were identical; it verified a three-video-frame **visual hold**, not a completed walking animation cycle. A longer sequence is the next Phase 4 research gate.

These findings require local, licensed game data. Original ROMs, save states, screen buffers and extracted graphics must never be committed to GitHub.

## Windows development workspace

Canonical project root is F:\Dev\ROMMAGE:

- SOURCE — Git repositories, SpriteMine package, development code and documentation.
- TOOLS — MesenCE emulator and supporting research utilities.
- FIXTURE — immutable ROMs, save states, frame captures, validation evidence and generated game-asset previews.

Primary production checkout: F:\Dev\ROMMAGE\SOURCE\SpriteMine. The owner also uses separate research checkouts; their branch and path are explicitly documented in the applicable research runbook.

### Install/test the merged foundation (PowerShell)

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\SOURCE\SpriteMine"
git fetch origin
git switch main
git pull --ff-only origin main

py -3.12 -m venv ".venv"
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" -m pytest -q
~~~

The code requires Python 3.11 or newer. If your environment already uses Python 3.11, its supported interpreter can be used instead of 3.12.

### Inspect the verified local SMB3 ROM

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\SOURCE\SpriteMine"
$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe"
$rom = "F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip"
if (-not (Test-Path -LiteralPath $rom)) { throw "ROM ZIP missing at expected FIXTURE path." }

& $python -m spritemine inspect $rom
& $python -m spritemine chr-export $rom --output "F:\Dev\ROMMAGE\FIXTURE\SMB3\Exports\CHR"
~~~

Expected for the verified SMB3 PRG1 ROM: 256 KiB PRG, 128 KiB CHR, mapper 4; 16 grayscale CHR-bank PNGs comprising 8,192 raw tiles and a manifest with offsets and hashes. This does not reconstruct complete characters automatically.

Expected complete ZIP SHA-256: 4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579. The tool does not alter the source.

## Branches and review

- [Foundation PR #1](https://github.com/87otlto-coder/SpriteMine/pull/1) — merged into main.
- [Static CHR explorer PR #4](https://github.com/87otlto-coder/SpriteMine/pull/4) — open against main.
- [MesenCE graphics harness PR #5](https://github.com/87otlto-coder/SpriteMine/pull/5) — open on research/smb3-emulator-feasibility.
- [Animation timeline draft PR #6](https://github.com/87otlto-coder/SpriteMine/pull/6) — stacked on PR #5.
- [Research Windows CI migration PR #9](https://github.com/87otlto-coder/SpriteMine/pull/9) — merged into the research base after hosted Windows Python/Lua validation.

GitHub Actions policy is **Windows-only** following the 11 November incident. New code and workflows should be reviewed with [AGENTS.md](AGENTS.md) and [the incident document](docs/ACTIONS_INCIDENT_2026-11-11.md). The main Tests workflow currently uses Windows with Python 3.11/3.12 and performs no artifact uploads.

## Further reading

- [Project status](docs/PROJECT_STATUS.md)
- [Roadmap and acceptance criteria](docs/ROADMAP.md)
- [Architecture and evidence classes](docs/ARCHITECTURE.md)
- [Windows testing guidance](docs/TESTING.md)
- [Research log](docs/RESEARCH_LOG.md)
- [Engineering instructions](AGENTS.md)


## Static CHR desktop prototype on feature/static-chr-explorer

**This branch adds the pending PySide6 PR #4; it is not the fully integrated release.**
Its UI offers verified-ROM opening, scrollable 16x32 CHR bank atlas, 1–8x
pixel-accurate zoom, tile provenance inspection, and explicitly synthetic
grayscale/green/amber preview palettes. Raw tile and bank exports remain
grayscale with manifests.

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\SOURCE\SpriteMine"
git fetch origin
git switch feature/static-chr-explorer
git pull --ff-only origin feature/static-chr-explorer
py -3.12 -m venv ".venv"
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" -m pip install -e ".[dev,gui]"
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" -m spritemine.desktop
~~~

Expected: a PySide6 CHR browser window. No production installer, original
in-game palette assignments or semantic character labels are claimed.
The native Windows interactive acceptance still needs bank 15/palette/export/
invalid-ROM tests; see docs/TESTING.md.
