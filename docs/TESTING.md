# Testing and validation

## Automated Python tests (no copyrighted ROM required)

Commands below use Python 3.12. Python 3.11 is also supported; check installed runtimes with `py -0p` before creating a virtual environment.

```powershell
Set-Location -Path "$HOME\SpriteMine"
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev,gui]"
& ".\.venv\Scripts\python.exe" -m pytest -q
```

The synthetic tests cover header parsing, trainer/mapper math, ZIP safety, unsupported formats, CHR bitplane order, atlas dimensions, manifest determinism, synthetic preview colors, and optional offscreen Qt widget smoke tests.

GitHub Actions runs normal Python tests on Python 3.11/3.12 on Windows and Ubuntu. The desktop feature adds a dedicated Qt smoke job on both OSes with `QT_QPA_PLATFORM=offscreen`. **Passing headless Qt smoke tests is not evidence of an actual interactive Windows desktop validation.**

## Optional local SMB3 integration test

Never commit this ROM. Set a path to the owner's verified SMB3 ZIP or .nes, and run:

```powershell
Set-Location -Path "$HOME\SpriteMine"
$env:SPRITEMINE_TEST_ROM = 'C:\Games\Super Mario Bros. 3.zip'
& ".\.venv\Scripts\python.exe" -m pytest -q
Remove-Item Env:SPRITEMINE_TEST_ROM
```

Expected ROM SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`; PRG/CHR CRC32 `A0ED7D20`/`C2928C49`. This input is omitted from CI.

## Interactive Windows UI validation (pending)

```powershell
Set-Location -Path "$HOME\SpriteMine"
git fetch origin
git switch feature/static-chr-explorer
& ".\.venv\Scripts\python.exe" -m spritemine.desktop
```

Checklist:
- Open locally stored SMB3 ZIP; title identifies verified revision.
- Switch bank 0 to 15; atlas displays 512 tiles per bank and supports scrolling/zooming.
- Click a tile; inspect matching bank/local index and ROM byte offset.
- Switch synthetic palettes; confirm previews change, and note these are not game-authentic colors.
- Export one tile, one bank and all banks into separate directories; inspect PNGs and `manifest.json`.
- Open an invalid ROM; confirm readable error rather than crashing.
- Record any visual issues, Qt errors, or missing functionality with Windows/Python/PySide6 versions.

## Later emulator validation (not attempted)

Record exact MesenCE revision, ROM hash, emulator state, controller inputs, frame/scanline, mapping, and screenshot. CI cannot establish OAM/CHR/palette synchronization or sprite/animation correctness.
