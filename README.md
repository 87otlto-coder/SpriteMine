# SpriteMine

**SMB3 first.** SpriteMine is a Windows-first tool for inspecting, reconstructing, and eventually exporting audiovisual resources from **Super Mario Bros. 3 (US PRG1 / Revision A)**. The project is still under active development; the integrated desktop milestone is not finished.

## What is actually on main

The currently merged foundation provides:

- Read-only .nes and single-ROM .zip import with iNES 1.0 parsing, verified fingerprints, mapper and bank offsets.
- NES 2bpp CHR-ROM tile decoding and deterministic grayscale PNG exports for 8x8 tiles and 8 KiB banks.
- Source provenance, JSON manifests, CLI and synthetic regression tests.

**Not yet integrated into main:** PySide6 static CHR browser (PR #4), MesenCE graphics research harness (PR #5, merged into the research base; not integrated into main), contiguous animation timeline (PR #6, merged into research; not main), complete Sprite Inspector, level decoding, audio workbench, asset catalog and Windows installer. These features must not be presented as merged merely because they work on research branches.

## Research that has already been validated

Research PR #5 documents three real SMB3 MesenCE slot-1 A/B/A replay samples, each with the complete 16x16 Mario region matched against the default 2C02 palette and an independent sprites-disabled background (256/256 pixels for standing, walking-right and rising jump). These **three sampled poses** are not exhaustive actor coverage.

Research PR #6 documents a consecutive three-frame capture (emulator frames 448385–448387). All three local sprite images were identical; it verified a three-video-frame **visual hold**, not a completed walking animation cycle. A longer sequence is the next Phase 4 research gate.

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

## Current headless development branches (2026-11-22)

**This section describes tested but unmerged feature branches, not `main`.** [Draft PR #21](https://github.com/87otlto-coder/SpriteMine/pull/21) includes 81 player recipes, three canonical Mario poses, a 24-frame native replay, 7,528 distinguishable authentic pipe-mask pixel comparisons with zero mismatches, and the native-validated 864-byte logical World 1-1 first-entry bonus map. These are selected samples, not complete game coverage.

The stacked [PR #22](https://github.com/87otlto-coder/SpriteMine/pull/22) models Plains patterns and attributes from the ROM; [PR #23](https://github.com/87otlto-coder/SpriteMine/pull/23) validates **2,176/2,176 native CPU staging bytes**; and [PR #24](https://github.com/87otlto-coder/SpriteMine/pull/24) has passed the owner's private Windows **physical PPU/CIRAM verification** over 104 frames and 5,491 nametable write requests with zero mismatches.

[PR #25](https://github.com/87otlto-coder/SpriteMine/pull/25) reconstructs the **World 1-1 bonus gameplay background** from the original ROM CHR, MMC3 register-derived bank mapping, physical CIRAM, scroll and palette. The owner's Windows PowerShell 5.1 test at commit `a462499` passed **61 private-ROM regression tests**, then the official offline verifier reported **`passed: true`, 13 frames × 256×192 pixels = 638,976 exact native RGB matches, zero differences**. It reuses the original deterministic MesenCE capture; no additional emulator session or patched ROM was required. See [acceptance and limitations](docs/research/SMB3_VISIBLE_BACKGROUND_NATIVE_GATE.md).

**Still out of scope:** status bar (scanlines 192–239), full rendered sprite/background compositing, all World 1-1 areas, general asset identity, audio and a complete integrated Windows UI. The existing PySide6 static CHR explorer [PR #4](https://github.com/87otlto-coder/SpriteMine/pull/4) also remains unmerged pending further native QA. Keep copyrighted game contents and MesenCE GPL-source material outside the public repository. The [integration plan](docs/RENDERING_INTEGRATION_PLAN.md) describes the safe review and merge sequence.
