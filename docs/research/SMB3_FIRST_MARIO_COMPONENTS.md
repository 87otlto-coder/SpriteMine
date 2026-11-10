# First candidate Mario hardware sprite composition — 2026-11-10

## Provenance and privacy

Evidence came from the owner's private, user-supplied SMB3 PRG1 ROM ZIP and MesenCE capture:

- ROM SHA-256: `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`
- ROM SHA-1: `6BD518E85EB46A4252AF07910F61036E84B020D1`
- Capture manifest: `phase_0000442741_1794295259.json`, frames **442741–442742**
- Attached capture ZIP contains **all 12 raw binary snapshot buffers**, despite its filename naming only the fourth endFrame pattern file
- No copyrighted capture buffer, game graphics or ROM bytes are included in this document or committed to GitHub

## Real data validated

The attached raw buffers have the expected sizes (4 × 8192-byte PPU, 4 × 256-byte OAM, 4 × 32-byte palette). The source ROM checksum exactly matches the authenticated SMB3 PRG1 ROM. The trace contains **114** MMC3 register write events and **zero** dropped writes.

Replaying the observed pre-write CPU register values through the MMC3 CHR bank model reproduces **all three frame-boundary PPU snapshots whose physical bank state is known**, byte-for-byte (8,192 bytes each):

| Boundary | Physical CHR 1 KiB banks, PPU $0000–$1FFF | Captured and predicted PPU SHA-256 |
|---|---|---|
| Frame 442741 start | Initial registers unavailable; do not guess | `3262677cd7ad5e9401f48044596532477a605f3fd7eb050dda4d43456bd05c64` (observed only) |
| Frame 442741 end | 92,93,94,95,126,126,126,126 | `0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918` |
| Frame 442742 start | 8,9,96,97,83,4,34,79 | `3262677cd7ad5e9401f48044596532477a605f3fd7eb050dda4d43456bd05c64` |
| Frame 442742 end | 92,93,94,95,126,126,126,126 | `0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918` |

The 8 KiB startFrame hash differs from the earlier in-game PAUSE capture because **the effective ROM bank mapping differs**. This reinforces why sprite reconstruction must carry per-frame physical CHR bank provenance. The first startFrame physically matches the later buffer by hash, but its initial register state is not independently evidenced by this trace.

## Mario-position OAM hardware components

Both captured frames have only two OAM entries with potentially on-screen Y coordinates:

| OAM index | Screen X,Y | 8x16 tile ID | Attribute | PPU top/bottom tile bases | Absolute ROM top/bottom offsets |
|---|---|---|---|---|---|
| 10 | 87,162 | 7 | 0x40 (horizontal flip) | 0x1060 / 0x1070 | 347248 / 347264 |
| 11 | 95,162 | 5 | 0x40 (horizontal flip) | 0x1040 / 0x1050 | 347216 / 347232 |

Both use palette slot 0. Palette RAM entries for sprite palette indices 1,2,3 are **0x16,0x36,0x0F** (22,54,15); RGB mapping is not yet validated against MesenCE output.

### Manual independent composition

The two 8×16 PPU-indexed components were decoded from the **verified second startFrame** PPU buffer, horizontal-flipped independently and placed at the recorded OAM coordinates. They form a **16×16 silhouette recognizable as small Mario** (cap, face and body) with index-0 transparency. Combined nontransparent pixels: **138** of 256.

The observed register trace updates PRG registers before scanline 193; the first CHR bank-register changes in both sampled frames occur at approximately **scanline 193**. The sprite component covers scanlines 162–177, preceding those CHR changes. This supports the inference that the verified startFrame CHR mapping remained in effect for these OAM components, within the observed MMC3 bank-write model. It does **not** directly measure every PPU sprite-fetch event.

## Code and repeatability

The research decoder `research/mesence/sprite_components.py` supports explicit `--group-oam 10,11`, composite RGBA **diagnostic grayscale** preview and a metadata-only group record. It does not auto-identify characters, substitute guessed missing components, perform sprite evaluation, or report a pixel-perfect original image. Synthetic tests verify OAM positioning, 8×16 CHR indexing, flips, index-0 transparency, and group composition. Generated previews remain local to FIXTURE.

Suggested usage after refreshing `research/smb3-emulator-feasibility`:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
& "F:\Dev\ROMMAGE\SOURCE\SpriteMine\.venv\Scripts\python.exe" ".\research\mesence\sprite_components.py" "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE\phase_0000442741_1794295259.json" --rom "F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip" --sample 3 --group-oam "10,11" --output-dir "F:\Dev\ROMMAGE\FIXTURE\SMB3\SpriteComponents\phase_0000442741_1794295259"
~~~

Adjust the original ROM location if needed; the CLI refuses overwriting any existing previews, or output into a Git checkout.

## Acceptance boundary

**Verified:** source ROM identity, three same-session PPU byte matches, two hardware components' tile interpretation/positions/flip/transparency and a recognizable candidate Mario 16×16 composition.

**Not verified:** full composited-screen pixel agreement, the exact emulator display RGB palette, per-scanline hardware sprite evaluation and priority, actor classification or animation completeness, or save-state/input replay. Complete Phase 3 Sprite Inspector status remains **open**.

**Next:** capture a screen RGB buffer at a known frame boundary while also retaining corresponding PPU/OAM/CHR provenance; compare actual sprite pixels and colors at the recorded coordinates. A simple screenshot alone is not sufficient evidence without phase alignment.


## Next validation: rendered RGB screen from same emulator frame

The new rendered-pixel research script pairs a completed MesenCE endFrame RGB24 buffer with same-session startFrame OAM/PPU/palette, tracked MMC3 bank writes and independent ROM-backed bank verification. The analyzer checks color-index consistency at the two Mario candidate OAM component positions (10 and 11) and reports neighboring one-pixel shifts without automatically fixing alignment. See docs/research/RENDER_RGB_CORRESPONDENCE.md for the Windows procedure.

This experiment has **not yet run on the owner's actual MesenCE screen**. Its fitted RGB classes are statistical descriptors of the capture, not a independently verified palette or final sprite/priority renderer.
