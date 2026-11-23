# SpriteMine M1 — provisional World 1-1 source compiler (chat prototype)

This is an original Python implementation of a **partial, read-only** SMB3 USA
PRG1 World 1-1 construction interpreter. It runs without Work Mode and requires
the user's original ROM ZIP. **It is not a finished Milestone 1 release.**

## What it does

- Verifies NES ROM SHA-256 and World 1-1 source stream SHA-256, identifies all
  86 construction commands, and accounts for variable-width records.
- Applies 84 source-derived commands to a 176 × 27 logical tile grid, including
  ground, pipes, pits, coins, brick/block runs, bushes, large colored blocks,
  cloud runs, and the goal region. Some block shadow and goal modeling is
  provisional and needs emulator comparison; 60 random cloud writes remain
  unresolved because the original RNG state is unavailable in this chat.
- Outputs a full-size 2816 × 432 preliminary image from genuine ROM CHR pixel
  data, **using illustrative colors and a historically documented but not
  whole-scene-verified CHR mapping**. It is not native gameplay RGB.
- Generates a version-1 JSON scene recipe and private PNG metatile assets
  compatible in structure with the scene compositor in SpriteMine PR #29.
  The recipe uses a single static tick, **not an animated milestone GIF**.
- Exports source command, logical tile, per-cell last-writer and uncertainty
  ledgers. All 4752 cells remain native-unverified until separately compared.

## Layout of the downloaded packages

**Code-only ZIP:** `world11_compile.py`, `preview_tiles.py`,
`make_m1_bundle.py`, `verify_pipe_native.py`, `verify_video_reference.py`, `tests/test_world11_source_compiler.py`, this README. It contains
no ROM or extracted game artwork.

**Private scene ZIP:** Generated PNGs, a compatible `scene/recipe.json`,
`source_command_ledger.json`, `source_tile_ledger.json`, preview image, and
`partial_layout_report.json`. It contains assets derived from the owner's ROM:
**keep it private, do not publish to GitHub**.

## Windows PowerShell 5.1 reproduction

From a checkout of this PR, the tool lives under
`F:\Dev\ROMMAGE\SOURCE\SpriteMine\tools\m1_world11`. Keep the original ROM
separately under `F:\Dev\ROMMAGE\FIXTURE`.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\tools\m1_world11'
python -m pip install 'Pillow>=10,<13' 'pytest>=8,<10'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip'
if (-not (Test-Path -LiteralPath $rom)) {
    throw 'Update $rom to the actual existing private ROM ZIP path under FIXTURE.'
}
$output = Join-Path 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1' ('SourcePreview-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
python .\make_m1_bundle.py $rom $output
if ($LASTEXITCODE -ne 0) { throw 'Source compilation failed' }
$env:SPRITEMINE_PRIVATE_ROM_ZIP = $rom
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
python -m pytest -q tests/test_world11_source_compiler.py
if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed' }
```

For a *single frame's* potentially accurate graphics mapping/colors, provide
all three verified private local files to `make_m1_bundle.py`:

```powershell
python .\make_m1_bundle.py $rom $output `
    --ppu-snapshot $ppuDump `
    --palette-ram $paletteDump `
    --rgb-profile $rgbProfile
```

