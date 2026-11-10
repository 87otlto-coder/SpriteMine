# SpriteMine — MesenCE frame capture experiment

## Current next step (2026-11-10): Same-session pre-render PPU capture

**Goal:** Capture two startFrame/endFrame pairs with a complete 8,192-byte PPU pattern snapshot, 256 bytes OAM and 32 bytes palette data at each phase. Record MMC3 writes in the same session and compare reconstructed ROM-backed patterns to the *full* captured 8 KiB hash. The script produces 13 local files (four snapshots × three buffers, plus one metadata JSON) and refuses to overwrite existing evidence. This does not prove visible-scanline sprite rendering.

### A. Update the research checkout (PowerShell)

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility
New-Item -ItemType Directory -Path "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE" -Force | Out-Null
Test-Path -LiteralPath "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research\research\mesence\spritemine_phase_capture.lua"
~~~

Expected: True.

### B. Run the recorder in MesenCE

1. Load the verified SMB3 US PRG1 ROM, ideally with Mario visible in World 1-1.
2. In **Debug → Script Window**, stop the previous script with the square Stop button.
3. Select **File → Open** and open F:\Dev\ROMMAGE\TOOLS\SpriteMine-research\research\mesence\spritemine_phase_capture.lua (not any mock_ file).
4. In Script Window settings, enable **Allow access to I/O and OS functions** for this trusted script; leave network disabled.
5. Press **F5**, then let emulation advance two frames.

Expected log: **SpriteMine PHASE CAPTURE COMPLETE:** followed by the full JSON path and counts of four snapshots and MMC3 writes. If it says FAILED, preserve the log for diagnosis.

### C. Validate the precise new capture session

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"

$captureDir = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE"
$manifest = Get-ChildItem -LiteralPath $captureDir -Filter "phase_*.json" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName

if (-not $manifest) { throw "No phase capture report found in $captureDir" }

py -3.12 ".\research\mesence\verify_phase_capture.py" $manifest
~~~

Expected: pass_structural_phase_capture_validation, four snapshots, twelve binary files, and SHA-256 hashes. The ROM-backed model remains **not attempted** without the ROM.

For independent same-session MMC3 model verification, supply the actual path of the original ROM under FIXTURE:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
$romPath = "F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip"
# Change this example to the existing ROM's actual path if needed.
py -3.12 ".\research\mesence\verify_phase_capture.py" $manifest --rom $romPath
~~~

Expected if the mappings agree: mapper_model_status = matches_known_boundaries; the **first** startFrame may correctly have unknown mapping because its earlier register state was not observed. The **second** startFrame should be independently predictable from writes between the captured frames, if all six CHR bank registers were updated. A mismatch is a research finding, not a reason to replace the data.

Only share the resulting metadata JSON or Script Window log. Never commit the local ROM or binary captures to GitHub.

---

This is a **research toolkit, not a completed emulator adapter**. Real MesenCE/SMB3 endFrame capture, start/endFrame mapping comparison, and MMC3 register-write trace have now been observed and validated structurally. Exact rendering-scanline sprite reconstruction remains unproven. GitHub CI also validates synthetic file writing and modeling.

## Local organization

- Git research checkout: `F:\Dev\ROMMAGE\TOOLS\SpriteMine-research` (existing folder; do not clone another copy)
- MesenCE emulator: its existing installation inside `F:\Dev\ROMMAGE\TOOLS`
- Local ROM and saved states: `F:\Dev\ROMMAGE\FIXTURE`
- Frame capture destination: `F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE`
- Main SpriteMine application: `F:\Dev\ROMMAGE\SOURCE\SpriteMine`

Do not commit, upload or distribute original ROMs, emulator states, rendered images or captured game graphics. The Lua recorder has file-system access only after the user explicitly enables MesenCE's script I/O/OS setting. Network access is unnecessary.

## Step 1 — Prepare the local folder and latest recorder (PowerShell)

```powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility

$captureDir = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE"
New-Item -ItemType Directory -Force -Path $captureDir | Out-Null

Test-Path ".\research\mesence\spritemine_frame_probe.lua"
explorer.exe "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research\research\mesence"
```

Expected: `Test-Path` prints `True`; File Explorer opens the source folder. Captures will be written to `FIXTURE\SMB3\MesenCE`, not MesenCE's default Lua data directory. To override the default for an alternative setup, launch the emulator from a PowerShell process with `SPRITEMINE_CAPTURE_DIR` set before launch; routine use needs no override.

## Step 2 — Load the verified ROM in MesenCE

1. Launch the already-installed MesenCE from `TOOLS`. In its menu select **File → Open** and locate your existing SMB3 PRG1/Revision A ROM or ZIP in `FIXTURE`.
2. Start a one-player game and enter World 1-1. The game must be advancing when the script runs.
3. Open **Debug → Script Window** (the menu shown in your existing Windows screenshots; keyboard shortcut is Ctrl+N).
4. In **Debug → Settings**, locate the script execution permissions and enable **Allow access to I/O and OS functions**. **Leave network permissions disabled.** The precise configuration label can vary across builds; if you cannot find it, show the Settings screenshot rather than guessing.
5. In the Script Window, choose its Open command and select:
   `F:\Dev\ROMMAGE\TOOLS\SpriteMine-research\research\mesence\spritemine_frame_probe.lua`
6. Run the loaded script with **F5**. Let SMB3 advance for two frames.

Expected script log: `SpriteMine probe: capturing the next 2 endFrame events`, followed by `SpriteMine: captured frame ...` twice and a final "Captured 2 endFrame snapshots" notice. Failures may reveal API or permission incompatibility; preserve the script log for diagnosis.

## Step 3 — Inspect and validate the capture

Run this only **after** MesenCE prints the two capture messages:

```powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
$captureDir = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE"

Get-ChildItem -LiteralPath $captureDir | Sort-Object Name | Select-Object Name, Length
py -3.12 ".\research\mesence\verify_capture.py" $captureDir
```

Expected: **ten files** — two JSON manifests, two OAM snapshots (256 B each), two palette snapshots (32 B each), two PPU pattern snapshots (8,192 B each), two screen RGB buffers (size depends on the rendered screen). The validator should report `result: pass_structural_capture_validation` and `capture_count: 2`. Without a `--rom` argument, the report does **not** independently verify the identity of the ROM; the emulator's SHA-1 is still recorded. Use `--rom "<your local ROM ZIP path>"` when ready to verify the exact SMB3 PRG1 fixture.

If an older capture already exists in this folder, move it to a separate session folder before recording again. Otherwise the validator may count more than two frames. A repeated run at the same frame can overwrite capture files. Do not delete evidence until it is reviewed.

## Capture contract and limitations

Each `frame_XXXXXXXXXX.json` has four matching `.bin` files:
- `_oam.bin`: 64 × 4-byte hardware sprite entries
- `_palette.bin`: 32 palette bytes
- `_ppu_pattern.bin`: 8,192 effective PPU pattern bytes, **not** identified physical CHR-ROM banks
- `_screen_rgb.bin`: video-filtered RGB24 frame, row-major

Metadata records frame count, master clock, region, Mesen-reported ROM SHA-1, sprite height and optional scanline/cycle. The script has **not** been verified against a real emulator session. Structural validation does not prove atomic/same-frame capture, correct MMC3 bank offsets, hardware sprite visibility, or reproducible state replay.

## Upstream research sources

- [MesenCE Lua API](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/Debugger/LuaApi.cpp)
- [MesenCE file-I/O sandbox](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/Debugger/ScriptingContext.cpp)
- [Bundled Lua example](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/UI/Debugger/Utilities/LuaScripts/Example.lua)

## First real capture: useful follow-up

The supplied frame 29276/29277 ZIP passed `verify_capture.py` with the authentic SMB3 PRG1 ROM. **However, its 8×16 sprite OAM references the upper PPU pattern bank, which is entirely zero at the endFrame capture point.** This is not yet a valid transparent Mario reconstruction source. Do not automatically export it as a confirmed character sprite.

