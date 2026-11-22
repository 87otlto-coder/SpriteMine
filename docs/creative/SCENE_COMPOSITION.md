# Headless scene composition

The compositor consumes local PNG assets and a versioned JSON recipe. It
renders an entire fixed two-dimensional canvas on every tick. Extraction tools
supply the inputs. They can change independently of the renderer.

This engine uses the fixed-palette and independent-period techniques reviewed in
[PR #27](https://github.com/87otlto-coder/SpriteMine/pull/27). The
[World 1-1 acceptance requirements in PR #28](https://github.com/87otlto-coder/SpriteMine/pull/28)
still apply. The checked-in generator and tests use original synthetic art and
geometry. They establish compositor behavior and export integrity.

## Windows reproduction

With Python 3.11 or newer and the project dependencies installed, run:

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Composition'
$env:PYTHONPATH = 'src'
$sceneRoot = Join-Path 'F:\Dev\ROMMAGE\OUTPUT' ('SyntheticScene-' + [guid]::NewGuid())
python tests/fixtures/make_scene_fixture.py (Join-Path $sceneRoot 'inputs')
python -m spritemine.scene_export (Join-Path $sceneRoot 'inputs\recipe.json') (Join-Path $sceneRoot 'build')
python -m pytest -q
```

The build contains a background-and-static-layers PNG, looping GIF, and
manifest with SHA-256 hashes of the recipe, source PNGs, and exports. To
regenerate, reuse the recipe and choose a fresh output directory. Compare the
hashes using the same Pillow version. Pillow can combine consecutive identical
frames into a longer hold. Playback timing is determined by the sum of holds.

## Recipe version 1

| Field | Meaning |
| --- | --- |
| `size`, `background` | Native world width and height, and opaque RGB clear color |
| `ticks`, `tick_ms` | Global period and time per tick. GIF requires a multiple of 10 ms and a total duration of at most 655,350 ms |
| `assets` | Map identifiers to relative PNG `file` paths, optional SHA-256, and optional `provenance` object |
| Asset `crop` | Source rectangle as `[left, top, width, height]`. Useful for tile atlases and captures with a HUD |
| Asset `palette` | Optional per-index RGBA entries for indexed PNGs. Alpha zero is transparent |
| `tile_size`, layer `tiles`, layer `tile_origin` | Grid cell width and height, rows of asset IDs or null, and optional grid origin in pixels |
| Layer `stamps` | Individual `asset` plus `at` coordinates. With an optional `viewport` object, `at` is in capture pixels and the converter adds `scroll` and subtracts `origin` on both axes |
| Layer `tracks` | Independently sampled tracks anchored at `at`. A track uses timed `cels` or compiled `motion` and optionally a `phase` in ticks |
| Cel `asset`, `offset`, `ticks` | Asset ID or null for hidden, optional displacement from anchor, and positive hold duration. Total holds must divide global ticks |
| `terrain` | Collision grid as `rows` of solid cells, `tile_size`, and optional `origin` |

Composite layers are ordered back to front. Within a layer, tiles are followed
by stamps and then tracks. Add later layers for foreground occlusion. Sprite
alpha affects compositing. Exports are opaque against the chosen background.
GIF export requires at most 256 composited RGB colors across all frames and
reports palette overflow instead of silently changing colors.

A motion track specifies `bounds`, `period`, `hide_y`, and `left` and `right`
lists of frame asset IDs. Optional controls include `direction` (-1 or 1),
`speed`, `max_fall`, `jump`, `frame_ticks`, and `turn_at_edge`. Terrain
collisions use integer pixel steps. An actor can patrol, hop, fall, or stay
hidden below `hide_y` until the next cycle. Visible motion must close at the
spawn point. Use explicit cels for captured movement, flight paths, emergence
and retraction, or other scheduled visibility changes. These are composition
rules and require game evidence before being described as native behavior.

## Connecting local inputs

An upstream decoder or capture utility can write an indexed tile atlas, resolved
tile rows and per-frame transparent PNGs into a private recipe directory.
Use asset provenance to retain source classification, ROM and capture hashes,
bank/palette references, capture frame IDs and decoder version. Map both scroll
axes using the captured playfield origin. Strip HUD and any unwanted sprites in
the upstream adapter or by cropping the source rectangle. Preserve unknown tile
coverage in the upstream report. A null grid cell only means there is no stamp
to paint at that position.

The 27-row staging evidence belongs to the existing native-staging workflow,
including `research/mesence/verify_background_staging.py` on the background
research branch. Reuse PR #27's decoded metatile/capture asset boundary and the
existing placement evidence upstream of this recipe. The recipe supports both
pixel and grid placements, independently phased schedules, and explicit
record-derived track anchors. It expects those inputs to be resolved already.
No direct adapter to the private staging artifact formats was verified here.

Current verification covers indexed palette alpha, captured crop and
two-axis placement, layer occlusion, edge and wall turns, gravity, hopping,
hidden reset, byte-identical repeat exports, decoded frame timing and RGB
round-trip, and nominal 2,816 × 432 export bounds. Synthetic checks provide no
World 1-1 placement, texture, timing, or coverage evidence. The private
World 1-1 panorama and full animated export remain open acceptance gates.

## Local NES graphics and viewport comparison

The adapter accepts a normalized descriptor with the same fields as recipe
version 1. A PNG asset can point to a local capture or animation frame.
For packed NES CHR bytes, set the asset file to a local binary, add
`chr: {"offsets": [0, 16, 32, 48], "grid": [2, 2]}` and supply the
four-entry RGBA palette. Offsets are byte positions in the specified
binary. The grid lays out 8 × 8 patterns in row-major order. Use explicit alpha
for the zero index where applicable. Upstream data supplies bank resolution,
logical tile rows, animation schedules and capture alignment. The bundle
contains hashes and keeps the original files untouched.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Composition'
$env:PYTHONPATH = 'src'
python -m spritemine.scene_input adapt $descriptor $bundle
python -m spritemine.scene_input compare (Join-Path $bundle 'recipe.json') $references
```

Set `$descriptor` and `$references` to private JSON paths and `$bundle` to a new
output directory. Each entry in the reference JSON's `checks` array gives
`file` (relative PNG path), `tick`, `crop` (x, y, width, height in capture pixels),
`scroll` (x, y), and optionally `origin` (x, y). Use synchronized reference
captures containing the same intended layers and omit any HUD from the crop.
The comparator reports each mapped world rectangle, differing pixel count,
and local mismatch bounds. Exit 0 means all listed crops matched, 1 means
at least one differed, and 2 indicates invalid input. Coverage is exactly the
set of submitted crops and ticks. A pass does not establish full-screen or
full-level coverage by itself.

Direct reading of emulator staging TSVs, runtime CHR bank resolution and native
World 1-1 visual acceptance remain outside the adapter's verified coverage.
