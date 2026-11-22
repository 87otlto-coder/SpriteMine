# SpriteMine — Creative Asset Workbench

**Project direction changed 2026-11-22.** SpriteMine is a **Windows-first creative toolkit for browsing, extracting/capturing, compiling, animating and exporting** visual and audio assets from classic games. The first and only active target is **Super Mario Bros. 3 (US PRG1 / Revision A)**.

**We are building usable wallpapers, stage GIFs, sprites and audio — not reverse engineering the game exhaustively.** Source-accurate ROM research supports creative output only when necessary.

**Milestone 1 owner revision (2026-11-22):** The 48-frame World 1-1-inspired GIF in PR #27 is only a prototype. Acceptance now requires the **entire main World 1-1 as one coherent full-width AND full-height two-dimensional scene** (nominal 176×27 metatiles / 2,816×432 native pixels; verify vertical world/scroll coordinates and HUD separation), correct art/crops/palettes/positions, then coherent independently animated objects. Mario absent by default or only one; **enemies last**, reusing existing `W101O` research. See [full-level M1 acceptance](docs/creative/SMB3_WORLD11_FULL_LEVEL_M1_ACCEPTANCE.md). Work headlessly with contact sheets/CLI/JSON recipes and inspect the real GIF before starting the audio milestone. **The desktop interface follows the proven headless creative workflows**, rather than preceding them.

**For every new development chat, read:** [AGENTS.md](AGENTS.md) → [product mission](docs/PRODUCT_DIRECTION.md) → [creative milestones](docs/ROADMAP.md) → [status](docs/PROJECT_STATUS.md). This 2026-11-22 decision **supersedes old research-first and full-level-decoding-first instructions** in historical research PRs and discussions.

## Current production milestones

| Order | Output | Status |
| --- | --- | --- |
| 1 | **Compiled World 1-1 stage GIF**, seamless loop, ≥2 independently animated objects, editable composition recipe | **Active; not yet delivered** |
| 2 | Playable **music loop + SFX WAV** outputs, trim/loop/provenance | Pending after M1 |
| 3 | Browseable/reusable asset projects and further animation/wallpaper exports | Pending |
| 4 | Usable **Windows PySide6** creative app over working pipelines | Pending |

**Completion is measured by actual playable/visible/audible exports and QA, not by tests, emulator internals understood, or number of decoded game mechanics.**

## What is actually on main

The currently merged foundation provides:

- Read-only .nes and single-ROM .zip import with iNES 1.0 parsing, verified fingerprints, mapper and bank offsets.
- NES 2bpp CHR-ROM tile decoding and deterministic grayscale PNG exports for 8x8 tiles and 8 KiB banks.
- Source provenance, JSON manifests, CLI and synthetic regression tests.

**Not yet integrated into main:** PySide6 static CHR browser (PR #4), MesenCE graphics research harness (PR #5, merged into the research base; not integrated into main), contiguous animation timeline (PR #6, merged into research; not main), complete Sprite Inspector, level decoding, audio workbench, asset catalog and Windows installer. These features must not be presented as merged merely because they work on research branches.

## Historical research evidence (reusable, not the roadmap)

Research PR #5 documents three real SMB3 MesenCE slot-1 A/B/A replay samples, each with the complete 16x16 Mario region matched against the default 2C02 palette and an independent sprites-disabled background (256/256 pixels for standing, walking-right and rising jump). These **three sampled poses** are not exhaustive actor coverage.

Research PR #6 documents a consecutive three-frame capture (emulator frames 448385–448387). All three local sprite images were identical; it verified a three-video-frame **visual hold**, not a completed walking animation cycle. A longer sequence is the next Phase 4 research gate.

These findings require local, licensed game data. Original ROMs, save states, screen buffers and extracted graphics must never be committed to GitHub.

**Latest accepted research outside `main`:** stacked draft [PRs #21–#25](https://github.com/87otlto-coder/SpriteMine/pull/25) have validated selected player/World 1-1 bonus-room structures. At PR #25 implementation commit `a462499`, owner Windows testing reported **61 passed** and a successful **13-frame × 256×192 = 638,976-pixel native bonus-background RGB match** with zero mismatches. These are genuine but **narrow research results**, not a finished GIF or an integrated application. Reuse their components selectively for M1 instead of repeating CPU/PPU investigations. See [technical acceptance](https://github.com/87otlto-coder/SpriteMine/blob/feature/smb3-world11-visible-background/docs/research/SMB3_VISIBLE_BACKGROUND_NATIVE_GATE.md).

## Windows development workspace

Canonical project root is F:\Dev\ROMMAGE:

- SOURCE — Git repositories, SpriteMine package, development code and documentation.
- TOOLS — MesenCE emulator and supporting research utilities.
- FIXTURE — immutable ROMs, save states, frame captures and private validation evidence.
- OUTPUT — generated GIFs, wallpapers, audio, contact sheets and editable creative projects.
- REPORTS — local output-quality checks, asset inventories and reproducibility summaries.

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
- [MesenCE graphics harness PR #5](https://github.com/87otlto-coder/SpriteMine/pull/5) — merged into research/smb3-emulator-feasibility (not main).
- [Animation timeline PR #6](https://github.com/87otlto-coder/SpriteMine/pull/6) — merged into research/smb3-emulator-feasibility (not main); the three-frame hold is verified, but a complete walk cycle is not.
- [Research Windows CI migration PR #9](https://github.com/87otlto-coder/SpriteMine/pull/9) — merged into research base; Windows Python 3.11/3.12 and Lua 5.4.8 probes passed. GUI CI maintenance PR #11 also merged into the GUI branch.

GitHub Actions policy is **Windows-only** following the 11 November incident. New code and workflows should be reviewed with [AGENTS.md](AGENTS.md) and [the incident document](docs/ACTIONS_INCIDENT_2026-11-11.md). The main Tests workflow currently uses Windows with Python 3.11/3.12 and performs no artifact uploads.

## Further reading

- [Project status](docs/PROJECT_STATUS.md)
- [Roadmap and acceptance criteria](docs/ROADMAP.md)
- [Architecture and evidence classes](docs/ARCHITECTURE.md)
- [Windows testing guidance](docs/TESTING.md)
- [Research log](docs/RESEARCH_LOG.md)
- [Engineering instructions](AGENTS.md)
- [Current creative product direction](docs/PRODUCT_DIRECTION.md)
- [Milestone 1 animated stage GIF plan](docs/ROADMAP.md)