After pulling the latest research branch, inspect a capture directory locally with:

```powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
py -3.12 ".\research\mesence\diagnose_capture.py" "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE"
```

This prints **derived metadata only**, including potential on-screen hardware sprite entries and any blank captured tile sources. The next research experiment will test rendering-time mapper state, not another identical endFrame snapshot.

## Next experiment — startFrame vs endFrame pattern bank comparison

The first real SMB3 capture was structurally valid, but its two 8×16 Mario-position OAM entries selected the upper pattern table while the endFrame upper table was entirely zero. A mapper bank change between visible rendering and VBlank is a hypothesis, not a confirmed cause.

The targeted follow-up script is research/mesence/spritemine_mapping_probe.lua. It reads **derived counts only** for lower/upper 4 KiB PPU pattern regions, plus the number of potential on-screen OAM entries with odd 8×16 tile IDs. It samples two startFrame / endFrame callback pairs and saves a small JSON file in the same FIXTURE directory. No game imagery is written by this diagnostic script.

First refresh the research checkout:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility
Test-Path ".\research\mesence\spritemine_mapping_probe.lua"
~~~

Expected: the final command prints True. In MesenCE, keep the verified SMB3 ROM running in World 1-1, open **Debug → Script Window**, stop the older capture script if still active (square Stop icon), then **File → Open** the new spritemine_mapping_probe.lua and press **F5**. With I/O/OS access enabled and network access still disabled, two log summaries should appear. The last line prints the path to a mapping_probe_*.json file.

To locate this metadata file:

~~~powershell
Get-ChildItem -Path "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE" -Filter "mapping_probe_*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 3 FullName, Length, LastWriteTime
~~~

You may share the **JSON metadata** or Script Window log for further diagnosis; do not upload ROMs or extracted graphics to public GitHub.

**Interpretation:** If the upper 4 KiB is populated at startFrame but blank at endFrame, phase-dependent mapping is demonstrated. If both are blank, the mapping could change during visible scanlines, or Mesen's debug read could be unsuitable. Either result is useful, but neither alone establishes exactly which physical CHR bank supplied Mario's rendered pixels. Test remains research-only.

## Confirmed start/end phase result — 2026-11-09

The actual MesenCE metadata captured by the owner for frames 136117/136118 shows upper PPU nonzero bytes **2991 at startFrame** versus **0 at endFrame**. All five potentially on-screen OAM entries with odd 8×16 tile IDs reference nonblank patterns at start and blank patterns at end. This confirms phase-sensitive debugger-visible PPU pattern data in SMB3. It does **not** yet identify physical CHR-ROM bank IDs or prove whether mapper writes happen inside visible scanlines. Do not substitute pre-render snapshots for scanline-accurate game asset provenance without further testing.

## Next on-device experiment — MMC3 register writes

**Motivation:** Real frames 136117/136118 have upper PPU pattern nonzero counts **2991 at startFrame → 0 at endFrame**, for two consecutive frames. Five potentially on-screen odd 8×16 sprite patterns are nonblank at start and blank at end. This establishes phase-dependent mapped content, not its cause.

New script: `research/mesence/spritemine_mmc3_trace.lua`. It records *only* metadata for **CPU writes to MMC3 bank-select/data range $8000–$9FFF**, plus frame/scanline/cycle and pre-write register values, for two complete frame intervals. A hard limit of 128 writes prevents runaway logging. The callback is invoked **before** the write takes effect, so the script does not claim an observed post-write bank state. Writes during VBlank outside the sampled intervals may be missed.

Refresh the existing research checkout:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility
Test-Path ".\research\mesence\spritemine_mmc3_trace.lua"
~~~

Expected: `True`. In MesenCE, stop the previous Lua script (square Stop button in **Debug → Script Window**). Choose **File → Open**, select `F:\Dev\ROMMAGE\TOOLS\SpriteMine-research\research\mesence\spritemine_mmc3_trace.lua`, then press **F5** while SMB3 is playing. The script will log `SpriteMine MMC3 trace COMPLETE` and the location of a small `mmc3_trace_*.json` file within `F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE`.

