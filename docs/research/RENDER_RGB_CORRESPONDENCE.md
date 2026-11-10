# Rendered RGB vs SMB3 OAM/CHR candidate — 2026-11-10

## Goal and current proof boundary

Previous captures verified the full 8 KiB ROM-backed PPU CHR bank mapping and reconstructed a recognizable 16x16 small Mario candidate from 8x16 hardware OAM entries #10 and #11. That is not proof that the final displayed screen pixels, colors or sprite priority agree.

This controlled follow-up records the current MesenCE RGB screen at the end of each of two frames, plus pre-render OAM, PPU, palette and timed MMC3 bank writes in the same session. It measures color-class consistency at the candidate OAM positions. It is experimental: no full actor identity, authentic NES RGB mapping, complete sprite evaluation, or pixel-perfect fidelity should be claimed from it alone.

MesenCE upstream timing check at revision 4b8a196e299b3de297b204fd1208d2981562c89b:
- Core/NES/NesPpu.cpp: SendFrame emits the EndFrame event before sending completed PPU output to the frontend
- Core/Debugger/LuaApi.cpp: GetRenderedFrame uses the current PPU frame and the active video filter; getScreenBuffer yields 24-bit RGB integers

Our new research files are:
- research/mesence/spritemine_render_probe.lua — the only script the owner loads in MesenCE
- research/mesence/verify_phase_capture.py — verifies 15 local files (four PPU/OAM/palette triples, two RGB buffers, one manifest) and reconstructs known physical MMC3 mappings
- research/mesence/analyze_render_capture.py — compares explicit OAM group pixels against endFrame screen RGB with no exported copyrighted pixels
- research/mesence/mock_mesence_render.lua — synthetic emulator for automated CI only; never load this into MesenCE

## Step A — update existing source checkout

PowerShell:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility
Test-Path -LiteralPath "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research\research\mesence\spritemine_render_probe.lua"
~~~

Expected: True.

## Step B — controlled on-device capture

1. In MesenCE, use the verified SMB3 US PRG1 ROM and enter World 1-1. Ensure the **game itself is unpaused** and small Mario is visible. Prefer standing still.
2. Open Debug > Script Window, click the square Stop button to stop any earlier script.
3. Use File > Open to choose exactly F:\Dev\ROMMAGE\TOOLS\SpriteMine-research\research\mesence\spritemine_render_probe.lua (NOT mock_mesence_render.lua).
4. Keep the existing I/O and OS Lua permission enabled for the trusted script, with Lua network access disabled.
5. Press F5 and let two frames advance. Script should log "SpriteMine RENDER CAPTURE COMPLETE:" and a new local manifest path.

The script writes a versioned render_... session: 14 binary buffers plus one JSON manifest. It refuses to overwrite existing captured evidence. Screen data is filtered MesenCE RGB24, not guaranteed original NES output.

## Step C — locally verify and produce metadata-only comparison

PowerShell, after the success message:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"

$captureDir = "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE"
$manifest = Get-ChildItem -LiteralPath $captureDir -Filter "render_*.json" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $manifest) { throw "No render_*.json capture manifest found." }

$roms = @(Get-ChildItem -Path "F:\Dev\ROMMAGE\FIXTURE" -Recurse -File |
    Where-Object { $_.Name -in @("Super Mario Bros. 3.zip","Super Mario Bros. 3.nes") })
if ($roms.Count -ne 1) { throw "Expected one SMB3 source ROM under FIXTURE; found $($roms.Count)." }

$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "SpriteMine Python environment not found: $python" }

$raw = & $python ".\research\mesence\analyze_render_capture.py" $manifest --rom $roms[0].FullName --group-oam "10,11"
if ($LASTEXITCODE -ne 0) { $raw; throw "Rendered pixel diagnostic failed." }

$report = ($raw -join [Environment]::NewLine) | ConvertFrom-Json
$report | Select-Object result, frame_count, geometry_supported, ppu_mapping_verified,
    oam_unchanged_between_start_and_end, palette_ram_unchanged_between_start_and_end |
    Format-List
$report.rgb_color_comparison.registered_oam_coordinates | Format-List
$report.chr_bank_changes_before_object_bottom | Format-Table -AutoSize

$reportPath = Join-Path $captureDir ("screencheck_" + [IO.Path]::GetFileNameWithoutExtension($manifest) + ".json")
[IO.File]::WriteAllText($reportPath, ($raw -join [Environment]::NewLine),
    (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Metadata-only report: $reportPath"
~~~

Expected: a metadata report describing the verified capture, OAM group, RGB class counts, and any geometry or mapper timing blockers. Please share only screencheck_render_*.json. Never commit the source ROM or any generated capture bin file to GitHub.

## Interpretation and limitations

The output groups expected nontransparent pixel indices by sprite palette slot and pixel index, and computes the dominant RGB color observed at those screen coordinates. A high modal agreement fraction indicates consistent observed RGB within those indexed classes. **It is not an independent calibration** because the colors are learned from the same rendered frame.

The diagnostic evaluates the exact OAM positions and four ±1-pixel controls, but never silently shifts the expected position to improve the score. If the active video filter changes the screen from 256x240, it reports unsupported geometry rather than scaling without proof. MesenCE's active video filter, palette emphasis/grayscale effects, sprite priority, background occlusion, hardware sprite evaluation, and the exact PPU fetch timing are still separate acceptance checks.

The next engineering choice depends on the real report: if alignment/color consistency is high and mapping stable, add an explicitly calibrated RGB palette and true per-pixel regression test; otherwise first investigate timing and video-filter geometry. Do not alter historical FIXTURE captures.


## Actual rendered RGB result and new independent reference (2026-11-10)

Owner supplied render session render_0000450823_1794339466 and screencheck_render_0000450823_1794339466. Mario candidate OAM #10/#11 at X=128/136 and Y=162. Verified full 8KiB ROM-backed mapped graphics; 256x240 RGB; no early CHR bank changes; unchanged OAM/palette RAM across frame. The earlier diagnostic finds 138/138 pixels consistent with screen-fitted RGB groups: #B53120 (37), #FECCC5 (31) and #000000 (70), with ±1-pixel shifts reducing the score to 55–81/138.

Independently inspecting MesenCE's built-in 2C02 default table confirms exactly those RGB values for NES color codes 0x16,0x36 and 0x0F. The latest analyzer uses **saved same-session palette RAM bytes** to select those upstream reference colors *before* comparing each opaque pixel with the rendered screen, without self-fitting. Exact result is pending an owner-side rerun on saved binaries, so do not promote the 138/138 fitted score to an independent color pass.

Reference, acceptance conditions, and next steps: docs/research/SMB3_MARIO_INDEPENDENT_PALETTE.md. The 118 transparent background positions and hardware priority require separate evidence and remain unresolved.
