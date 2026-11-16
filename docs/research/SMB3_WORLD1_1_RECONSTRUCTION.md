# SMB3 PRG1 — World 1-1 construction and runtime map research

Status: **ROM-fingerprinted source stream; command interpretation derived from disassembly; final map/runtime comparison pending**  
Research date: 2026-11-16  
Target: **Super Mario Bros. 3 (USA), PRG1 / Revision A — World 1-1**  
Related: [PR #20](https://github.com/87otlto-coder/SpriteMine/pull/20), [existing runtime report](SMB3_RUNTIME_FORENSICS.md), [player physics and animation](SMB3_PLAYER_PHYSICS.md).

No new native emulator capture, complete level decoder or final framebuffer comparison was produced for this note. This document preserves the construction-level discoveries and separates source instructions from generated level state, collision and pixels.

## 1. Provenance and evidence classification

**Verified in PR #20:** the original nine-byte World 1-1 header begins at ROM file offset 0x1FB92; the 264-byte layout stream begins at file offset 0x1FB9B, within physical 8-KiB PRG bank 15. The stream uniquely matches the verified PRG1 ROM and Southbird's World 1-1 disassembly data.

- Layout stream SHA-256: ef2d1e5a95cd51391e5651af0cdd9ab0cba36985e4cf971d3eed7c34d506892a
- Header reader reports 11 horizontal screens; initial X=24/Y=384; timer 300; see PR #20 for the rest of the decoded header and validation limitations.
- The original source ROM, images and gameplay state remain in local FIXTURE only, not in this repository.

**Rechecked statically in this session:** the instruction boundaries, generator/fixed/junction counts, extra-parameter positions, ground-run records and the separate object-list entries are consistent with the source data and loader dispatch. This recheck parses the **disassembly's byte declarations**, relying on PR #20 for the exact verified ROM stream fingerprint.

**Not yet verified:** executing the complete construction algorithm against actual ROM bytes in a separately tested decoder; comparing the complete output with live 0x6000 tile RAM, PPU nametables, collision or gameplay positions.

Pinned source references: Southbird SMB3 disassembly [World 1-1 layout](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/levels/Plains/1-1.asm), [World 1-1 object list](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/objects/1-1.asm), [PRG030 loader and renderer](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm), [PRG014 generators](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg014.asm), [PRG015 tile tables](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg015.asm), [PRG005 object spawner](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg005.asm).

## 2. Layout is an instruction stream, not a raster tile array

Following the PRG030 loader's dispatch and extra-byte rules, the source stream parses into:

| Command class | Count |
| --- | ---: |
| Generator | 71 |
| Fixed-size | 14 |
| Junction | 1 |
| Extra data bytes following certain generators | 5 |
| Final 0xFF terminator | 1 byte |

Byte accounting: 86 three-byte commands × 3 = 258 bytes; five additional fourth bytes; one terminator = **264 bytes**. This is why treating the stream as arbitrary three-byte records would misalign later commands.

The header/configuration, primary three-byte command, selected generator and optional additional width byte each have separate semantics. The parser must implement the exact dispatch and lengths; do not infer general lengths from one example. A junction command saves alternate entrance coordinate metadata, not an ordinary terrain tile.

The initial instruction (source offset 0x00, bytes 00 00 03) selects LoadLevel_RandomPUpClouds. The generator attempts **60 cloud-tile writes** using game random state. Consequently an exact rendered map cannot be determined solely by copying the static stream without reproducing the relevant random initialization and overwrite order.

## 3. Principal ground runs and gaps

The source's five solid-ground run commands (generator index 11) provide:

| Layout byte offset | Initial column (16px units) | Top row | Width byte | Nominal inclusive covered columns |
| --- | ---: | ---: | --- | --- |
| 0x03 | 0 | 26 | 0x26 | 0–38 |
| 0x3A | 39 | 25 | 0x1C | 39–67 |
| 0x56 | 72 | 26 | 0x15 | 72–93 |
| 0x96 | 96 | 26 | 0x04 | 96–100 |
| 0x9A | 104 | 26 | 0x47 | 104–175 |

The ground generator writes an initial edge, continuing columns, and a final edge, giving width byte + 1 columns in these cases. The second run spans two vertical ground rows (25–26) under the specified shape parameter; the others have top row 26.

The run coverage leaves three **gaps between these runs**:
- Columns 68–71 (64 px).
- Columns 94–95 (32 px).
- Columns 101–103 (48 px).

A *separate* later source instruction at stream offset 0xF8 (bytes 1A 8B A2; generator index 9, LoadLevel_Pitfall) constructs a narrow pit in previously covered ground around columns 139–141, replacing the center column 140 with sky and producing flanking edges. Because generators can overwrite tiles, these are **source-derived ground constructions and likely holes**, not yet a validated final collision map.

The nominal 11-screen horizontal layout spans columns 0–175 (176 16px columns). This does not mean every tile in the 11-screen region has been reconstructed.

## 4. Other recognizable source-level features

The dispatcher and generator names identify these World 1-1 instruction positions:

| Feature selected in source | Column | Row |
| --- | ---: | ---: |
| First vertical pipe | 22 | 23 |
| Hidden 1-Up brick | 90 | 8 |
| P-Switch brick | 127 | 23 |
| Alternate-area vertical pipe | 141 | 7 |
| Goal-region generator | 155 | 0 |

These are **source command starting positions**, not independently validated final rendering coordinates or proof of interactive behavior at runtime. Large generators (especially the goal) produce multiple tiles from one instruction.

For additional run instructions, an audit of generator IDs in the disassembly found:
- 14 coin-run commands specifying **23 coin-tile placements**.
- Six brick-run commands specifying 18 tile placements.
- Nine wood-block-run commands specifying 18 tile placements.
- Four coin-question-block runs specifying six placements.

These are command-level requested writes; some placements can be overwritten by later generators or changed by game state. Do not use them as counts of collectible coins or final visible tiles.

## 5. Enemy and interactable object placements are separate

The World 1-1 map selects a second source list, W101O, in PRG bank 6. The list begins with a source header byte 0x01 of unresolved meaning, contains **15 object placement records**, and terminates with 0xFF. The source labels resolve to:

| Object identity from source labels | Source records | Columns |
| --- | ---: | --- |
| Goomba | 4 | 14, 33, 52, 55 |
| Venus Fire Trap | 1 | 22 |
| Red Troopa | 2 | 36, 131 |
| Paragoomba | 1 | 59 |
| Hopping Green Paratroopa | 3 | 83, 86, 89 |
| Green Troopa | 1 | 92 |
| Green Piranha Plant | 1 | 112 |
| Fire Piranha Plant | 1 | 116 |
| End-level card object | 1 | 168 |

Source naming is **not** confirmation that all entries are simultaneously active or visible. PRG026 LevelLoad_CopyObjectList copies the list into live placement RAM; PRG005 Level_ObjectsSpawnByScroll then considers nearby placements as scrolling progresses.

For ordinary horizontal scrolling, the object-spawn position can be computed from the camera with a rightward look-ahead of 272 pixels (256 + 16), or an offset 32 pixels to the left of the camera for leftward scrolling, aligned to tile columns. Initial-scene setup simulates scrolling to populate nearby objects. Spawning also depends on flags and available slots, so mathematical trigger positions are **not actual observed spawn frames**.

The standard spawner searches five active slots (0–4); special objects can use different slots and paths. Level_ObjectsSpawned marks whether source placements have been spawned; some disposal paths clear the flag and allow later respawn.

Known source-mapped RAM regions:
- 0x7B00–0x7B0F: start index into the object list by screen.
- 0x7B10–0x7B3F: source-placement spawn flags.
- 0x7B40–0x7BCF: up to 48 three-byte placement records.

For SpriteMine: **ROM placement**, **live object state**, **hardware OAM components** and **visible sprite** are separate provenance entities.

## 6. Game-managed tile memory and incremental renderer

The disassembly declares Tile_Mem at CPU 0x6000–0x794F, **6,480 bytes**, sufficient for fifteen horizontal screens of 16 × 27 logical 16x16 tiles (432 bytes per screen). An 11-screen World 1-1 would nominally use 4,752 tile bytes; this is a capacity calculation, **not a measured initialized memory dump**.

A horizontal-level logical tile can be addressed conceptually as:

    0x6000 + (screen_index * 0x1B0) + (row * 16) + column_within_screen

Follow the actual boundary handling and horizontal/vertical mode when implementing the decoder.

PRG030 Scroll_DoColumn consumes logical tile IDs to construct 8x8 pattern-column data. Source buffer addresses:
- 0x0382–0x03B7: Scroll_PatStrip, 54 bytes.
- 0x03BA–0x03C7: Scroll_AttrStrip, 14 bytes.

Scroll_Do_AttrColumn derives palette attributes from the logical tile’s upper two bits, packaging four 16x16 tile palette choices into each NES attribute byte. Scrolling updates VRAM incrementally, so a static full logical map and the current PPU screen can legitimately differ during update timing.

PRG015’s Plains 16x16-tile layout maps one tile ID to four 8x8 pattern references. Source-derived example: logical tile 0x55 (ground top-left) selects top-left 0x0A, top-right 0x01, bottom-left 0x5A, bottom-right 0x61; the logical tile’s top bits also imply relative palette group 1. These are **pattern indices**, not independently checked CHR-ROM bytes, physical bank mappings or actual RGB pixels.

## 7. Runtime state and collision interpretation

The Plains tile attribute/collision thresholds loaded into Tile_AttrTable at CPU 0x7E94–0x7E9B are:

| Tile ID range | Floor minimum | Wall/head minimum |
| --- | --- | --- |
| 0x00–0x3F | 0x25 | 0x2D |
| 0x40–0x7F | 0x50 | 0x53 |
| 0x80–0xBF | 0xA0 | 0xAD |
| 0xC0–0xFF | 0xE2 | 0xF0 |

The game's probe positions, slopes and special cases determine how these comparisons are used. A tile drawing that *looks* solid does not define universal solidity.

The 128-byte Level_BlockGrabHitMem array at 0x7E02–0x7E81 records certain collected coins and hit-block history. Level_ChangeTile_ByTempVars can update the logical tile memory. P-Switch handling can substitute an **effective collision tile** (e.g. coin ↔ brick) without necessarily rewriting every stored source tile. Video update events may change visible PPU state later than the logical-state change.

Thus a correct reconstruction needs at least:
1. Raw ROM construction commands and their provenance;
2. Constructed logical map **at a specified state/seed**;
3. Current logical/interactable object state and effective collision semantics;
4. PPU nametable, attribute, CHR-bank and palette state;
5. Actual visible render at a specified frame/scanline.

## 8. Recommended decoder and tests

Implement an **SMB3/World1-1-only read-only decoder** before generalizing.

Suggested intermediate representations:
- Command record: source ROM file offset, variable byte length, opcode/index, starting coordinates and raw hash (no copyrighted dump).
- Tile-write event: command ID, world screen/column/row, before/after logical tile ID, generator, deterministic order, required game-state input.
- Constructed-map snapshot: ROM fingerprint, tileset, RNG/input history, level flags, per-screen 16×27 logical tile IDs, completeness mask.
- Object placement: source list offset, object symbol/type, source coordinate, spawn-flag index and separately observed runtime slot identity.
- Renderer provenance: logical tile ID → 8x8 pattern refs → physical MMC3 bank mapping → PPU attrs → frame pixels.

**Acceptance gates:**
1. Parser consumes exactly all 264 source bytes; 86 commands, five extra bytes, one terminator; no overrun or unsupported instruction silently skipped.
2. Every identified ground, pipe, block, pit and goal generator has deterministic synthetic tests for tile writes and ordering, clipping and boundaries.
3. Random cloud output is deterministic for a captured seed/state, with explicit unknown values when seed cannot be recovered.
4. Final logical map is compared to a real, read-only gameplay Tile_Mem snapshot, with source/ROM identity and frame documented.
5. Ground gaps and collision behavior are verified independently against ROM bytes, player collision probes and actual gameplay observations.
6. CHR, palette and PPU rendering fidelity are checked separately; no panorama is promoted to a decoded level.

**Next decisive experiment:** from the accepted immutable save state, snapshot Tile_Mem, camera world X and Mario world X/Y around 448396–448408. Reconstruct the underfoot tile positions and correlate the first loss of solid support to the Player_InAir and Player_Frame transitions. Do not claim the captured Mario fall occurred at any particular World 1-1 pit until world position, loaded level identity and map state are observed.

## Boundaries and license

No ROM, save state, assembly source, extracted sprites, level binaries or audio are stored here. Source facts are paraphrased with links. The source disassembly lacks an explicit reuse license in the project’s earlier review; obtain a separate license assessment before copying its code or large tables. SpriteMine’s original ROM and private A/B/A fixtures remain immutable and local.
