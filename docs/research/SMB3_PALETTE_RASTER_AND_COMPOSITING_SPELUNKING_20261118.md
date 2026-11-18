# SMB3 PRG1 — Expedition 14: palette state, PPU colors, sprite alpha and raster compositing

Date: 2026-11-18. Target: Super Mario Bros. 3 (USA) PRG1 / Revision A, focusing on the World 1-1 main and secret bonus layouts. Research-only; no emulator tests or copyrighted assets committed.

## Evidence classes

- **SMB3 source-derived, not original ROM reverified this expedition:** Southbird disassembly commit [`09b1bd81a788de8ceec664a34094e84ddb463117`](https://github.com/captainsouthbird/smb3/tree/09b1bd81a788de8ceec664a34094e84ddb463117), primarily [PRG027 palette tables/loader](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg027.asm#L1447-L1896), [PRG026 fade/update machinery](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L1997-L2239), [PRG007 rotation](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg007.asm#L334-L449), [PRG008 runtime player recolor](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm#L1064-L1137), and [PRG030 area setup](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L2400-L2427).
- **Independent emulator source confirmation:** MesenCE 2.2.1 pinned commit [`20ba206cef5ba207c21203176d02cb9f43dda9fb`](https://github.com/nesdev-org/MesenCE/tree/20ba206cef5ba207c21203176d02cb9f43dda9fb), especially [BaseNesPpu.cpp palette semantics](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/BaseNesPpu.cpp#L65-L163), [NesPpu.cpp sprite/background arbitration](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L836-L916), [NesDefaultVideoFilter.cpp palette conversion](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesDefaultVideoFilter.cpp#L45-L153), and [debug palette tooling](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Debugger/NesPpuTools.cpp#L469-L504).
- **Independent hardware references:** [NESdev PPU palettes](https://www.nesdev.org/wiki/PPU_palettes), [PPU rendering](https://www.nesdev.org/wiki/PPU_rendering), [PPU registers](https://www.nesdev.org/wiki/PPU_registers), and [NTSC video](https://www.nesdev.org/wiki/NTSC_video).
- **Not performed:** No reread of the user's private ROM; no live MesenCE execution, screenshots, native debugger/scanline captures or A/B/A, no test runs, and no ROM/asset commit. Expedition 12 contains prior PRG1 ROM-confirmed World 1-1/bonus headers and candidate map; this expedition reuses those **previously** established source header values without claiming fresh ROM verification.

## Findings 131–153

### 131 — World 1-1 main and bonus have different source-selected backdrop entries

The World 1-1 main header selects Plains (`Level_Tileset=1`) BG palette set **0**, sprite set **8**. Its reciprocal secret-room header selects the **same Plains tileset**, BG palette **5**, sprite set **8**. [Original source layouts](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/levels/Plains/1-1.asm) and [bonus layout](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/levels/Plains/1-1Bonus.asm) carry these fields. [`PalSet_Plains`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg027.asm#L1468-L1495) gives **target backdrop palette index $3C** for BG set 0 and **$0F** for set 5. These are NES palette **indexes, not RGB**. Initial fade, overlays or runtime writes may change the PPU-visible color; the ROM bytes and actual screenshot were not rechecked here.

### 132 — Background and sprite palettes are selected separately from the same tileset's palette families

[`Setup_PalData`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg027.asm#L1765-L1831) takes `Palette_By_Tileset[Level_Tileset]`, copies one 16-entry background palette selected by `PalSel_Tile_Colors` and one 16-entry sprite palette selected by `PalSel_Obj_Colors` into the 32-byte master target `Pal_Data`. Because main and bonus specify sprite set 8, they share an **initial source palette family for object colors**, subject to player state, overrides and runtime changes. The two palette selectors are not a single composite palette number.

### 133 — The code supports an exceptional palette override, but reachability is not established

When `Pal_Force_Set12` is nonzero, `Setup_PalData` follows an alternative pointer-selection/copy path and resets that variable afterward; it copies 32 consecutive bytes directly rather than independently indexing the background/sprite sets. Source inspection proves the branch exists; **this expedition did not establish its activation in World 1-1**. The override is another reason raw header values alone are not sufficient for every live palette.

### 134 — Palette target, fade/update buffer and actual PPU RAM are distinct provenance states

[`Pal_Data`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm#L2740-L2755) is the 32-byte master target. [`Palette_Buffer`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm#L2154-L2163) (actual declaration in the 0x07C1 region) stores the current/updating palette state; [MesenCE `WritePaletteRam`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/BaseNesPpu.cpp#L85-L106) implements the PPU's own independent $3F00–$3F1F palette storage. SpriteMine must capture which of the three it is showing, especially during level transitions.

### 135 — Shared backdrop entries are explicitly normalized by SMB3

After loading the sprite palette, `Setup_PalData` copies `Pal_Data[0]` into `Pal_Data[16], [20], [24], [28]`. The source palette tables also repeat the chosen background color in positions 0/4/8/12 of the active background set. [MesenCE PPU](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/BaseNesPpu.cpp#L76-L106) confirms special aliasing of $3F00 with $3F10 and the other $x4/$x8/$xC positions with their sprite counterparts. Do not model these as eight independently visible sprite colors.

### 136 — `$FF` in the source sprite palette is not a real NES palette output color

Source sprite-family tables use `$FF` in the unused color-zero slots. `Setup_PalData` overwrites the color-zero entries of the resulting sprite palette with the current background color. NESdev confirms that **sprite pattern pixel 0 is transparent**, even if a nominal palette-zero byte has a value. Avoid interpreting source `$FF` as a white pixel or alpha-visible entry.

### 137 — Fade initialization deliberately begins below the target's brightness tier

[`Palette_PrepareFadeIn`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L1997-L2047) initializes the 32-byte active buffer by subtracting `$30` from each target palette index, using `$0F` if it underflows. [`Palette_DoFadeIn`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L2048-L2098) subsequently uses the target's low nibble or adds `$10` toward the master value. For ordinary main World 1-1 backdrop target `$3C`, the prepared first value is therefore **`$0C`**, not `$3C`; bonus-room target `$0F` prepares as `$0F`. These are code-derived setup values, not the PPU contents at an observed gameplay frame.

### 138 — Fade steps are queued video updates, not instantaneous 32-byte swaps

The fade routine initializes `Fade_Level=4`, `Fade_Tick=4`, then sequences buffer changes as the counter advances. It sets `Graphics_Queue=6` when an update is due; [PRG030 `Video_Upd_Table`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L60-L75) maps queue entry 6 to the palette update command structure. [`Video_Misc_Updates`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L3297-L3340) ultimately writes PPU bytes from that update stream. Thus do not infer exact display color solely from `Fade_Level` without also tracing VBlank dispatch and PPU palette writes.

### 139 — The game has a structured VRAM update bytecode distinct from scrolled tile strips

`Video_Misc_Updates` recognizes target VRAM address, byte count, one-byte repetition and horizontal (+1) or vertical (+32) increment mode. The same pathway is used for whole-palette fade updates, individual UI/status overlay modifications and dynamic graphics updates. A decoder that applies only `Scroll_PatStrip`, `Scroll_AttrStrip` and `TileChng_VRAMCommit` is incomplete for final screen reproduction. The game-specific update bytecode is source backed; timing of competing updates remains unverified.

### 140 — Mario's runtime power-up recolor writes exactly three PPU palette bytes

[`Level_SetPlayerPUpPal`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm#L1064-L1137) emits a graphics-buffer command targeting **PPU $3F11–$3F13** and updates `Palette_Buffer[0x11..0x13]` to match. The RGB appearance of a player sprite can therefore change **without rewriting its CHR data or OAM tile indices**. The source selects entries for Mario, Luigi, Fire, Frog, Tanooki, Hammer or statue states, with special fallback behavior for small/big/raccoon. This routine's inclusion in active gameplay must be traced before attributing a particular frame's tint.

### 141 — The runtime player recolor does not itself rewrite the master `Pal_Data`

The `Level_SetPlayerPUpPal` code writes `Graphics_Buffer` and `Palette_Buffer` but no `Pal_Data` entry in that routine. A later call to target-based fade setup could produce a different temporary palette even if the player's suit has not changed; whether this scenario actually occurs in World 1-1 is **unverified**. This is a provenance warning, **not** a claimed SMB3 palette bug.

### 142 — SMB3 supports gameplay-queued color cycling without CHR changes

[`ColorRotation_Do`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg007.asm#L338-L445) executes only with nonzero `RotatingColor_Cnt`. It selects among four palette-color indexes based on the low two bits of the counter and writes small VRAM update commands through the graphics buffer. Therefore a visual color effect can occur without changes to logical tile IDs, 8×8 CHR patterns, nametables, or OAM. **This does not establish that the color-rotation effect is active in an ordinary World 1-1 capture.**

### 143 — Non-high-bit color rotation writes `$3F10–$3F13`, indirectly changing the universal backdrop

In the branch where the original `RotatingColor_Cnt` has bit 7 clear, `ColorRotation_Do` prepares a **four-byte** update beginning at `$3F10`, choosing a rotating first byte unless the counter has reached zero (then it uses `Palette_Buffer+$10`). MesenCE and NESdev independently confirm `$3F10` aliases `$3F00`. Thus, **if this branch is executed and the command committed**, it can color-cycle the entire screen's universal backdrop even though its address appears to be in the sprite palette region. This is a conditional, source/hardware-derived effect, not a live observed World 1-1 artifact.

### 144 — High-bit color rotation modifies background palette entries differently

When bit 7 is set, `ColorRotation_Do` instead queues an eight-byte write beginning at **`$3F04`**, mixing rotated colors and preserved `Palette_Buffer` entries. It touches parts of BG palette ranges 1 and 2; it does not simply set a single background color. Combined with hardware palette-zero aliasing, only the non-zero pattern-index entries will contribute normal non-transparent tile pixels. Capture this effect separately from the non-high-bit `$3F10` path if it becomes relevant to a reproducible SMB3 fixture.

### 145 — A graphical layer can change through palette-only, CHR-only or nametable-only events

Source paths already confirmed across Expeditions 11–14:
- P-Switch can overlay collision semantics and choose a different 2-KiB CHR bank without bulk rewriting tile map;
- normal level animation changes physical CHR pages while preserving nametable pattern numbers;
- player suits can change sprite color entries without changing OAM/CHR;
- fade/color rotation update palette state without replacing tile patterns;
- block edits and scroll updates write nametable data.
These independent degrees of freedom must not be collapsed into one 'asset changed' state. Their actual interaction and timing must be recorded in a native capture.

### 146 — PPUMASK grayscale and emphasis apply *after* palette-index selection

NESdev [PPU registers](https://www.nesdev.org/wiki/PPU_registers) and pinned [MesenCE `UpdateColorBitMasks`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/BaseNesPpu.cpp#L155-L163) show PPUMASK grayscale bit 0 masks the 6-bit palette value with `$30`; bits 5/6/7 apply NTSC red/green/blue emphasis. These modify **displayed output**, not the underlying palette RAM write data. MesenCE also handles PAL/Dendy's reversed red/green emphasis semantics. We have **not** observed these modes active in the user's World 1-1 trace; nonetheless a generic screenshot-to-raw-color verification must capture PPUMASK.

### 147 — Emulated RGB is a configurable transformation, not a universally canonical ROM color

NESdev [NTSC video](https://www.nesdev.org/wiki/NTSC_video) explains that an NTSC NES generates composite video, not per-pixel RGB. [MesenCE `NesDefaultVideoFilter`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesDefaultVideoFilter.cpp#L45-L153) builds a **512-entry output lookup** covering 64 base indices × 8 emphasis states and may apply user-selected palettes, hue, saturation, brightness and contrast. Therefore **matching a screenshot's ARGB bytes requires recording the emulator video settings and PPU model**, not only ROM identity and palette RAM. Archive underlying NES palette indexes separately from converted PNG RGB values.

### 148 — PPU composite transparency is a 2-bpp pixel-state decision, not an RGB-color comparison

NESdev [PPU palettes](https://www.nesdev.org/wiki/PPU_palettes) and [PPU rendering](https://www.nesdev.org/wiki/PPU_rendering) establish that 2-bpp pattern value zero is transparent for sprite pixels. BG pattern value zero reveals the universal backdrop `$3F00` when no opaque sprite is in front. The color index `$0F` means black, **not** 'transparent'; a black-valued nonzero sprite pixel is fully opaque for priority and collision tests. SpriteMine's exported alpha must come from 2-bpp pixel values (plus actual hardware masking if claiming visible output), not a selected RGB chroma key.

### 149 — OAM order can defeat intuitive BG priority rules

[MesenCE `GetPixelColor`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L836-L916) evaluates active sprites in OAM priority order, then applies sprite-vs-background priority. NESdev documents the *sprite priority quirk*: a higher-priority OAM sprite marked 'behind background' can obscure a lower-priority OAM sprite even if the latter is marked 'in front'. The hardware output depends on **OAM order, both nonzero pixel masks, background pixel and priority**, not only coordinates and palette. This is particularly relevant to assembling Mario from multiple 8x16 hardware sprites.

### 150 — The emulator exposes raw NES palette state and RGB previews as distinct debugger data

Pinned [MesenCE `NesPpuTools::GetPaletteInfo`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Debugger/NesPpuTools.cpp#L469-L504) reports `MemoryType::NesPaletteRam`, `RawPalette[0..31]` and separately calculated `RgbPalette` entries. This suggests a strong *read-only* validation path for SpriteMine: capture 32 raw palette bytes plus PPUMASK and filter settings from the emulator, and compare independently against predicted `Pal_Data` and observed frame RGB. Do not assume the debugger palette preview alone captures mid-frame palette changes or raw fetch-time mappings.

### 151 — MesenCE retains a 16-bit per-pixel palette-index framebuffer before RGB conversion

[`NesPpu::GetScreenBuffer`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L1235-L1251) returns a `uint16_t*` buffer; [`BaseNesPpu::UpdateColorBitMasks`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/BaseNesPpu.cpp#L120-L163) can encode the selected six-bit NES palette color together with three emphasis bits into this representation. [`NesDefaultVideoFilter::DecodePpuBuffer`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesDefaultVideoFilter.cpp#L182-L196) then maps these values through the configurable `_calculatedPalette[512]` RGB conversion table. This is a particularly promising **indexed-frame capture surface** for pixel-exact cross-checks, if a supported emulator integration can expose it. **Do not assert that the public MesenCE Lua API directly exposes this internal pointer; integration feasibility remains untested.**

### 152 — MesenCE's video output may be overscan-cropped independently of emulated PPU state

The same `DecodePpuBuffer` reads the raw 256-pixel-wide PPU buffer at offsets shifted by `GetOverscan().Top/Left`, and emits the configured output `FrameInfo.Width×Height`. Consequently a screen PNG can be spatially cropped even when the original emulated PPU image remains a full 256×240 picture. For SpriteMine, compare source coordinates against **uncropped PPU pixel coordinates first**, then apply a separately identified presentation crop. Record output dimensions, overscan settings and video filter in any pixel-exact screenshot acceptance report.

### 153 — A post-composite color-index buffer cannot recover per-sprite alpha and OAM provenance

[`NesPpu::GetPixelColor`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L836-L916) chooses the final background/sprite palette entry before it writes the frame color. An ordinary 16-bit color-index framebuffer therefore records the **selected final color**, not all of the rejected background pixels, overlapping sprite masks, or exact originating OAM component identity. Two opaque sprite pixels and a background pixel can produce the same final index; alpha is not recoverable from the visible image alone. For complete SpriteMine sprite reconstruction, keep a separate time-indexed OAM/CHR/pattern-opacity/priority trace, even when raw indexed framebuffer comparison succeeds.

## Minimal native verification matrix

| Probe | Baseline World 1-1 | Bonus-room entry | During fade | With player-suit change | Conditional rotation |
| --- | --- | --- | --- | --- | --- |
| Area/level header and tileset | Mandatory | Mandatory | Mandatory | Same scene | If active |
| `PalSel_Tile_Colors` / `PalSel_Obj_Colors` / `Pal_Force_Set12` | Record | Record | Record | Record | Record |
| `Pal_Data[32]` and `Palette_Buffer[32]` | Compare | Compare | Per update | Compare before/after | Compare before/after |
| Actual PPU palette RAM `$3F00..$3F1F` | Compare | Compare | Per commit | Compare before/after | Per commit |
| `PPUMASK`, PPU model, full video filter settings | Record | Record | Record | Record | Record |
| OAM, CHR mapping, sprite priority and 2-bpp masks | Selected pixels | Selected pixels | If visible | For actor | If visible |
| Actual emulator framebuffer/raw indexed pixels and processed RGB | Ground truth | Ground truth | Per frame | Before/after | Before/after |

1. Use the owner's verified immutable PRG1 and a reproducible MesenCE save-state with documented inputs/frame identifiers. Store local test/capture products only within `F:\Dev\ROMMAGE\FIXTURE\SMB3` or research `REPORTS`, never GitHub.
2. First load World 1-1 and its bonus area at unambiguous entry/after-fade states. Compare `Pal_Data[0]`, `Palette_Buffer[0]`, PPU `$3F00` and the displayed backdrop before concluding the target $3C/$0F values are used.
3. Trace exactly one `Level_SetPlayerPUpPal` call and the resulting `$3F11–$3F13` PPU writes, then verify the player sprite's colors and OAM/CHR remain distinguishable.
4. For any naturally triggered rotation, record whether the producer uses $3F10 or $3F04 branch, VRAM commit timestamp and resulting raw PPU palette. Do not force speculative gameplay conditions or modify ROM.
5. Capture raw 2-bpp pattern masks, OAM ordering, Sprite/BG priority, PPUMASK and per-scanline mapper banks to validate alpha/occlusion against original screen pixels. Compare raw NES color indices first; only then compare converted RGB with documented emulator filter settings.

## Engineering implication

Separate at minimum five representations: (1) original-ROM palette family/table, (2) state-selected `Pal_Data` target, (3) `Palette_Buffer` active software state and queued graphics commands, (4) actual time-indexed PPU palette/PPUMASK/CHR/OAM/nametable state, and (5) video-filtered final RGB output. Preserve per-pixel *pattern-zero alpha and priority* separately from RGB. Never promote source-derived palette predictions or a plausible screenshot to validated original framebuffer output.
