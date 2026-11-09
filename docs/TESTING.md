# Testing and validation

## Automated tests (no game ROM required)

From PowerShell after cloning and switching to the development branch:

```powershell
Set-Location -Path "$HOME\SpriteMine"
py -3.11 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
& ".\.venv\Scripts\python.exe" -m pytest -q
```

These tests cover header parsing, mapper/offset math, invalid inputs, ZIP handling without extraction, NES 2.0 rejection, CHR-RAM handling, bitplane order, atlas size, deterministic manifest, and CLI error handling. CI is configured for Windows and Ubuntu with Python 3.11 and 3.12.

## Optional real SMB3 integration

Do **not** commit the ROM. Set an environment variable to the locally stored user-provided ROM or ZIP:

```powershell
Set-Location -Path "$HOME\SpriteMine"
$env:SPRITEMINE_TEST_ROM = 'C:\Games\Super Mario Bros. 3.zip'
& ".\.venv\Scripts\python.exe" -m pytest -q
Remove-Item Env:SPRITEMINE_TEST_ROM
```

Expected ROM SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`; PRG CRC32 `A0ED7D20`, CHR CRC32 `C2928C49`, combined CRC32 `2E6301ED`. There are 16 banks of 512 8×8 tiles. The integration test is skipped in public/remote CI unless the environment variable is set.

## Real Windows/emulator validation (pending)

Do not assert that Python tests validate MesenCE OAM, MMC3 scanline mapping, palette fidelity, transparent sprite rendering or GUI behavior. Record emulator build/version, ROM checksum, state/input sequence, and screenshots when this phase begins; keep all copyrighted data outside the repo.
