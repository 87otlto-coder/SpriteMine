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

Native MesenCE reference dumps can be read directly. Use `"format": "rgb24"`
and `"size": [256, 240]` for a full native RGB frame. For either format, set
`"sha256"` to require an exact source fingerprint. Comparison results include
the observed digest. Provide the playfield crop and both world scroll axes
explicitly. A raw frame or staging event alone cannot establish those offsets.

For aligned comparisons, optionally declare `"playfield": [0, 0, 256, 192]`
to reject crops that extend into the HUD of a capture with that boundary.
Use the boundary verified for the selected capture. To align by a measured
point, supply `"anchor": {"capture": [x, y], "world": [wx, wy]}` in place
of scroll and origin. The points must refer to the same location in the
same scene and frame.

PPU scroll describes the nametable address space. The 13 accepted bonus-area
reference frames record PPU coordinates (8, 239) at start, in base nametable
0. That gives the hardware fetch origin but supplies no mapping to the
main area's world coordinates. A world comparison needs a verified world
anchor or camera origin from the corresponding capture.

### Bounded World 1-1 main-area reference alignment

The native screen-8 checkpoint places the upper pipe mouth at columns
141–142, row 7. The top-left corner maps to world (2256, 112) at 16 pixels
per logical tile. Independent inspection of the private replay RGB frames
located the left corner of its 32-pixel top edge at capture (106, 112) in
frame 450778 and at (108, 112) in frame 450840. The resulting world
origins are (2150, 0) and (2148, 0), respectively. The sampled PPU
start-state fine X shifts by two pixels in the same direction as the
inferred camera motion. Both frames precede the bonus-room junction.

Use scanlines 0–191 as a conservative comparison crop. This inspection
does not establish an exact main-area HUD split or a vertical scroll
transition. A separate rerun of the existing pipe-mask verifier on private
paired captures matched all 7,528 eligible overlap samples. That comparison
tests the native mask model and is independent of the scene compositor.
The main-area world anchors can align a future comparison with an
independently supplied scene. They do not establish scene pixel fidelity
or coverage outside the sampled pipe.

### Native vertical alignment cross-check

In the earlier lower approach, frame 449473 shows the two blocked pipe
openings at capture rows 65 and 129. The recorded logical map independently
places them at tile rows 19 and 23, which start at world rows 304 and 368.
Both landmarks give world Y origin 239. The start-of-frame PPU state also
records local fetch Y 239. The blocked openings occupy the logical tile
span starting at capture X 124, giving world X origin 2132, consistent with
PPU local fetch X 84 in this part of the map. Individual border pixels may
be transparent and should not be used as tile boundaries.

A native-to-native cross-check of the upper pipe crops from frames 450778
and 450840 found identical RGB for all 1,024 pixels in the anchored
32-by-32 rectangle. This establishes a consistent native reference in
that rectangle. Compositor fidelity requires a separate scene input.

## Direct MesenCE CPU-staging input and inspection

The importer uses the existing neutral A/B/A replay layout from PR #23.
It consumes the hashed `B/background-staging.tsv`, paired 54-byte pattern
strips and screen-major `bg-*-tiles.bin` snapshots for one staging frame.
Patterns are arranged as 16 × 16 metatiles over all 27 logical rows. Only
columns with agreeing left and right uploads are populated. Null cells
preserve unobserved columns. The importer reads the selected graphics
frame's mapped PPU CHR windows, palette bytes and PPU state. Use a local
192-byte RGB profile containing 64 consecutive RGB triplets.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Composition'
$env:PYTHONPATH = 'src'
python -m spritemine.native_staging $capture $stagingFrame $graphicsFrame $profile $bundle --screens $screens
python -m spritemine.scene_export (Join-Path $bundle 'recipe.json') $exports
python -m spritemine.scene_coverage (Join-Path $bundle 'recipe.json') $coverage --references $references
```

Use fresh output directories. The selected capture needs a logical dump of the
declared screen count. Choose the graphics frame using independent stability
evidence for the target scene. Window hashes identify the captured mapping;
they do not identify physical ROM bank numbers when the capture lacks that
association. The importer uses the logical tile palette group and captured
palette RAM. Attribute-commit equivalence, mid-frame mapper changes, HUD and
sprites are outside this importer. The existing independent verifiers remain
the authority for their respective capture gates. The generated recipe can
accept additional PNG assets, foreground layers and independently timed
tracks through the normal compositor schema.

Coverage writes JSON and a text grid. Each cell lists resolved grid tiles,
ticks at which matching crop rectangles cover the entire cell, and ticks
whose mismatch bounding rectangles overlap it. Failed comparisons retain
their exact pixel count and bounding rectangle. Match evidence applies to
the listed ticks and to the supplied reference classification. Tile occupancy
excludes stamps and tracks. No references means no matched cells.

## Milestone 1 integration order

The owner-confirmed [PR #28 requirements](https://github.com/87otlto-coder/SpriteMine/pull/28)
govern M1. First review the entire 11-screen, 27-row main-area static scene
(2,816 × 432 logical pixels) with an unknown-cell ledger and no Mario or enemies.
Validate terrain, pipes, blocks, plants, scenery, priority and camera alignment
against native gameplay regions. Then independently animate the observed
objects in a stationary seamless GIF, with at most one Mario. Integrate
enemies last. The bonus area has its own coverage and the creative GIF in
PR #27 remains a prototype.

The existing W101O records describe placements, including 14 enemies and an
end card. Once the source coordinates and frame assets are available, use an
explicit world anchor per placement and attach a track. Existing motion
supports edge turns, falling, hopping and hidden resets. Explicit cels permit
source-derived timing without expanding into a gameplay simulator. Distinguish
recorded source behavior from authored loop and reset behavior.
