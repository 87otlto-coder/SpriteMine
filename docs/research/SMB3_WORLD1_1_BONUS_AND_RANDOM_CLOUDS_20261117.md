# SMB3 PRG1 — Expedition 12: World 1-1's reciprocal bonus room, construction geometry and stochastic clouds

Date: 2026-11-17. Target: **Super Mario Bros. 3 USA PRG1 / Revision A** only.

## Evidence boundaries

- **ROM verified, static only:** Read the owner's supplied `Super Mario Bros. 3.zip` in memory, containing one 393,232-byte iNES image. Unmodified image SHA-256: `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`. Original main level stream SHA-256 `ef2d1e5a95cd51391e5651af0cdd9ab0cba36985e4cf971d3eed7c34d506892a` independently rechecked. No original content was rewritten, extracted to GitHub, or published.
- **Source derived:** The command ID mapping, tile-write footprints, RNG transformation and control-flow interpretation are reconstructed from Southbird's [SMB3 pinned disassembly](https://github.com/captainsouthbird/smb3/tree/09b1bd81a788de8ceec664a34094e84ddb463117), commit `09b1bd81a788de8ceec664a34094e84ddb463117`. They have not been independently validated by running an SMB3 interpreter or MesenCE.
- **Not tested:** Native MesenCE, frame/cycle timing, complete final Tile_Mem, PPU nametable, visible bitmap, interactive collisions, seed replay, and actual traversal of either pipe.
- Companion [World 1-1 construction baseline](SMB3_WORLD1_1_RECONSTRUCTION.md), [block interactions](SMB3_BLOCK_INTERACTION_SPELUNKING_20261117.md), [Expedition 10 event provenance](SMB3_EVENT_PRODUCER_CHAINS_20261117.md). Third-party assembly licensing review remains required before reuse.

## Findings 94–109

### 94. Reciprocal World 1-1 main/bonus header pointers — ROM verified

