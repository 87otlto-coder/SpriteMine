# SMB3 background-only reference and transparent-pixel acceptance gate

2026-11-10. SMB3 US PRG1, MesenCE research only. All captured ROMs, save states and screenshots must remain in F:\Dev\ROMMAGE\FIXTURE, never GitHub.

## Motivation

Mario's single pose from frame 450824 has 138/138 independently RGB-matched **opaque** pixels using actual NES palette RAM and fixed MesenCE default 2C02 colors. The remaining 118 pixels in the 16x16 OAM composition are correctly alpha-zero in the extracted sprite but have not been compared to an independent background-only image. Using the original sprite-visible screen as its own background evidence would be circular.

## Source-verified MesenCE mechanism

Pinned MesenCE revision 4b8a196e299b3de297b204fd1208d2981562c89b:

- UI/Views/NesConfigView.axaml: NES **Video** tab / Miscellaneous includes Disable Sprites, bound to Config.DisableSprites.
- UI/Config/NesConfig.cs: NES runtime SpritesEnabled = !DisableSprites.
- Core/NES/BaseNesPpu.cpp: maps NES config SpritesEnabled into the emulator sprite display flag.
- Core/NES/NesPpu.cpp: GetPixelColor uses that emulator display flag to suppress choosing a sprite color while keeping actual sprite shift-register processing and sprite-zero-hit logic separate.

This is an emulator display option, not an edit to NES PPU mask $2001, original ROM bytes or game data. Its effect on the user's installed Windows MesenCE build must still be validated; the option itself is not recorded in current Lua manifest files.

## Controlled replay plan (not yet performed)

A new *matched* pair of captures is needed. The previous frame 450824 cannot simply be paired with a different moment after Mario moves.

1. With the verified SMB3 US PRG1 ROM running in World 1-1, keep small Mario motionless. Pause **emulator execution**, not SMB3's own pause screen.
2. Export a save state to F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE using MesenCE's save-state functionality. If the interface cannot save directly to FIXTURE, inspect its options before proceeding. Do not silently create save states in unrelated home folders.
3. With NES Video > Disable Sprites **unchecked**, reload the save state. Start the existing research/mesence/spritemine_render_probe.lua while emulator execution is paused, then resume for its two frame pairs. Record the new foreground render_*.json manifest path.
4. Stop the previous Lua script and pause emulator execution. Set NES Video > Disable Sprites **checked**. Reload the **identical save state**, start the identical render probe while paused, and resume for the same two frames with no buttons pressed. Record the new background-only render_*.json manifest path.
5. Restore Disable Sprites to **unchecked** after the experiment.
6. Compare the two local manifests using research/mesence/verify_background_composite.py and the immutable verified original SMB3 ROM. The script outputs metadata only, never captured game pixels.

The user may need a screenshot-guided walkthrough for the NES settings and save-state export. Avoid inventing a MesenCE menu path not verified in the installed build.

## Independent comparison and safety gates

The validator rejects non-SMB3 ROMs, unverified MMC3 mapping, mismatched frame numbers or master clocks, different startFrame PPU/OAM/palette SHA-256, unsupported screen geometry, missing palette codes, and hardware sprites with background-priority bit set.

Within Mario's complete OAM union rectangle (16x16), the verifier checks:
- All opaque pixels against fixed MesenCE default 2C02 RGB references.
- All 118 source-transparent positions against the **separate sprites-disabled** RGB screen at those same coordinates.
- An 8-pixel ring surrounding Mario must be identical in both RGB captures; a changed ring indicates scene/camera mismatch.
- At least one opaque sprite pixel must visibly differ between the enabled/disabled captures, otherwise the reference cannot establish sprite suppression.

The success label is deliberately conditional: region_exact_conditional_on_sprites_disabled_reference. The GUI toggle is not captured as machine-readable metadata, and matching frame/OAM/PPU/palette plus a ring still does not independently prove full nametable/scroll history. A miss must be preserved and investigated, not silently aligned away.

## Run the analysis only when both real manifests exist

PowerShell template (replace BOTH manifest names with exact real file paths printed by the two successful captures):

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility

$foreground = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\render_FOREGROUND_SESSION.json"
$background = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\render_BACKGROUND_SESSION.json"
$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe"

$roms = @(Get-ChildItem -LiteralPath "F:\Dev\ROMMAGE\FIXTURE" -File -Recurse | Where-Object { $_.Name -in @("Super Mario Bros. 3.zip", "Super Mario Bros. 3.nes") })
if ($roms.Count -ne 1) { throw "Expected exactly one verified SMB3 ROM under FIXTURE." }
if (-not (Test-Path -LiteralPath $foreground) -or -not (Test-Path -LiteralPath $background)) { throw "Use the real manifest paths instead of placeholders." }

$raw = & $python ".\research\mesence\verify_background_composite.py" $foreground $background --rom $roms[0].FullName --group-oam "10,11"
if ($LASTEXITCODE -notin @(0,3)) { $raw; throw "Background comparison could not run." }
$report = ($raw -join [Environment]::NewLine) | ConvertFrom-Json
$report.comparison | Format-List
~~~

The placeholders are intentionally not executable until real names are known. The assistant should provide fully resolved copy-paste Windows commands after the actual foreground/background manifest names are supplied.

## Current completion level

Implemented: strict metadata-only paired-render comparator and deterministic synthetic tests, passing GitHub Actions Windows and Ubuntu Python jobs. Verified upstream presence of the NES Disable Sprites option and code path.

Not verified on owner's Windows MesenCE: identical save-state replay with that toggle, any background-only captured RGB, or the 118 transparent pixels against that independent reference. Full sprite/background priority and animation coverage remain open.