Alternatively, use the *unmodified* two-file capture ZIP created during the
450840 replay. This is the preferred option because it checks that PPU and
palette inputs are from the same frame and avoids unpacking files manually:

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\tools\m1_world11'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip'
$graphicsZip = 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1\World11_Frame450840_Graphics.zip'
$rgbProfile = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Palettes\MesenCE_2C02_RGB24.bin'
$output = Join-Path 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1' ('NativeFrame-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
python .\make_m1_bundle.py $rom $output --frame-graphics-zip $graphicsZip --rgb-profile $rgbProfile
if ($LASTEXITCODE -ne 0) { throw 'Frame-local scene generation failed' }
```

Use a **new** `$output` directory for each run. The profile must contain 64
consecutive RGB24 colors (192 bytes). The PPU snapshot is 12,288 bytes, palette
RAM is 32 bytes. The parser matches each of the four background mapped 1-KiB
CHR windows to the original ROM, and rejects ambiguous matches. **A single
frame's mapping is not proof of all columns or animation timing.**

The CLI remains a headless tool in dependent draft PR #31, not yet merged
into main. The owner may use PR #29's compositor on the private
`scene/recipe.json`. Public Windows CI tests synthetic inputs; original ROM
and MesenCE verification are optional private checks only.

## Evidence and restrictions

- Target ROM fingerprint:
  `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`
- World 1-1 264-byte stream fingerprint:
  `ef2d1e5a95cd51391e5651af0cdd9ab0cba36985e4cf971d3eed7c34d506892a`
- Reference used for structure/behavior, not copied implementation:
  [Captain Southbird SMB3 disassembly](https://github.com/captainsouthbird/smb3),
  pinned `09b1bd81a788de8ceec664a34094e84ddb463117`.
- The original ROM ZIP is **never changed**. No ROM or extracted art is in the
  source-code ZIP. Public implementation is in draft PR #31 (not main).
- A targeted lower-pipe visual correction was made following the owner's
  MesenCE screenshot. The source's low-nibble+1 pipe-body run is preserved,
  but overlapping body pixels no longer replace already populated Plains
  ground tiles in this *visible-scene preview*. The suppressed writes are
  preserved as `pipe_ground_overlaps` in the provenance report. This is an
  explicitly provisional creative-compositor rule until source/runtime tile
  ordering is independently confirmed.
- The uploaded screenshot (`image(20261122-202320).png`) was aligned with the
  source stage at world origin (2176,239), 2x scale and display x-offset 1.
  For logical row 26, columns 139–146, only 15 of 16 tile scanlines are visible
  before the HUD. The previous preview differed in 2,556 of 7,680 displayed
  RGB pixel samples; the corrected preview matches all 7,680 (0 mismatches).
  This also confirms the one-cell pit at col 140 is real. This is screenshot-
  bounded evidence, not whole-stage native RGB acceptance.
- To reproduce that check locally, keep the screenshot private and run:

  ```powershell
  Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\tools\m1_world11'
  python .\verify_pipe_native.py `
      'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11M1\<render-folder>\partial_chr_preview.png' `
      'F:\Dev\ROMMAGE\FIXTURE\SMB3\<private-screenshot-name>.png' `
      'F:\Dev\ROMMAGE\REPORTS\SMB3\pipe_row26_comparison.json'
  ```
  The report directory must exist and the destination JSON must not already
  exist. The screenshot is only a reference; its pixels are not used to draw
  the candidate stage.
- Next M1 tasks: resolve authentic RNG-dependent cloud placements, validate
  command semantics/overwrites and entire logical map against native
  Tile_Mem or captured staging data; use correct frame/column CHR mapping
  and palettes; add real object animations and enemy timelines; validate
  native pixel coverage and full fixed-panorama animated export.

## 2026-11-22 visual review of the private gameplay recording

The owner-supplied MesenCE recording is a compressed 30fps MP4, not lossless
RGB24. Private local frame extraction and an explicit camera alignment were
performed using the video at t=14s and t=18s. Independent scenery was rendered
from the ROM, not copied from the recording.

- **Late pipe/terrain scene** at source world origin `(2208,239)`: comparing the
  248 × 192 native-scale candidate against a 2× display crop of the recording,
  with a 36 × 40 cursor exclusion, put 45,758 of 46,176 compared positions
  within 50 RGB units per channel (99.09%). This is **H.264-tolerant visual
  evidence**, not exact RGB acceptance.
- **Goal-edge silhouette** from the t=18s frame, origin `(2456,239)`: 4,960
  of 4,960 pixels classified as sky or black agreed with the ROM-rendered
  goal edge, world rectangle `(2472,239,32,155)`. This checks the black/sky
  shape only, not original color values or every goal decoration.
- The diagonal black boundary and outlined black goal scenery are **real
  features of World 1-1**. Do not erase them as if they were image defects.
- The large-block shadows remain source-modeled and plausible; final native
  tile-map acceptance has not occurred. Avoid altering their palette or blend
  mode without contradictory native evidence.

An optional video-frame comparison helper is included:

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\tools\m1_world11'
# Supply a private 516x546 PNG frame extracted from the original MesenCE MP4,
# and a fresh destination for the JSON report.
python .\verify_video_reference.py $previewPng $videoFramePng $reportJson
# For the *goal* frame instead, add --goal-edge.
```

Video-frame coordinates are intentionally specific to the owner's recorded
MesenCE window. These video checks never count toward strict native RGB24
coverage. Exact future validation should use independently captured native
RGB24, synchronized CHR banks/palette and the correct camera origin.

Code lives in a separate, reviewable source package. The captures, extracted
CHR graphics, MP4 and private scene ZIP must stay outside public GitHub.

## Repository integration

This feature branch is based on `feature/scene-compositor` (draft PR #29).
Run `python -m pytest -q tests/test_world11_source_compiler.py` from the
repository root. Tests requiring ROMs, captures or gameplay video skip in
public CI. The source compiler is a transitional headless workflow; it is
not a second permanent ROM-import API and does not satisfy full World 1-1
visual acceptance yet.
