# World 1-1 original Piranha art — authored wallpaper loops

**Status:** working private preview, not original-gameplay or full-level native RGB acceptance.

This feature extends the [World 1-1 source compiler](README.md), [original CHR animation](animate_world11.py), and [goal-card roulette](GOAL_ROULETTE.md). The **source ROM is immutable**, generated PNG/GIF remain private, and no original copyrighted game graphics are part of GitHub.

## Exact original input records

The verified SMB3 **USA PRG1 / Revision A** ROM contains World 1-1 `W101O` at file offset `0xC537`, including:

| Original object ID | Source X/Y (16-pixel units) | Source world X + init offset / Y | Graphics |
| --- | --- | --- | --- |
| `$A6` tall Venus Fire Trap | `$16`, `$17` | `(360, 368)` | red/green tall plant |
| `$A0` green Piranha Plant | `$70`, `$18` | `(1800, 384)` | green mouth plant |
| `$A4` green fire Piranha | `$74`, `$17` | `(1864, 368)` | green fire plant |

Original `ObjInit_RedPiranha`/`ObjInit_GreenPiranha` shifts X by 8 pixels. The original object pattern table in `PRG/prg005.asm` uses 8×16 NES OAM sprites `$E1/$E3/$E5` for the plain green variant and `$F1/$F3/$F5/$F7` with `$E3` stems for fire variants. The palette is from `ObjectGroup04_Attributes`: 2 for green, 1 for Venus's head, 2 for lower stem. `ObjectGroup04_PatTableSel` sets CHR page `$4F` for these objects. Frame-450840 MesenCE PPU `$1C00..$1FFF` matches **ROM CHR 1 KiB page 79** byte for byte. All art is decoded from those source tiles and the captured palette; no screenshots are used as art.

## Movement and correctness classification

The original `Piranha_Emerge` and `Piranha_Retract` use vertical speed `-$10` and `$10` in 8.8 fixed-point terms (approximately 1 pixel per game frame); targets are 25 pixels for green and 33 for the tall red variant. The head animation toggles every eight game frames. The actual game additionally uses Mario-proximity gating, timers, sometimes projectile spawning, sprite masks and OAM priority. Those aren't reproduced here.

**Wallpaper behavior is authored**, on purpose: fixed-camera, independently phased emergence/hold/retraction/hidden cycles that repeat, 40 ms per exported PNG time slot, and three plant tracks with different start phases. The original background/goal frame cycles are approximated as 120 ms per state (three 40 ms ticks), compared with approximately 133.1 ms in the NTSC original. The pipe-mouth occlusion uses a transparent clip at the original pipe-cap Y rather than the original masking sprite `$77`. This is visually suited to a static wallpaper, **not** a native CPU/PPU trace.

The output GIF lasts 5,760 ms and is sourced from **144 lossless numbered 2,816×432 PNG frames**. GIF encoders can merge adjacent identical frames and add their durations; the acceptance check therefore compares *every PNG time slot* against the decoded GIF's cumulative timing, rather than asserting the compressed GIF physically contains 144 distinct frames. Scene still uses the actual PR #29 compositor and original output recipe.

## Windows PowerShell 5.1: reproducible private build

```powershell
$repo = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip'
$graphics = 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1\World11_Frame450840_Graphics.zip'
$rgb = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Palettes\MesenCE_2C02_RGB24.bin'
$root = 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1'
$run = Join-Path $root ('PiranhaScene-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
Set-Location -LiteralPath $repo
foreach ($file in @($rom, $graphics, $rgb)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing private input: $file" }
}
New-Item -ItemType Directory -Force -Path $run | Out-Null
$static = Join-Path $run 'static'
$animated = Join-Path $run 'animated'
$withGoal = Join-Path $run 'goal'
$withPlants = Join-Path $run 'piranhas'
$export = Join-Path $run 'export'
python -m pip install -e '.[dev]'
python 'tools\m1_world11\make_m1_bundle.py' $rom $static --frame-graphics-zip $graphics --rgb-profile $rgb
if ($LASTEXITCODE -ne 0) { throw 'Static map compilation failed' }
python 'tools\m1_world11\animate_world11.py' $rom (Join-Path $static 'scene\recipe.json') $graphics $rgb $animated
if ($LASTEXITCODE -ne 0) { throw 'Background animation build failed' }
python 'tools\m1_world11\goal_card.py' $rom (Join-Path $animated 'recipe.json') $graphics $rgb $withGoal
if ($LASTEXITCODE -ne 0) { throw 'Goal roulette build failed' }
python 'tools\m1_world11\piranha_plants.py' $rom (Join-Path $withGoal 'recipe.json') $graphics $rgb $withPlants --export $export
if ($LASTEXITCODE -ne 0) { throw 'Piranha PNG/GIF build or timeline verification failed' }
$env:SPRITEMINE_PRIVATE_ROM_ZIP = $rom
$env:SPRITEMINE_PRIVATE_GRAPHICS_ZIP = $graphics
$env:SPRITEMINE_PRIVATE_RGB_PROFILE = $rgb
$env:SPRITEMINE_PRIVATE_GOAL_RECIPE = Join-Path $withGoal 'recipe.json'
python -m pytest -q tests/test_world11_piranha.py
if ($LASTEXITCODE -ne 0) { throw 'Piranha regression tests failed' }
Write-Host "GIF: $(Join-Path $export 'scene.gif')"
Write-Host "PNG frames: $(Join-Path $export 'frames')"
Write-Host "Manifest: $(Join-Path $export 'piranha_timeline_verification.json')"
```

Output stays in private `F:\Dev\ROMMAGE\OUTPUT`. Source ROM and MesenCE fixture captures remain read-only. Repeated exports must use fresh run folders; original game data must not be pushed to public GitHub.

## M1 remains unfinished

This introduces three original-source enemy sprites and a first coherent visual motion pass. Additional actors (Goombas, Koopas, Paratroopas), original cloud RNG, source map/scenery validation and owner acceptance of the whole animated panorama remain outstanding. Native OAM sprite masks, object spawn conditions, and projectile gameplay remain outside this authored wallpaper scope. Do not mistake a visually plausible composition for complete game emulation.

Credit/source research: Southbird SMB3 disassembly, pinned commit `09b1bd81a788de8ceec664a34094e84ddb463117`, `PRG/prg005.asm` and `PRG/objects/1-1.asm`, https://github.com/captainsouthbird/smb3 . Verify redistribution obligations of third-party references before adapting their code. This feature references original source logic; it does not include disassembly code.
