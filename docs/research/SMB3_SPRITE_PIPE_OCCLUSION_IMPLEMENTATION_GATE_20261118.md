# SMB3 PRG1 — Expedition 15: Mario's OAM recipes, real pipe occlusion and the implementation gate

Date: 2026-11-18. Scope: **Super Mario Bros. 3 (USA) PRG1 / Revision A only.** This is the last research-to-implementation checkpoint, not a claim that a complete runtime sprite decoder now exists.

## Evidence and authority

**New static original-ROM verification:** Read the owner's `Super Mario Bros. 3.zip` *in memory* and confirmed it contains one iNES `Super Mario Bros. 3.nes` image of **393,232 bytes**, SHA-256 **`4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`**, header hex `4e45531a101040000000000000000000`. Never altered or extracted the ROM to a public working tree. The binary *pattern identities, bytes, and SHA-256 derived mask hashes* below are newly computed from this verified input.

**Static source behavior:** Pinned [Southbird SMB3 disassembly](https://github.com/captainsouthbird/smb3/tree/09b1bd81a788de8ceec664a34094e84ddb463117), especially [PRG029 player draw](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg029.asm#L375-L839), [PRG008 level initialize](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm#L475-L487), [PRG031 OAM reset/DMA/CHR bank routine](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm), [smb3.asm OAM layout](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm#L909-L934). These are interpretations of a disassembly, not yet executed PC traces on this specific save state.

**Independent hardware/emulator confirmation:** [NESdev PPU programmer reference](https://www.nesdev.org/wiki/PPU_programmer_reference), [PPU OAM and sprite priority](https://www.nesdev.org/wiki/PPU_OAM), [8×16 pattern rules](https://www.nesdev.org/wiki/PPU_pattern_tables), [PPU evaluation](https://www.nesdev.org/wiki/PPU_sprite_evaluation), [MMC3 filtered A12 IRQ](https://www.nesdev.org/wiki/MMC3); [MesenCE 2.2.1 PPU sprite implementation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L721-L916), [MMC3](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h), [official Lua API documentation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json), [Lua implementation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Debugger/LuaApi.cpp#L605-L710) at pinned commit `20ba206cef5ba207c21203176d02cb9f43dda9fb`.

**Prior live evidence reused, not revalidated:** SpriteMine's earlier 24-frame MesenCE capture (frame IDs 448385–448408), ROM-correlated six-pattern recipes and A/B/A history are recorded in [Runtime Forensics](SMB3_RUNTIME_FORENSICS.md) and [Player Physics](SMB3_PLAYER_PHYSICS.md). Their original private files were **not** reread or replayed in this expedition. Cross-matching previously reported pixel counts below is meaningful **independent static corroboration**, *not* a new emulator pass.

## Findings 154–176

### 154 — The complete player recipe tables are re-fingerprinted against the owner's original ROM

In-memory PRG1 ranges:

| Original file offset | Contents | Length | SHA-256 |
| --- | --- | ---: | --- |
| `0x3AC10` | 81 biased recipe half-offsets | 81 | `6244cf2be9719ef22a1ada5357104eb781864d9b107a30b0d3b6acfc675fc240` |
| `0x3AC61` | 81 six-pattern player recipes | 486 | `4c655ba8a75e38616af7567e99867b697485ab1bf663a52e59643e0fec7606b5` |
| `0x3AE47` | 81 player-frame CHR 1-KiB page offsets | 81 | `b9e1db86cd863b6b7977b0623276163d2edbeaecce7dac40a330ec90b2b1ebd3` |

These were independently read from the immutable input in this expedition and agree with previously documented CPU addresses in [Runtime Forensics](SMB3_RUNTIME_FORENSICS.md): PRG29 `$CC00/$CC51/$CE37`. Only bytes/hashes are reported, not copyrighted ROM payloads.

### 155 — Player graphics use six *slots*, but six slots are not six visible sprite components

[`Player_Draw`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg029.asm#L400-L573) chooses six recipe pattern bytes, assigning the first three to the *upper* row's OAM pattern fields and last three to the *lower* row, then assigns X/Y and attributes. The special value `$F1` is a **software 'do not render' sentinel** and causes `Y=$F8` on the corresponding OAM entries. The 24-frame data's six pattern fields are not proof that six 8×16 hardware images were visible.

### 156 — The `$F1` sentinel is **not** a blank CHR pattern

For active small-player bank `$53`, the original ROM 8×8 CHR tile `$F0` contains **18 nonzero** 2-bpp pixels and tile `$F1` **62 nonzero** pixels. Consequently, an 8×16 OAM entry with pattern index `$F1` could be visibly nonempty if SpriteMine simply decoded its CHR data. In the SMB3 player interpreter it must instead be suppressed by its **OAM Y rewrite**. Do not equate ROM tile number `$F1` with the hardware concept of an intrinsically transparent tile.

### 157 — Standard Mario owns exactly six known OAM entries, beginning at index 10

The normal [`Level_Initialize`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm#L475-L487) stores `Player_SprOff=$28`. Since OAM entries are 4 bytes each, the six-entry Mario construction occupies CPU shadow OAM **`$0228-$023F`**, physical OAM indices **10–15** when the current offset remains `$28`. The scene may contain other effects/sprites outside this range, and the source does not establish that every level/time preserves that offset. Check `Player_SprOff` at runtime before assigning ownership.

### 158 — The player recipe has a precise but non-obvious two-row mapping

Within the six OAM records rooted at `Player_SprOff`, recipe bytes 0–2 are assigned to pattern fields at local offsets `$0D,$11,$15`, while bytes 3–5 go to `$01,$05,$09`. The first three OAM slots are the **lower row, Y+16**; the last three the **upper row, Y**. A decoder that assumes recipe order equals OAM order reverses the player's halves.

### 159 — Small Mario's three relevant ROM recipes identify two actual 8×16 images each

The immutable PRG1 table stores:

| Logical recipe | Six ROM pattern fields (source order) | Visible 8×16 indexes after `$F1` filtering | 1-KiB CHR bank |
| --- | --- | --- | --- |
| `$3E` walk A | `F1 F1 F1 05 07 F1` | `$05,$07` | `$53` |
| `$3F` walk B | `F1 F1 F1 01 03 F1` | `$01,$03` | `$53` |
| `$40` jump/fall | `F1 F1 F1 19 1B F1` | `$19,$1B` | `$53` |

[`Player_PUpRootPage`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg029.asm#L390-L409) sets the small-player root to `$50`; each of these `Player_FramePageOff` values is `3`, hence `$53` at `PatTable_BankSel+2`. The runtime-selected `Player_Frame` itself remains **unobserved in this expedition**; these are statically matched recipe candidates.

### 160 — Real 8×16 tile selection is governed by OAM tile bit 0, not just PPUCTRL's sprite bank

[NESdev PPU reference](https://www.nesdev.org/wiki/PPU_programmer_reference) and [MesenCE `LoadSprite`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L721-L760) agree that with 8×16 sprites an **odd OAM tile index** addresses PPU `$1000`, and the even index addresses `$0000`; index bit 0 is removed for the upper 8×8 subtile and the next sequential tile provides the lower 8×8. Thus `$05 → $04,$05`, `$07 → $06,$07`, and the correct mapper physical window is R2=`$53` for these normal small-player frames. The PPUCTRL 8×8 sprite pattern table bit does **not** override the per-sprite bit in 8×16 mode.

### 161 — Independently decoded original ROM 2-bpp silhouettes match two prior validation totals

From the verified ROM, using page `$53`, two adjacent 8×16 sprites, each from its even/odd pair, direct bitplane decoding produces:

| Recipe | Zero/transparent pixels (out of 256) | Opaque pixels | Value counts: `0,1,2,3` |
| --- | ---: | ---: | --- |
| `$3E` | 118 | **138** | `118,37,31,70` |
| `$3F` | 82 | **174** | `82,42,36,96` |
| `$40` | 62 | **194** | `62,48,39,107` |

Earlier SpriteMine MesenCE validation independently reported **138/118** for a walking/standing appearance and **194/62** for the rising-jump appearance. Those two matching totals are **static corroboration of the previously observed results**, not independent proof of all 256 pixel positions or correct on-screen sprite flipping. The `$3F` totals are a new deterministic static expected value, not an asserted prior native pixel test.

### 162 — Private-safe deterministic pixel fingerprints for the next test suite

Define a 16×16 canonical unflipped candidate bitmap: concatenate the 8-pixel-wide sprite indexed values left-to-right for each of 16 rows; each value is `(low_bitplane_bit | (high_bitplane_bit << 1))`. Hash the **256 raw indexed bytes**, and separately hash a 256-byte alpha mask where each nonzero indexed byte becomes `01`, otherwise `00`.

| Recipe | 256-byte indexed SHA-256 | 256-byte alpha SHA-256 |
| --- | --- | --- |
| `$3E` | `59a99166faf0abdb429c7cb265dfc8333dce2cc2c8852e0ba1ac57fd87d359ac` | `cca62efc7fa9a1d1809afed6987e8fe48348ae74a9a0f3d058a07bfe19a162d8` |
| `$3F` | `a04ee7c9349a05404140af3e5cc1a84eb91678b54a8be81f1e339e2454c5efe1` | `eec9c262edcdc3d8d71036ffcbf52c74fd3e2517efdd305c75afef8693ff25ce` |
| `$40` | `9d97e76ab09aaf2c205fc8f25c5a4f40d66d5130a4b42b89dce03e341f03862c` | `9d7b1ac228ca04e421b18190a0ed159688516fb73ef142601e6f9064505996bb` |

These are reproducible **private-ROM-derived local-model expectations**. Record them in public test code as hashes/metrics only, while keeping copyrighted source CHR bytes and resulting artwork private. Because `Player_FlipBits` can reorder and mirror tiles, hash values apply to this explicitly defined **unflipped canonical** orientation, not necessarily the capture's onscreen pixels. Independent implementation and fixture validation are still required.

### 163 — Runtime flash invincibility can suppress Mario's OAM without changing the pose recipe

[`Player_Draw`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg029.asm#L415-L446) decrements `Player_FlashInv` and conditionally jumps around writing the new patterns/attributes/positions. Thus `Player_Frame` and available CHR pixels can remain stable while Mario visually flashes or disappears. SpriteMine must record **actual PPU/OAM state for each frame**, not infer always-visible player pixels from a recipe alone. Need runtime probe to learn the exact OAM-clear order and timing.

### 164 — Starman can cycle the player sprite palette while geometry remains unchanged

[`Player_Draw`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg029.asm#L438-L498) chooses the low two palette-select bits from `Counter_1` and invincibility timers; the wear-off path slows that cycle. In the same source, `Temp_Var1` merges those palette bits into the OAM attribute values. This creates different visible colors with identical tile/CHR/position. It is separate from Expedition 14's **palette RAM** recolor: OAM palette-selection and the palette's contents are independent dimensions.

### 165 — Mario's behind-background state is an OAM attribute, not evidence of background masking alone

The player routine tests `Player_Behind` / `Player_SandSink` and ORs OAM attribute bit `$20` (behind BG) into all six sprite records. [NESdev sprite priority](https://www.nesdev.org/wiki/PPU_sprite_priority) confirms this suppresses the chosen sprite against a nonzero BG pixel **after** sprite selection. A character's logical world position or fixed scene geometry does not by itself identify the per-pixel visibility mask.

### 166 — OAM symmetry is sometimes synthesized by the draw routine

The source compares the first two lower-row pattern IDs; if they match, it forces opposite H-flip bits across mirrored pairs. The subsequent `Player_FlipBits` path can additionally exchange pattern fields, adjust X, and offset the assembly during `Player_Flip` somersaults. A ROM 'recipe' therefore contains **input components**, not the final four-byte OAM records; verifying six tile fields without their positions/attribute bits does not establish a complete visible pose.

### 167 — Offscreen clipping is deliberate Y rewriting, with a separate status-bar threshold

[`Player_Draw`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg029.asm#L731-L784) computes an offscreen flag and suppresses entire OAM rows around screen-Y thresholds `$B0` and `$C0`, writing `$FF` to row Y values; its `$F1` sentinel pass separately writes `$F8`. The software is not clipping a cropped PNG after the fact. The exact resulting rendered scanlines depend on OAM's Y-minus-one behavior and the PPU/IRQ scanline split, so don't equate `$B0` to a universally fixed final alpha cutoff without live comparison.

### 168 — SMB3 has a real four-hardware-sprite pipe-entrance occlusion mechanism

The source branch after the main six-player sprite setup checks `Level_PipeMove` and, when nonzero, programs **four 'mask' 8×16 sprite records** into `Sprite_RAM+$00,$04,$08,$0C`: the first four OAM entries (indices 0–3). It places them around `Pipe_PlayerX/Y`, sets pattern ID `$77`, and marks each with attribute `SPR_BEHINDBG=$20`. Source comments describe them as masking Mario through the pipe entrance. These mask sprites have **higher OAM priority than Mario's default indices 10–15**, making a true hardware foreground/behind-BG occlusion case. [`Player_Draw` mask branch](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg029.asm#L793-L839).

### 169 — Pipe occlusion uses two priority stages, which a flattened overlay cannot reproduce

When a mask sprite pixel is nonzero, the **earlier OAM index wins** sprite-sprite priority over Mario; its `behind BG` bit can then cause the background's nonzero pixel to win. This 'sprite occludes another sprite, then loses to background' mechanism is exactly the NES [sprite priority behavior](https://www.nesdev.org/wiki/PPU_sprite_priority), and is independently present in [MesenCE `GetPixelColor`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L836-L916). If both the mask pixel and BG pixel are zero, Mario may remain visible through that location. **Actual pipe-mask pixels and intended traversal were not observed live**; the exact visual result requires fetch-time CHR bank, mask pattern and BG opacity.

### 170 — The `$77` pipe-mask CHR is not guaranteed opaque by its OAM tile number

A targeted original ROM cross-check shows that *if* the mask pattern `$77` were interpreted with 8×16 sprite bank `$53`, its corresponding physical CHR 8×8 tiles `$76/$77` would have only **35+42 = 77 nonzero 2-bpp pixels out of 128**, **not 128**. Other potential player CHR banks also vary. Thus the disassembly's informal 'should be completely opaque' comment is **not a validated universal property**, and SpriteMine must not replace `$77` with an artificial fully opaque rectangle. This **does not prove a native pipe visual glitch**, because the actually selected bank/frame during pipe traversal has not been traced. It is a specific high-value negative test against a tempting shortcut.

### 171 — Only the first eight qualifying sprites per scanline are rendered under normal NES limits

[NESdev PPU OAM](https://www.nesdev.org/wiki/PPU_OAM) establishes the eight-sprites-per-scanline evaluation limit and OAM order. [MesenCE `LoadExtraSprites`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L782-L819) explicitly supports an optional sprite-limit-removal path controlled by emulator settings. **Capture whether the limit is enabled**, since the same 256-byte OAM can give a different framebuffer in a configured emulator than on an original NES. Pipe masks (up to four) plus Mario and other actors increase the importance of this gate; a live over-limit scanline for World 1-1 has not yet been demonstrated.

### 172 — Emulated 8×16 Y position is offset one displayed scanline from OAM's stored Y

[NESdev PPU evaluation](https://www.nesdev.org/wiki/PPU_sprite_evaluation) confirms an OAM sprite's Y coordinate encodes the top displayed Y minus one due to next-scanline evaluation. PPU [8×16 vertical flip](https://www.nesdev.org/wiki/PPU_programmer_reference) reverses both subtiles and pixel order. Source [MesenCE `LoadSprite`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L721-L760) explicitly handles scanline-relative offsets and `verticalMirror`. Tests must cover `Y=$FF` (wrap/off-top), `$F8` (software hide), `$B0/$C0` (status cutoff), and X=0/255 and flip bits. Avoid simply treating OAM Y as the displayed top-left Y.

### 173 — The HUD and MMC3 IRQ require *scanline provenance*, not an end-frame OAM/CHR sample

Expedition 13 established the normal [HUD IRQ](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm#L2176-L2301) overrides sprite CHR mapping with blank bank `$7E`. But MMC3 IRQ scheduling is **PPU A12-edge-triggered**, not simply a 'scanline=192' software if statement: [NESdev MMC3](https://www.nesdev.org/wiki/MMC3), [MesenCE MMC3 `NotifyVramAddressChange`](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h#L316-L350). Hence a post-IRQ OAM/CHR dump can contain real Mario entries whose old graphics were displayed earlier in the same frame. Record the **actual IRQ event, mapper banks before/after and frame/PPU timing**; `$C000=192` is a programmed counter, *not* the experimentally measured exact line.

### 174 — The pinned MesenCE Lua API has the necessary *read-only memory surfaces*

Official [Lua documentation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json) explicitly lists `emu.memType.nesSpriteRam` (hardware primary OAM), `nesSecondarySpriteRam`, `nesPaletteRam`, `nesChrRom`, `nesNametableRam`, `nesDebug` (side-effect-free CPU reads), and `nesPpuDebug` (side-effect-free effective PPU reads). It exposes `emu.read`, `emu.convertAddress`, `emu.getCpuCycleCount`, `emu.addEventCallback` (`irq`, `nmi`, `startFrame`, `endFrame`) and `emu.addMemoryCallback` (`exec`, `read`, `write`). This is a concrete API-backed basis for the next **bounded and read-only** MesenCE capture harness. None of these APIs was newly run on the owner's Windows machine; script callback performance and precise timing must be checked.

### 175 — Memory-write callbacks execute **before** writes; a passive trace must not return a value

Pinned [LuaDocumentation.json](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json#L23-L35) specifies read callbacks are invoked **after** reads while write callbacks are invoked **before** writes. A callback returning an integer can **change** the game state by replacing the read/write value. The planned SpriteMine observer must record the incoming value, **return nil**, and avoid calling side-effectful `nesMemory` or `nesPpuMemory` reads in tracing code. For a writable register `$8000/$8001`, a callback reading register state inside a pre-write notification may still see the *previous* mapper state. Capture write order and reconstruct the command+bank change from incoming values; validate against actual post-event mapper/PPU observations.

### 176 — Lua framebuffer documentation and implementation differ: RGB is exposed, not internal indexed PPU pixels

The [MesenCE Lua docs](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json#L229-L256) describe `emu.getScreenBuffer` / `getPixel` as returning ARGB, but the pinned [`LuaApi::GetScreenBuffer/GetPixel` implementation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Debugger/LuaApi.cpp#L648-L710) first passes the PPU frame through the video filter, then masks each value with `0xFFFFFF` before returning it to Lua. Thus the Lua API yields **processed 24-bit RGB components** (no meaningful alpha), *not* Mesen's internal 16-bit indexed pre-RGB framebuffer. For an exact raw indexed/scanline source, investigate a **separately approved and narrowly scoped emulator instrumentation** option only if needed after the first bounded Lua gate. Do not confuse the two, and do not rely on the public documentation's 'ARGB' wording for alpha correctness.

## Decision: stop research-only spelunking here, switch to implementation

The strongest immediately buildable feature is **a private-ROM-aware static 8×16 player-sprite renderer and bounded live OAM+PPU evidence validator**, NOT a generalized asset classifier, automatic all-SMB3 sprite exporter, or UI redesign.

### Gate A — deterministic source-independent tests (no emulator required)

- Read the immutable verified PRG1 image from the private FIXTURE path. Verify exact full-ROM hash, iNES structure, all three player table hashes above and CHR page `$53` hash **`dcec01e246088b7654fe954cac7babbff983156af0412ea6e30e028398a95d48`**.
- Independently implement 8×8 NES two-bitplane decoding, 8×16 odd/even tile-bank selection, H/V flips, OAM Y+1 semantics, alpha=`pixel!=0`, bounds and deliberate `$F1` suppression as a **player recipe interpretation rule**, not a hardware rule.
- Compare all three canonical 16×16 indexed/alpha hash pairs and 138/174/194 opacity counts. Include synthetic unit tests for cases `$F1` interpreted as actual CHR (must be nonblank), black-but-opaque indexed pixel, even OAM tile selecting PPU $0000, 8×16 vertical flip swapping subtile order, and left-edge masking.
- No derived media or copyrighted bytes enter GitHub; only code, tests with synthetic data, length/digests and documentation.

### Gate B — narrow MesenCE Lua live capture (no custom C++ required yet)

- Begin at a **previously verified SMB3 PRG1 save state and frame**. Record ROM hash, MesenCE version/binary hash, saved state hash, controller input history and frame/cycle identity.
- Capture **hardware OAM** `nesSpriteRam`, **shadow OAM** CPU `$0200-$02FF` via `nesDebug`, `Player_Frame`, `Player_SprOff`, `Player_FlipBits`, `Player_SpriteX/Y`, `Player_Suit`, `Player_FlashInv`, `Player_StarInv`, `Level_PipeMove`, `Player_Behind` and `Player_SandSink` at documented points. Resolve actual addresses from the pinned disassembly/verified assembly mapping, not guesses.
- Observe MMC3 write sequence at CPU `$8000/$8001` with **pre-write** callbacks, track IRQ/NMI event timestamps and capture `nesPpuDebug`/palette RAM and processed screenshots. **Avoid indiscriminate PPU $2007 tracing** until impact is tested; sampling memory safely by type is supported.
- Compare the real 24-frame `$3E → $3F → $3E → $40` recipe sequence against observed `Player_Frame` RAM, all six OAM records, 16×16 raw pixel masks and the corresponding visible framebuffer. Validate 8-sprite-limit configuration and capture any emulator-specific video filter settings.
- A/B/A: identical owner-provided save/input fixture before and after enabling the read-only probe, same hashes/frames. No gameplay writes, cheats, altered ROM or synthetic states presented as native game evidence.

### Gate C — first **real hardware occlusion** acceptance

- Choose a naturally reached World 1-1 pipe entrance from a deterministic save/input recipe; trace `Level_PipeMove` transition, `Pipe_PlayerX/Y`, `Player_SprOff` and OAM indices 0–3 (four masking sprites) versus indices 10–15 (Mario).
- Read **actual** mask pixel coverage using the *observed bank* at each scanline. Reconstruct final masks through OAM priority → BG priority → HUD blank CHR/sprite limits. Confirm any difference between `$77`’s commented 'opaque' intention and its physical CHR mask. Do **not** force a solid overlay.
- Export an internal private evidence bundle: original ROM and emulator hashes; save/input/clock; raw OAM and CHR-bank trace; BG and sprite pixel/priority mask; pixel comparison with original indexed or explicitly noted RGB baseline; documented missing/unobserved portions.
- Treat Gate C as **observed original pipe occlusion**, not an assertion that all SMB3 foreground objects are decoded.

### Gate D — level reconstruction after Mario's pixel gate

Take Expedition 12's 864-byte **candidate** World 1-1 secret-room Tile_Mem (not a native verified map) and compare actual area-load Tile_Mem → 54-byte PPU pattern strip → 14-byte attribute strip → pixel output using the same provenance/test machinery. Move to the stochastic main World 1-1 cloud generator only when RNG state and source input/timing are captured. This makes level and sprite reconstruction share *verified PPU evidence* without conflating their decoders.

## Implementation boundaries and repository hygiene

- Preferred integration design: **Python read-only ROM/CHR/recipe parser + tested pure pixel composer**; replaceable MesenCE Lua event/read capture adapter; JSON provenance records; optional private PNG preview/export. Preserve `raw` (ROM-backed), `decoded` (source/ROM algorithm) and `captured` (emulator-observed) labels distinctly.
- Windows-only validation. Use `F:\Dev\ROMMAGE\SOURCE` for feature-branch repo work; `F:\Dev\ROMMAGE\TOOLS` for MesenCE; `F:\Dev\ROMMAGE\FIXTURE\SMB3` for immutable ROM, save states and private game captures; `F:\Dev\ROMMAGE\REPORTS` for private validation reports and `OUTPUT` for exports if present. Public GitHub: only code, synthetic tests, hashes and write-ups; **no extracted copyrighted game graphics or ROMs**.
- Continue from the *current* implementation branch/PR state after reviewing GitHub; research branch `research/smb3-rom-spelunking-20261116` is documentation, not an automatic implementation base to merge blindly. Review source license before adapting third-party code.
- Definition of first 'complete' feature: tested static decoder with immutable PRG1 hashes, tested pure 8×16 OAM semantics including flips/transparency, reproducible 24-frame live captures with no A/B/A perturbation, coordinate/mask/priority matching and explicit gaps. The private pipe test is the next higher-value acceptance milestone.
- If native MesenCE cannot expose a true indexed PPU framebuffer via Lua, label screenshot comparison RGB/video-filter-dependent and use CPU/PPU state and derived masks as additional corroboration; defer C++ until a specific missed acceptance requirement justifies it.

**Stop condition:** This is sufficient to begin engineering. Do not continue speculative archaeology while Gate A and the bounded Gate B are unimplemented.
