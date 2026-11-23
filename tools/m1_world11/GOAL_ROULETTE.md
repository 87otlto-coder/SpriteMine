# World 1-1 original end-card roulette (source-driven M1)

The end-level roulette is object `OBJ_ENDLEVELCARD` (`$41`), rendered as two
mirrored 8×16 NES hardware sprites. The original frame table `ObjP41` contains
the untouched three-frame pattern indices `$51`, `$53`, `$55`. The original
attribute table selects sprite palettes 1, 2 and 1 respectively. They display
a red/white **Mushroom**, green/white **Flower** and white **Star** over the
black, white-bordered goal square. The right 8×16 half is a horizontally flipped
copy of the left half.

`EndLevelCard_Untouched` in `PRG/prg002.asm` changes `Objects_Frame` every **8
NES game frames**. At approximately 60.0988 NTSC frames per second, the rate is
**133.11 ms per symbol**. A four-phase CHR background cycle also advances every
8 frames. The combined 3×4 animation returns to its original state after 12
steps (96 game frames, about 1.597 seconds). GIF uses 130 ms per step (1.56
seconds) to preserve the original four-phase background cadence within GIF's
10 ms timing granularity; playback is about 2.3% faster than the source game.

The World 1-1 enemy/object record `OBJ_ENDLEVELCARD,$A8,$15` maps to native
world position `(2688, 336)`, with a 16×16 sprite pair. No manual graphical
placement is needed. The source background includes the 32-ish pixel white
outlined card square; the sprite component is drawn on top.

The private MesenCE frame-450840 PPU snapshot matches original ROM CHR page 4
at `$1400..$17FF` byte-for-byte; that is where the end-card OAM patterns are
read. The matched frame-local sprite palette and default 2C02 RGB profile
provide the actual pixel colors. This private snapshot is an authenticated
source graphics input, not a destination screenshot copied into a tile. The
user's 2026-11-22 MesenCE recording independently shows the same star,
mushroom and flower symbols around 18.5–20 seconds. Because the recording is
H.264, it is visual evidence and **not** a lossless native RGB gate.

## Reproduction from a checked-out feature branch (PowerShell 5.1)

All paths are absolute; keep the verified ROM and graphics capture immutable.
Replace the indicated private files' names only if they are stored at different
paths under `FIXTURE` or `OUTPUT`. Run commands on Windows with Python 3.11 or
newer and the package installed.

```powershell
$repo = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip'
$graphics = 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1\World11_Frame450840_Graphics.zip'
$rgb = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Palettes\MesenCE_2C02_RGB24.bin'
$root = 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1'
$run = Join-Path $root ('GoalRoulette-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))

Set-Location -LiteralPath $repo
foreach ($file in @($rom, $graphics, $rgb)) {
    if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing private input: $file" }
}
New-Item -ItemType Directory -Force -Path $run | Out-Null
$static = Join-Path $run 'static'
$animated = Join-Path $run 'animated'
$withCard = Join-Path $run 'goal-scene'
$export = Join-Path $run 'export'

python 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\tools\m1_world11\make_m1_bundle.py' `
    $rom $static --frame-graphics-zip $graphics --rgb-profile $rgb
if ($LASTEXITCODE -ne 0) { throw 'Static source generation failed' }

python 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\tools\m1_world11\animate_world11.py' `
    $rom (Join-Path $static 'scene\recipe.json') $graphics $rgb $animated
if ($LASTEXITCODE -ne 0) { throw 'Background animation generation failed' }

python 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\tools\m1_world11\goal_card.py' `
    $rom (Join-Path $animated 'recipe.json') $graphics $rgb $withCard --gif-output $export
if ($LASTEXITCODE -ne 0) { throw 'End-card animation or GIF verification failed' }

$env:SPRITEMINE_PRIVATE_ROM_ZIP = $rom
$env:SPRITEMINE_PRIVATE_GRAPHICS_ZIP = $graphics
$env:SPRITEMINE_PRIVATE_RGB_PROFILE = $rgb
python -m pytest -q tests/test_world11_animation.py tests/test_world11_goal_card.py
if ($LASTEXITCODE -ne 0) { throw 'World 1-1 animation regressions failed' }

Write-Host ('GIF: ' + (Join-Path $export 'scene.gif'))
Write-Host ('PNG frames: ' + (Join-Path $export 'frames'))
Write-Host ('Manifest: ' + (Join-Path $export 'goal_roulette_verification.json'))
```

A **fresh** `$run` folder is required; the builder refuses to overwrite a
previous scene. The generated recipe and exported assets stay under private
`OUTPUT`; no game artwork or ROM is stored in GitHub.

## Scope and verification

- **Original** ROM-derived sprite bytes, source-derived placement and original
  8-game-frame state interval; matched ROM/PPU sprite CHR page.
- **GIF timing:** 130 ms per state (133.1 ms in original NTSC game). Twelve
  frames combine the three card and four background phases. All frames must be
  visually distinct and match the numbered PNGs pixel-for-pixel after GIF
  decoding; deterministic repeat exports must produce identical hashes.
- **Unverified / unfinished:** This implements the *untouched* spinning goal
  box only. It does **not** implement Mario collecting it, the card flying
  away, `COURSE CLEAR`, or map inventory sequence. It does **not** establish
  native RGB24 acceptance for the entire World 1-1 canvas.
- The user's H.264 playthrough shows both the untouched spin and the collected
  end sequence. Use it to plan the separate transition animation, not as a
  replacement for lossless emulator captures.

Source reference: [captainsouthbird/smb3](https://github.com/captainsouthbird/smb3)
commit `09b1bd81a788de8ceec664a34094e84ddb463117`,
`PRG/prg002.asm`, `PRG/prg000.asm`, `PRG/objects/1-1.asm`.
