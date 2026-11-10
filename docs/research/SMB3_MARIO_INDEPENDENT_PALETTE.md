# SMB3 frame 450824 — default-palette RGB evidence and transparency boundary

Date: 2026-11-10. Scope: SMB3 US PRG1 only. This document records **derived metadata**, not copyrighted game graphics or ROM bytes.

## Source evidence

Owner-supplied private files:
- render_0000450823_1794339466.json, MesenCE versioned render probe, frames 450823 and 450824
- screencheck_render_0000450823_1794339466.json, metadata-only analyzer result

ROM SHA-256: 4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579 (verified SMB3 US PRG1).
Render frame RGB SHA-256: 78e49771babc3ab3193e15d46c856d6e56a53627b9b9e53adfb471ea6e610f9d, native 256×240 RGB24.
Second startFrame PPU SHA-256: e5b13a28c78d277bad5d2846fe2275eb973ca8fded35ebeadea3335274dbcdf2.
Reported physical CHR mapping verification: true. OAM and palette RAM SHA-256 unchanged from start to end of rendered frame; no tracked MMC3 CHR bank changes before candidate object's lower row.

At frame **450824**, candidate hardware OAM entries #10/#11 occupy X=128 and X=136, Y=162, each 8×16. This yields a 16×16 bounding region with **138 predicted opaque pixel positions** and **118 source-transparent positions**. Its source tile ROM offsets are 347248/347264 and 347216/347232.

## Independent source RGB reference

MesenCE Core/NES/NesDefaultVideoFilter.cpp, upstream commit 4b8a196e299b3de297b204fd1208d2981562c89b, declares its built-in **2C02 default NES palette** with these entries:

| NES code | Built-in default 2C02 RGB | RGB inferred by the older screen-only analyzer | Reported pixels |
|---|---|---|---|
| 0x16 | #B53120 | #B53120 | 37 |
| 0x36 | #FECCC5 | #FECCC5 | 31 |
| 0x0F | #000000 | #000000 | 70 |

MesenCE source: https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/NES/NesDefaultVideoFilter.cpp

These three exact RGB matches are **independent of fitted-screen color estimation** at the palette lookup level. Their expected **NES palette RAM codes in this particular rendered session have not yet been independently read into the uploaded screencheck JSON**. The saved local binary palette RAM buffer must be checked. Earlier SMB3 Mario gameplay captures used codes 0x16,0x36,0x0F, but do not silently assume unchanged code values across sessions.

MesenCE supports custom palettes, color-emphasis/grayscale effects and video hue/saturation/brightness/contrast, so this built-in palette is not universally identical to all renderer configurations. The observed exact source RGB is strong supporting evidence for an unmodified palette in the captured screen, not a capture of the emulator's configuration settings.

## Screen-only alignment result already verified

At registered OAM coordinates: 138 of 138 predicted nontransparent pixel positions had the modal RGB of their own palette index (per-class 37/37, 31/31, 70/70), modal consistency **1.000000**.

One-pixel displacement controls: horizontal ±1 yielded 81/138 (~0.586957) and vertical -1 yielded 56/138 (~0.405797), +1 yielded 55/138 (~0.398551). This makes accidental displacement substantially less plausible.

**Important statistical caveat:** the modal color is fitted using *the same screen pixels being measured*. A 100% fitted modal score does NOT independently verify the RGB values. The next direct comparison must use palette RAM codes and fixed upstream default RGB references **without fitting to the screen**.

## Implemented independent check and optional local color preview

Code:
- research/mesence/nes_palette_reference.py defines **only three** researched default 2C02 color values. No full external GPL palette table is copied.
- research/mesence/analyze_render_capture.py now adds independent_default_palette_check. It reads the saved 32-byte palette RAM from the **same frame** and looks up sprite indices 1/2/3 at RAM offsets 0x11/0x12/0x13 (or matching alternative sprite palette slots). It compares every expected opaque pixel RGB against the saved framebuffer. Unsupported codes, out-of-bounds pixels and mismatches are explicit; no screen color fitting or best-shift corrections.
- research/mesence/sprite_components.py optionally creates alpha-preserving colored previews with --reference-colors and --group-oam 10,11, using the same narrow MesenCE palette reference. Its existing synthetic grayscale preview remains the default; files are saved **only** in local FIXTURE and never overwritten.

