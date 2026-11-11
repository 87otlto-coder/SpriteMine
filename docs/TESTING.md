# SpriteMine testing and validation

## Current merged foundation — local Windows tests

The production source checkout is F:\Dev\ROMMAGE\SOURCE\SpriteMine. Keep the verified ROM and all extracted game data under FIXTURE.

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\SOURCE\SpriteMine"
git fetch origin
git switch main
git pull --ff-only origin main
py -3.12 -m venv ".venv"
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" -m pytest -q
~~~

Python 3.11 is also supported. Synthetic tests validate ROM parsing, mapper and bank offsets, ZIP safety, error handling, NES 2.0/CHR-RAM unsupported cases, CHR bitplane decoding and deterministic manifests. No game ROM is needed in CI.

**GitHub Actions:** As of the November 11 incident mitigation, main Tests uses hosted Windows runners only, with Python 3.11 and 3.12. Do not add Ubuntu/Linux/macOS jobs without the owner's authorization. The workflow does not upload copyrighted assets or build archives.

## Optional local SMB3 PRG1 integration

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\SOURCE\SpriteMine"
$env:SPRITEMINE_TEST_ROM = "F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip"
if (-not (Test-Path -LiteralPath $env:SPRITEMINE_TEST_ROM)) {
    throw "Local verified SMB3 PRG1 ZIP missing."
}
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" -m pytest -q
Remove-Item Env:SPRITEMINE_TEST_ROM -ErrorAction SilentlyContinue
~~~

Expected known complete ROM ZIP SHA-256:
4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579.
PRG CRC32 A0ED7D20, CHR CRC32 C2928C49, combined CRC32 2E6301ED.
There are 16 CHR banks of 512 raw 8x8 tiles each. Public CI skips the opt-in private ROM test.

## Unmerged GUI and emulator research

Static GUI PR #4, MesenCE graphics proof PR #5 and stacked animation PR #6 each have separate tests and Windows owner-observed acceptance criteria; they are **not part of the main test suite until merged**.

The owner's private MesenCE slot-1 A/B/A harness reports full 16x16 background compositing agreement on three sampled Mario poses (256/256 for each), and the three-frame short timeline has one held pose across frames 448385–448387. These results require immutable private ROM, save state, emulator binary version, controller-latch history, frame/clock and source ROM/CHR mapping hashes. Preserve all raw evidence locally under FIXTURE.

Research workflow migration PR #9 passed hosted Windows Lua 5.4 and Python checks and merged into the research base. GUI compatibility PR #11 independently passed Windows Qt/Python checks. Synthetic CI cannot substitute for real MesenCE, and real MesenCE screenshots alone cannot establish complete decoded sprites or animations.

## Policy and acceptance

Follow docs/ACTIONS_INCIDENT_2026-11-11.md and AGENTS.md before changing or triggering hosted workflows. Never publish ROM data, capture buffers or private assets. Keep source hashes, decoder versions, offsets, MMC3 mapper state, frame/scanline indices, save-state SHA, emulator build and controller input history when evaluating real SMB3 output.

For unresolved cases (sprite priority, per-scanline CHR fetch, sprite limits, transparency behind moving backgrounds, complete animation durations, GUI interaction), mark them not tested or unsupported rather than implicitly passing them.


## PR #4 desktop feature — Windows Qt smoke and native acceptance

This branch adds a PySide6 GUI entrypoint and synthetic previews. Use the
existing canonical production checkout rather than cloning under HOME.

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\SOURCE\SpriteMine"
git fetch origin
git switch feature/static-chr-explorer
git pull --ff-only origin feature/static-chr-explorer

$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    py -3.12 -m venv ".venv"
}
& $python -m pip install -e ".[dev,gui]"
$env:QT_QPA_PLATFORM = "offscreen"
& $python -m pytest -q tests/test_preview.py tests/test_desktop.py
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
& $python -m spritemine.desktop
~~~

Expected: the headless Qt smoke tests pass; the last command opens the
interactive Windows CHR browser. Check bank 0 and 15, scrolling/zoom,
tile metadata and palette switching (synthetic colors only), tile/bank/all
export into new local FIXTURE output directories, deterministic manifests,
and explicit error handling for invalid ROMs. Record observations and
runtime versions before accepting GUI completion. Never publish screenshots
containing extracted game art in the public repository.
