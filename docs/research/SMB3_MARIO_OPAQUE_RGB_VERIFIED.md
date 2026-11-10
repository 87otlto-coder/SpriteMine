# SMB3 small Mario — independent opaque-pixel RGB verification PASSED

**Date:** 2026-11-10  
**Scope:** SMB3 US PRG1, captured MesenCE default 2C02 palette conditions, **one** small-Mario pose at frame 450824.  
**Status:** PASS for independently predicted **opaque** sprite RGB at the exact hardware-OAM coordinates; **not** full background compositing or animation validation.

## Evidence reviewed

The owner uploaded metadata-only `screencheck_independent_render_0000450823_1794339466.json` plus six private PNG previews (two hardware 8x16 components and their 16x16 combined composition, each in grayscale and MesenCE default-2C02 reference RGB).

Original local session: `render_0000450823_1794339466`. Verified source ROM SHA-256: `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`. Frame 450824 rendered RGB source SHA-256: `78e49771babc3ab3193e15d46c856d6e56a53627b9b9e53adfb471ea6e610f9d`. PPU source SHA-256: `e5b13a28c78d277bad5d2846fe2275eb973ca8fded35ebeadea3335274dbcdf2`.

The actual local Python verifier reports:

- `independent_default_palette_check.status = reference_opaque_pixels_exact`
- `pixels_expected=138`, `pixels_compared=138`, `pixels_exact=138`, `pixels_mismatched=0`, `pixels_out_of_bounds=0`, `exact_fraction=1.0`
- Per captured sprite palette RAM entry: NES code `0x16` at palette offset 17 maps to independent MesenCE RGB `#B53120` (**37/37**); code `0x36` at offset 18 maps to `#FECCC5` (**31/31**); code `0x0F` at offset 19 maps to `#000000` (**70/70**).
- `ppu_mapping_verified=true`, `geometry_supported=true` (256x240 screen), `oam_unchanged_between_start_and_end=true`, `palette_ram_unchanged_between_start_and_end=true`, no tracked CHR bank register changes before this sprite's final row.
- Source OAM entries **10** at (128,162), tile 7, and **11** at (136,162), tile 5. Both derive exact ROM offsets (347248, 347264) and (347216, 347232) respectively.

**Independent palette reference:** upstream MesenCE `Core/NES/NesDefaultVideoFilter.cpp` at `4b8a196e299b3de297b204fd1208d2981562c89b`, default 2C02 palette. The code reads actual saved palette RAM, maps its codes to fixed upstream reference RGB, and compares against rendered screen bytes; it does **not** learn expected RGB by fitting the same screen.

## Local image-byte verification (2026-11-10)

The six uploaded original PNGs were inspected in memory with Pillow; no game graphics were checked into this repository.

| Private PNG basename | Size | Opaque pixels | Fully transparent pixels | PNG SHA-256 |
|---|---|---:|---:|---|
| `hardware_group_oam_10_11_frame_450824.png` | 16x16 | 138 | 118 | `55adb23537d34c51809ed4ce3d40503ca0cc2b43f58a72ee26e0e0637f025e5d` |
| `hardware_group_oam_10_11_frame_450824_mesen2c02ref.png` | 16x16 | 138 | 118 | `0dd531eb61f9d07255b2f3068cd6c17e8ca311c5d07249150a1f2752606cd9c7` |
| `hardware_oam_10_frame_450824.png` | 8x16 | 73 | 55 | `28168f4a66d4ead2ea6575b809c5e3dbf38e3c67a928d6ac6961f50ffc979eb2` |
| `hardware_oam_10_frame_450824_mesen2c02ref.png` | 8x16 | 73 | 55 | `b95e86c741c6c860afdec4f04a7c0153fc00424eb0bc67a6d78f0dfcccd9f1ee` |
| `hardware_oam_11_frame_450824.png` | 8x16 | 65 | 63 | `4c899728c5f47ebc66c73b0376cc7a7d15f3dbe444ccb076508fdc198c443945` |
| `hardware_oam_11_frame_450824_mesen2c02ref.png` | 8x16 | 65 | 63 | `f17a5a734c14e145232ff38864007ad9f38d2e148f23693c1c30edaca9ecd561` |

Both 16x16 exports contain exactly 118 pixels with alpha zero and 138 with alpha 255, with no intermediate alpha values. Grayscale output opaque counts: 70 white, 37 dark gray, 31 light gray; color output opaque counts: 70 black, 37 red, 31 skin. Individual 8x16 OAM alpha counts add up to the combined 16x16 alpha counts (73+65=138), and the mask is identical across grayscale and colored versions. The colored and grayscale image bytes themselves are different, as expected.

## Strict acceptance boundary

**Now verified for this one frame:** ROM-backed physical CHR mapping at captured boundary, 8x16 hardware OAM tile decoding, group placement and horizontal flipping, index-0 alpha, MesenCE built-in default NES 2C02 palette-code mapping, and exact reference-color RGB on **all 138 opaque pixels in the actual rendered frame**.

**Not verified:** the 118 transparent *background pixels* against an independent background-only reference; an NES background tile/scroll/palette reconstruction; sprite/background priority when they overlap; rendering with alternative custom palettes or video filters; per-scanline sprite-limit behavior; actor classification of every OAM record; animation timing, save-state/input replay, or general sprite coverage.

A source index-zero alpha of 0 is correct decoded sprite semantics, **but proving the background is what is shown at those holes requires a separate background ground truth.** Using the already composited framebuffer as both source and ground truth would be circular.

## Next controlled experiment

Choose the smallest non-destructive experiment that yields an **independent background-only reference** for the same on-screen scene/camera state: e.g. a deterministic emulator save-state plus an emulator-controlled sprites-disabled render of the same frame, or explicit background-plane rendering from correct nametable/attribute/CHR/scroll and palette evidence. Before changing MesenCE hooks, inspect whether the emulator supports capturing the background layer without modifying ROMs or game state, and test timing/coherence on synthetic data. No background bytes or screenshots should be put in GitHub.

**Decision:** Clear *one-pose opaque-pixel RGB* research gate; leave *background transparency and full compositing* gate open.