**Pending:** Real local rerun of the new analyzer against all existing 15 files. Expected if same-session palette RAM codes are indeed 0x16,0x36,0x0F: independent_default_palette_check.status = reference_opaque_pixels_exact and pixels_exact = pixels_expected = 138. This is a **prediction**, not yet a verified result.

## What remains outside this gate

The 118 transparent source positions cannot be confirmed against an independent background-only reference from this capture alone. Index-zero transparency is already correctly decoded from NES 2bpp CHR bytes, but comparison to the actual pixels *behind* those holes requires captured background state or a controlled sprite-disabled reference with matching savestate/input.

Likewise, this single pose does not establish all Mario animations, sprite priority for other scenes, eight-sprites-per-scanline evaluation, edge clipping, or universal display palettes.

**Decision:** Proceed with the no-recapture local palette test and optional colored preview. Only after actual success should we mark Mario's **138 opaque pixels under the documented default MesenCE palette assumptions** independently verified. Full composite/transparent background proof remains open.


## Run the independent test and export local reference-color Mario (Windows PowerShell)

Do not repeat the MesenCE capture. All required raw files are already under FIXTURE.

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility
if ($LASTEXITCODE -ne 0) { throw "Could not update research branch." }

$manifest = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\render_0000450823_1794339466.json"
if (-not (Test-Path -LiteralPath $manifest)) { throw "Missing saved render manifest." }

$roms = @(Get-ChildItem -LiteralPath "F:\Dev\ROMMAGE\FIXTURE" -Recurse -File |
    Where-Object { $_.Name -in @("Super Mario Bros. 3.zip","Super Mario Bros. 3.nes") })
if ($roms.Count -ne 1) { throw "Expected exactly one SMB3 ROM in FIXTURE." }

$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "SpriteMine Python venv missing." }

$raw = & $python ".\research\mesence\analyze_render_capture.py" $manifest --rom $roms[0].FullName --group-oam "10,11"
if ($LASTEXITCODE -ne 0) { $raw; throw "Independent RGB verification failed to run." }

$report = ($raw -join [Environment]::NewLine) | ConvertFrom-Json
$check = $report.independent_default_palette_check
$check | Select-Object status, pixels_expected, pixels_compared, pixels_exact, pixels_mismatched, pixels_out_of_bounds, exact_fraction | Format-List
$check.sprite_palette_entries | Format-Table -AutoSize

$reportPath = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\screencheck_independent_render_0000450823_1794339466.json"
if (Test-Path -LiteralPath $reportPath) { throw "Report exists; refusing overwrite: $reportPath" }
[IO.File]::WriteAllText($reportPath, ($raw -join [Environment]::NewLine),
    (New-Object System.Text.UTF8Encoding($false)))
Write-Host "New metadata report saved: $reportPath"

if ($check.status -eq "reference_opaque_pixels_exact") {
    $out = "F:\Dev\ROMMAGE\FIXTURE\SMB3\SpriteComponents\render_0000450823_1794339466_default2c02"
    $preview = & $python ".\research\mesence\sprite_components.py" $manifest --rom $roms[0].FullName --sample 3 --group-oam "10,11" --reference-colors --output-dir $out
    if ($LASTEXITCODE -ne 0) { $preview; throw "Reference-color preview export failed." }
    explorer.exe $out
} else {
    Write-Warning "Independent palette check is not exact. Preserve report for investigation."
}
~~~

**Expected if the live capture used the default 2C02 palette:** status reference_opaque_pixels_exact; 138/138 pixels exact, 0 mismatches. This is a **prediction until the command runs on the saved capture**. It may instead produce a mismatch or unsupported code; preserve that evidence rather than forcing success.

If the check passes, the new local FIXTURE directory contains grayscale diagnostic previews plus reference-colored 8x16 components and the 16x16 candidate composite PNG with index-0 transparency. This is a MesenCE default 2C02 reference rendering, not proof of other video configurations, background priority or the full visible composite.

Please share only screencheck_independent_render_0000450823_1794339466.json. Original ROMs and all generated game graphics remain in FIXTURE and out of GitHub.