To locate the newest report:

~~~powershell
Get-ChildItem -Path "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE" -Filter "mmc3_trace_*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 FullName, Length, LastWriteTime
~~~

Share the JSON metadata report or error log, not the underlying ROM or captured screen bytes. Its timestamps may show when bank-select/data writes occur during active scanlines; further tests will be required to link those writes to exact physical CHR-ROM sources and sprite pixel output. This is research instrumentation, not the final live Sprite Inspector.

## Reproduce physical CHR-ROM bank correlation (optional advanced check)

Use the owner's immutable SMB3 PRG1 ROM/ZIP, the earlier extracted `frame_0000029277_ppu_pattern.bin`, and the metadata-only trace `mmc3_trace_0000189263_1794256680.json`. These inputs remain inside `FIXTURE` and must never be committed to GitHub.

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility

& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" ".\research\mesence\correlate_chr_banks.py" `
    --rom "F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip" `
    --pattern "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\frame_0000029277_ppu_pattern.bin" `
    --trace "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\mmc3_trace_0000189263_1794256680.json"
~~~

**Adapt the three input paths to the actual file locations.** The correlation tool requires the editable `spritemine` package in the Python environment; if necessary install the main checkout with `-e ".[dev]"` first. Expected metadata: eight uniquely matched windows `[92,93,94,95,126,126,126,126]` and a matching modeled layout at scanline 193, reproduced in two frames. The tool prints no copyrighted ROM bytes or images. The trace and snapshot come from different gameplay intervals, so agreement validates a repeated mapper configuration, not synchronization.

## Optional full SMB3 provenance regression

After placing the original ROM, prior extracted PPU pattern snapshot and metadata trace under `FIXTURE` and setting your three environment variables, run the research tests locally:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
$env:SPRITEMINE_TEST_ROM = "F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip"
$env:SPRITEMINE_CAPTURE_PPU_PATTERN = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\frame_0000029277_ppu_pattern.bin"
$env:SPRITEMINE_CAPTURE_MMC3_TRACE = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\mmc3_trace_0000189263_1794256680.json"
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" -m pytest -q tests/test_chr_bank_correlation.py
Remove-Item Env:SPRITEMINE_TEST_ROM, Env:SPRITEMINE_CAPTURE_PPU_PATTERN, Env:SPRITEMINE_CAPTURE_MMC3_TRACE -ErrorAction SilentlyContinue
~~~

Adjust the fixture paths to their actual local locations and ensure the Python environment has both SpriteMine and pytest installed. This opt-in test confirms the cross-session mapping pattern and SHA-1; it is intentionally skipped in GitHub CI because raw game files are private.

## ROM-backed MMC3 mapping decoder (read-only)

Two related research utilities serve different purposes:

- correlate_chr_banks.py: given a local ROM, a **raw 8192-byte captured PPU pattern file**, and MMC3 trace, match each captured 1 KiB PPU slot to its physical CHR-ROM bank; report ambiguity when multiple physical banks contain identical data.
- decode_mmc3_trace.py: given a local SMB3 ROM and a trace JSON, model all **known** MMC3 CHR register values at each observed frame boundary, list eight physical bank indexes and exact ROM offsets, and compute the expected full PPU pattern SHA-256. Optionally compare private capture ZIP PPU snapshots by hash. It does not output any graphics bytes and refuses guesses before all six CHR registers have been observed.

**Verified result:** modeled endFrame 8 KiB PPU SHA-256 = 0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918, exactly matching the private captures for frames 29276 and 29277. The predicted startFrame PPU SHA-256 = ff1fed9ebea0ff45c17ae1ddb93bf3205ee591438cc8d45af83167a80d4f69b5; a byte-for-byte independent startFrame capture still needs to be performed.

See docs/research/MMC3_CHR_MAPPING_VERIFICATION.md for the source table and complete evidence. Full provenance is confined to local FIXTURE paths.
