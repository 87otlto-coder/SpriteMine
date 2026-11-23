# M1 World 1-1 — remaining eleven enemy actors (ambient wallpaper)

This extends the original-source **World 1-1** private scene, which already
contains the fixed 176×27 logical main panorama, four-phase background tiles,
untouched goal roulette and three independent Piranha Plants. It adds **exactly
11 additional World 1-1 actor placements**, deriving their patterns from the
verified SMB3 US PRG1 / Revision A ROM and matching MesenCE palette capture.

No ROM or extracted game artwork is committed or shared through GitHub.

## What this produces

- One stationary **2,816 × 432** scene with 66 independent animation tracks:
  51 background, 1 goal roulette, 3 plants, 11 additional enemies.
- All four Goombas, both red Koopas, one green Koopa, one Paragoomba and three
  hopping green Paratroopas at their original **source-record** coordinates.
- Each assembled from original 8×16 hardware sprite CHR pieces and the captured
  2C02 colors, with the sprite CHR page byte-verified against ROM 1KiB page 79.
- 144 numbered private PNG frames, an indefinite-loop GIF (40ms source ticks,
  **5,760ms** total), original asset/scene recipe and validation metadata.
- GIF byte-for-byte re-export determinism for the same ROM, capture, recipes,
  platform and Pillow version; all decoded GIF temporal samples checked against
  each private source PNG in RGB space. The GIF may merge identical time slots.

**Authenticity boundary:** source **sprite pieces**, palette references and
**placements** are original. Their joining/alignment follows the original
`GroundTroop_Draw`, `Troopa_Draw`, `ParaGoomba_Draw` and ObjP6C/ObjP72 tables,
but the full actor layout is a synthesized scene rather than observed complete
runtime OAM. Horizontal patrols, edge turns, short hops, fluttering, timing
phase offsets and terrain-contact adjustments are intentionally **authored
ambient wallpaper motion**, not claims of complete SMB3 movement simulation.
All 11 original source entries are shown simultaneously for creative purposes;
the actual game activates/deactivates enemies in response to scrolling and
player interaction. Their runtime visibility is **not** reproduced.

The present 25fps loop approximates ~133ms native four-background-phase and
roulette changes with 120ms animation holds. It is source-informed, not
frame-exact. No background scrolling, HUD, Mario or bonus room is included.

## Windows PowerShell 5.1 reproduction

Use the canonical `F:\Dev\ROMMAGE\SOURCE`, `FIXTURE`, and `OUTPUT` folders.
The private inputs below must have been placed under these paths first; the
script will fail explicitly rather than guessing locations or silently
creating fake artwork.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'

$rom = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip'
$graphics = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\World11_Frame450840_Graphics.zip'
$rgb = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Palettes\MesenCE_2C02_RGB24.bin'
$work = 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1'
$priorZip = Join-Path $work 'SpriteMine_M1_Piranha_Private_Scene.zip'
$priorRoot = Join-Path $work 'PriorPiranhaScene'
$priorRecipe = Join-Path $priorRoot 'private_piranha_scene\recipe.json'
$newScene = Join-Path $work 'World11_GroundActors_PrivateScene'
$export = Join-Path $work 'World11_GroundActors_Export'

foreach ($file in @($rom, $graphics, $rgb, $priorZip)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
        throw "Missing required private input: $file"
    }
}
if (-not (Test-Path -LiteralPath $priorRecipe -PathType Leaf)) {
    New-Item -ItemType Directory -Force -Path $priorRoot | Out-Null
    Expand-Archive -LiteralPath $priorZip -DestinationPath $priorRoot
}
if (Test-Path -LiteralPath $newScene) { throw "Preserving existing scene: $newScene" }
if (Test-Path -LiteralPath $export) { throw "Preserving existing export: $export" }

python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies failed to install' }

$env:SPRITEMINE_PRIVATE_ROM_ZIP = $rom
$env:SPRITEMINE_PRIVATE_GRAPHICS_ZIP = $graphics
$env:SPRITEMINE_PRIVATE_RGB_PROFILE = $rgb
$env:SPRITEMINE_PRIVATE_PIRANHA_RECIPE = $priorRecipe
python -m pytest -q tests/test_world11_ground_enemies.py
if ($LASTEXITCODE -ne 0) { throw 'World 1-1 actor tests failed' }

python tools\m1_world11\ground_enemies.py $rom $priorRecipe $graphics $rgb $newScene --export $export
if ($LASTEXITCODE -ne 0) { throw 'Private scene export failed' }

Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $export 'scene.gif')
Write-Host "Open: $(Join-Path $export 'scene.gif')"
```

Expected: **5 targeted tests pass with private inputs** (or 4 passed / 1
skipped in public Windows CI); `scene.gif` and 144 PNGs appear under the
private export, with a timeline-verification JSON reporting no RGB mismatches.

The private source inputs are never modified, and an existing output directory
is not overwritten. A second independent output path can be used for byte
reproducibility testing.

## Source provenance and limitations

- `PRG/objects/1-1.asm`, W101O at original ROM file offset `0xC537`.
- `PRG/prg004.asm`, `ObjectGroup03_PatternSets`, `GroundTroop_Draw`,
  `Troopa_Draw`, `ParaGoomba_Draw`, `ObjNorm_ParaGoomba`, `ObjNorm_RedTroopa`.
- Source pinned to Southbird SMB3 disassembly commit
  `09b1bd81a788de8ceec664a34094e84ddb463117`.
- Original MesenCE frame 450840 PPU and palette; PPU `$1C00..$1FFF` exactly
  matches source CHR 1KiB page 79. NES 8x16 odd-index tile mapping and palette
  0 transparency preserved.
- Trajectories and feet alignment use fixed local **World 1-1** surface IDs.
  This is not a generalized level collision decoder or proof of authentic AI.
- The current map still has unresolved RNG-dependent clouds, provisional
  generator interpretations and incomplete all-region native RGB validation.
  Full M1 acceptance and approval are outstanding.

No GUI, complete gameplay replay, audio work, new game support or source ROM
modifications are part of this deliverable.