The main layout header at file offset `0x1FB92` (CPU `$BB82`) has alternate layout pointer CPU `$BC93`. Its target bonus header at file offset `0x1FCA3` has reciprocal alternate layout pointer CPU `$BB82`. The main header's alternate object pointer is CPU `$C006` (the disassembly's `Empty_ObjLayout`), while the bonus header points back to CPU `$C527` (the source's `W101O` original object layout). Therefore **the original World 1-1 metadata defines a two-node, bidirectionally linked area graph**, not just a one-way bonus destination. Sources: [main header](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/levels/Plains/1-1.asm), [bonus header](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/levels/Plains/1-1Bonus.asm), [junction alternate-pointer initialization](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L1589-L1617).

### 95. Bonus room stream boundaries — ROM verified

The bonus header has nine bytes at `0x1FCA3–0x1FCAB`, SHA-256 `211cb8053814ee568312e7137704e9cf21311c4ec8885f25f31328b43908db0b`. The bonus stream starts at `0x1FCAC`, terminates at `0x1FCF8`, and has exactly **77 bytes including one terminal $FF**; SHA-256 `37b5d2266e2ee509010b07cc366e8904e51560c70aeec5f1da179f276486b3c6`. Main stream ends immediately before the bonus header: main stream at `0x1FB9B`, length 264, ends `0x1FCA2`. Thus both source regions are contiguous in this verified PRG1 image. Do not assume these offsets for any revision other than the checked image.

### 96. Bonus room command grammar and counts — ROM bytes + source dispatch

The 77-byte bonus stream parses into **22 three-byte command headers**, **ten fourth-byte parameters**, and **one terminator**: `22*3+10+1=77`. It contains 21 generator commands and one junction command. Generator indices: `40` (10), `22` (9), `26` (1), `27` (1). In [Plains generator dispatch](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg015.asm#L125-L235), these indicate ten top-decorated diamond-block rectangles, nine coin runs, and two ceiling-pipe styles. The [TopDeco generator](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg014.asm#L2079-L2178) reads a **fourth width byte**, unlike ordinary three-byte records. Its type 40 uses the diamond-block top/follower values. This extends the original World 1-1 parser's five-extra-byte ground-run rule: **bonus layouts also require TopDeco fourth-byte handling**.

### 97. Requested bonus coin and rectangle footprints — static emulator-independent model, not final tile map

Nine coin runs request `12` 16x16 coin placements, after decoding lower-nibble inclusive width in [LoadLevel_BlockRun](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg014.asm#L1173-L1216). Ten diamond rectangles request `285` tile writes from their `width_parameter+1` by `shape_low_nibble+1` dimensions. A coordinate-union model yields **269 distinct rectangle cells**, i.e. 16 repeated writes, with **no coordinate overlap between those 269 cells and the 12 coin-run positions**. This assumes precisely the source's start-coordinate and row/column progression rules; it does not incorporate the two ceiling-pipe generators, persistent item memory, actual randomized game state, collision, the final tile memory, or visuals. Hence **12 is a requested-placement count, not a proven player-collectible count**. [Bonus layout source](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/levels/Plains/1-1Bonus.asm).

### 98. The bonus room is a separate header-driven configuration, not merely the main room at a different coordinate

Main header declares 11 screens, default Plains background palette and overworld music; bonus header declares 2 screens, a different background palette and underground music. Both use Plains tileset. The precise start position, scrolling flags and music handoff follow [PRG030 header decoder](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L4173-L4415); music can preserve an active temporary track. An area capture must preserve header identity and output state, not merely the original World 1-1 world index.

### 99. Plains initial tile clearing covers fifteen 432-byte screens with overlapping writes — source derived

[PRG015 `LevelLoad_TS1`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg015.asm#L96-L124) invokes both `Tile_Mem_ClearB` and `Tile_Mem_ClearA` for Y values 0..239. [PRG030 helpers](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L4023-L4074) distribute writes across all fifteen 432-byte horizontal screens. Within each screen, A covers offsets 0..239; B covers offsets 192..431; intersection 192..239 is 48 bytes. Their **union exactly covers 432 bytes per screen**. A Python set-union sanity check verified this arithmetic, not the ROM runtime or executed writes. The clear operates on all fifteen reserved screens even when the level header declares eleven or two.

### 100. World 1-1's first generator writes 60 randomized cloud tiles — but screens are mapped asymmetrically

The first main World 1-1 construction command selects [`LoadLevel_RandomPUpClouds`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg014.asm#L2725-L2787). It calls `Randomize` once per candidate and then draws two bytes from the pool. The second byte is used for screen/column selection. When its high nibble is $F, the routine adds $20 with 8-bit wrap, mapping values $F0–$FF to $10–$1F: **screen 15 maps to screen 1**. The other high-nibble values select screens 0..14. Over 256 possible input-byte values, screen 1 has 32 encodings and each other screen has 16. These are **encoding multiplicities**, not verified RNG frequency probabilities. The generator may write beyond World 1-1's declared eleven screens (up to screen 14) without escaping the fifteen-screen tile-memory capacity.

### 101. Cloud graphic choice is correlated with X column, not an independent random selection

The same second random byte, following any screen-15 remap, supplies both location and the graphic choice `X & 3`; value 3 becomes value 1. Therefore graphic indices map **column modulo 4** as `0->0, 1->1, 2->2, 3->1`. Their name symbols are `TILE1_PUPCLOUD_M/F/S`. Of 256 possible byte values, graphic index 1 occurs 128 times, while 0 and 2 occur 64 times each. These are **mapping counts**, not observed cloud counts. SpriteMine's procedural level generator must reproduce this location/graphic correlation rather than independently sampling cloud appearance.

### 102. Cloud Y row distribution is similarly nonuniform

The first random byte's low nibble is converted as `0–9 -> same`, `10–15 -> 1–6` via subtraction by nine. Thus output rows are only 0–9; rows 1–6 have two low-nibble preimages, rows 0,7,8,9 one. This yields a specific, source-backed positional bias that can be independently checked once actual RNG state is available. Again, avoid treating nibble multiplicity as a statistical guarantee of 60 observed placements.

### 103. Random clouds may be overwritten by subsequent construction instructions

The cloud generator directly writes logical tile memory without checking whether that coordinate was previously written. It is the **first** World 1-1 instruction, and the loader processes following commands in stream order. Repeated random coordinates can overwrite prior clouds and later authored generators can overwrite cloud cells. Thus 60 candidate writes do **not** entail 60 distinct surviving cloud tiles. Actual survivors depend on RNG state, instruction sequence and logical-map writes.

### 104. RNG is shared with an eligible NMI path

[`Randomize`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L4619-L4637) rotates a multi-byte `Random_Pool` after XORing two bit taps to produce its carry. It does not draw from independent entropy on every cloud command. The [PRG031 interrupt path](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm#L1600-L1622) also calls `Randomize` when `VBlank_TickEn` is nonzero. Therefore deterministic cloud reconstruction may require not just an initial random seed but also exact intervening RNG calls and interrupt/update ordering. No frame-level seed has been captured.

### 105. Scene transitions rebuild object spawning separately from collected-item memory

A [general junction](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L1577-L1617) loads the alternate layout/object pointers and toggles `Level_JctFlag`. Its display restart jumps into [`PRG030_897B`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L1361-L1398), **after** the fresh-level code that clears `Level_BlockGrabHitMem`. Meanwhile, [`LevelJunction_PartialInit`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm#L692-L733) resets `Level_ChangeReset`, and [`Level_DoChangeReset`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg005.asm#L6174-L6263) clears object states and all 48 spawn flags. These are different persistence domains: coin/hidden-1-Up bitmap can persist across a junction, while on-screen objects and spawn flags are refreshed. This is a static call-chain prediction, not evidence that any particular enemy has already respawned in a captured World 1-1 replay.

### 106. Source object records are not necessarily visible enemies

[`Level_ObjectsSpawnByScroll`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg005.asm#L4921-L5140) has special cases for `OBJ_AUTOSCROLL`, `OBJ_TREASURESET`, `OBJ_BONUSCONTROLLER`, `OBJ_TOADANDKING` and several spawn/event controllers. Some are control records whose side effects occur **without allocating an ordinary enemy object slot**; `OBJ_ENDLEVELCARD` instead forces slot 6, whereas ordinary objects scan slots 4..0. Therefore the number of placement records does not equal the number of rendered characters or sprite instances. The World 1-1 source list has 15 placement records, but this fact cannot be used to infer 15 concurrent OAM objects.

### 107. Full World 1-1 acceptance requires both areas and their state transitions

The immutable ROM and disassembly establish a main/bonus layout-pair target, but not yet its complete authentic tilemap. Proposed acceptance must cover: both headers/streams, exact dispatch and extra-byte grammar; player state and area transition; preserved per-half collected-item bitmap; refreshed object-spawn bookkeeping; conditional tile/PPU output; a captured RNG state, and native MesenCE comparison of both fully generated logical maps. The [primary World 1-1 research document](SMB3_WORLD1_1_RECONSTRUCTION.md) already notes random clouds and incomplete final maps. Do not mark the entire stage complete based on a static panorama or solely the main area.

### 108. Each direction has a different encoded landing recipe — original ROM fields and pinned-source decoder

The main layout contains one junction command at layout offset `0xF5` (ROM file offset `0x1FC90`): it populates junction lookup **slot 8**, with Y/exit descriptor `$42` and X descriptor `$80`. The bonus layout contains one junction command at layout offset `0x49` (file offset `0x1FCF5`): it populates **slot 1**, with Y/exit descriptor `$71` and X descriptor `$19`. These three-byte commands were read directly from the owner's original PRG1 ROM. [`LoadLevel_StoreJctStart`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg014.asm#L5005-L5025) indexes the 16-slot Y/X junction arrays using the low nibble of the first byte; the other two command bytes are the stored Y/X descriptors. [`LevelJct_General`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L1750-L1909) selects the lookup by the **departing** area Player_XHi for horizontal levels and decodes the target Player position.

For a source-position index matching the stored slot, the predicted targets are:

| Route | Departure lookup slot | Target Player world X | Target Player world Y | Pipe exit direction | Starting vertical scroll |
| --- | ---: | ---: | ---: | --- | --- |
| World 1-1 → bonus | 8 | `$0088` (136 px) | `$00F0` (240 px) | 2: down | `$B0` |
| Bonus → World 1-1 | 1 | `$0918` (2328 px) | `$0180` (384 px) | 1: up | `$EF` |

Both descriptors leave vertical-level mode clear. The low X byte gains the decoder's center `$08`; vertical Y positions are selected from `LevelJct_YLHStarts`. These are **source/ROM-derived candidate landing states**, **not observed transition frames**. The entry-path premise (departing Player_XHi=8 or 1), subsequent screen/camera adjustments and actual exit behavior must be confirmed in MesenCE. The main area's source pipe at tile column 141 resides in screen 8, while the bonus room's source ceiling pipes include screen 1, making the keys plausible without proving traversal.

### 109. A level graph edge carries more than destination identity

The two reciprocal link pointers identify target layouts, but each direction also has a different **entry slot**, **X/Y landing recipe**, **pipe-exit direction**, **initial vertical scroll**, and **object pointer**. A future asset catalog should represent an area transition as a directed edge with these fields, separate from the destination's own header and from live player/camera state. This avoids conflating identical rooms entered from different pipes or start positions. Only the two World 1-1 edges above are statically established; broader behavior needs evidence.

## Narrow native verification plan

1. Under the original verified PRG1 ROM and immutable MesenCE save-state, capture `Random_Pool`, `Level_JctCtl`, `Level_JctFlag`, current layout pointers, `Level_BlockGrabHitMem` and area-specific Tile_Mem at the start and end of each load. Record the number and timing of `Randomize` calls (NMI vs loader) with physical bank PC, avoiding active RAM modification.
2. Verify both ROM headers and command stream hashes at runtime; compare main and secret room dispatch IDs, generated tile-memory 16x27 screen contents, and PPU output separately.
3. Traverse the bonus/return junction under deterministic inputs. Collect a coin, cross the transition, return; check which region of `Level_BlockGrabHitMem` changes and whether collected placements reappear. Observe object reset/spawn state independently from tile persistence.
4. Test whether all 12 bonus coin-run source positions survive complete construction and can be collected; test initial 60 random cloud writes against final survivors, and compare map outputs across seeds.
5. Preserve the actual ROM, MesenCE build, save-state and inputs solely in the private `F:\Dev\ROMMAGE\FIXTURE\SMB3` tree; commit only evidence metadata and source-backed research, never ROM bytes or extracted stage imagery.

## Architectural implication

A level is a **graph of source layout headers**, each with its own construction stream and configuration, linked by runtime junctions. Reconstructed geometry is **ordered side-effectful execution**, not a decompressed image. Rendering, effective collision, object placement, and collected-item persistence must remain independent provenance layers. Maintain a path for exact RNG state/history and reproducible area transitions before guaranteeing any screen as a faithful source reconstruction.
