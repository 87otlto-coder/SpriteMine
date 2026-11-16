# SMB3 PRG1 — Player collision, motion, and animation research

Status: **source-derived + analytical model; native transition tracing pending**  
Research date: 2026-11-16  
Game: **Super Mario Bros. 3 (USA), PRG1 / Revision A**  
Related: [PR #19](https://github.com/87otlto-coder/SpriteMine/pull/19), [draft PR #20](https://github.com/87otlto-coder/SpriteMine/pull/20), [runtime evidence ledger](SMB3_RUNTIME_FORENSICS.md), [World 1-1 reconstruction](SMB3_WORLD1_1_RECONSTRUCTION.md).

This document records reproducible findings, not a claim that a complete animation, collision emulator, or level has been decoded. **No new emulator run or capture was performed for this research note.** The disassembly is a research reference and its symbol names require runtime confirmation on the verified PRG1 image.

## Evidence classification

- **Captured/independently validated:** the existing 24-frame A/B/A timeline, frame PNGs, spritesheet and OAM/ROM source associations, as accepted in PR #19/#20. The private capture data remains outside Git.
- **Verified static correlation:** PR #20's ROM-fingerprinted 81-entry player recipes and 144 matching OAM tile fields (six tile fields per frame, not 144 independent poses).
- **Source-derived:** behavior directly followed from the PRG1 disassembly, including collision probes, tile thresholds, gravity and animation selection.
- **Modeled:** predicted vertical positions from an explicitly assumed initial state.
- **Unresolved:** actual RAM register values, executed code path, camera/world coordinates and terrain under Mario during frames 448396–448408.

References use the [Southbird SMB3 disassembly at commit 09b1bd81](https://github.com/captainsouthbird/smb3/tree/09b1bd81a788de8ceec664a34094e84ddb463117), particularly [PRG008](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm), [PRG030](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm), [PRG015](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg015.asm) and [smb3.asm symbols](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm). This text paraphrases findings; it does not copy third-party assembly.

## 1. Existing measured sequence and recipe linkage

Private accepted timeline: F:\Dev\ROMMAGE\FIXTURE\SMB3\Animations\right-8-31-e6bd441caa\timeline.json  
Timeline SHA-256: 212fad937f7474078716a70e83227d9fc8fb9230a755748002a9ce9c0ffa034c  
Emulator frames: 448385–448408 (24 consecutive entries).

| Frames | Hold length | Source-matching recipe | Meaning in source | Captured screen X |
| --- | ---: | --- | --- | ---: |
| 448385–448389 | 5 | 0x3E | small Mario, walking pose A | 128 |
| 448390–448395 | 6 | 0x3F | small Mario, walking pose B | 128 |
| 448396–448399 | 4 | 0x3E | walking pose A again | 128 |
| 448400–448408 | 9 | 0x40 | small Mario, standard jump/fall | 128 |

Exactly three RGBA appearances occur in four holds. In the last nine-frame hold, the appearance does not change while the recorded Y positions are 98, 98, 99, 100, 101, 103, 105, 107, 109. These Y values are **screen coordinates from capture records**, not a direct world-Y trace.

The PRG1 symbols explicitly identify PF_WALKSMALL_BASE = 0x3E and PF_JUMPFALLSMALL = 0x40. The small-player ground movement routine, GndMov_Small in PRG008, chooses the jump/fall recipe when Player_InAir is nonzero (subject to alternate high-speed and movement conditions). PR #20 correlates source recipes with OAM patterns, but **has not observed Player_Frame RAM during these frames**.

## 2. Source execution order and the possible transition delay

The main Player_Update path in PRG008 runs the player control/movement logic and scrolling before calling Player_DetectSolids. It later processes special tiles/frames and issues another draw. In the ordinary small-player movement path, the current animation recipe can therefore be chosen **before** collision detection flags loss of ground support.

Consequently, an edge transition could set Player_InAir late in one update, then select PF_JUMPFALLSMALL on the next update. This is a possible one-update effect, not an experimentally confirmed explanation for frame 448400. Draw calls and other animation overrides mean a single frame-boundary snapshot cannot by itself prove the instruction sequence.

Relevant routines: Player_Update, Player_Control, GndMov_Small, Player_CommonGroundAnims, Player_DetectSolids, Player_SetSpecialFrames, Player_Draw.

## 3. Collision probes and tile semantics

For ordinary non-sloped levels, Player_DetectSolids uses offset tables for **two ground and two forward-facing collision probes**. Their offsets vary with Mario's height (small/ducking versus big), upward/downward motion, his position within a 16-pixel tile and facing/side. Sloped levels use different probe positions, shape lookup tables and edge handling. Visible sprite transparency is **not** a collision mask.

The logical tile is fetched by Player_GetTileAndSlope / Player_GetTileAndSlope_Normal from the game-managed, horizontally screen-chunked tile map (see companion level research). The tile's top two bits select one of four ID groups. On flat floors the engine compares the fetched ID to tileset-specific minimum values for floor or wall/head solidity.

Plains tileset 1 thresholds loaded into CPU RAM 0x7E94–0x7E9B:

| Tile ID group | Floor threshold | Head/wall threshold |
| --- | --- | --- |
| 0x00–0x3F | 0x25 | 0x2D |
| 0x40–0x7F | 0x50 | 0x53 |
| 0x80–0xBF | 0xA0 | 0xAD |
| 0xC0–0xFF | 0xE2 | 0xF0 |

These are **thresholds used by the relevant collision path, not universal per-tile solidity flags**. For example, logical ground tile 0x55 exceeds both thresholds for its group; logical sky tile 0x80 does not meet its group’s floor threshold. Tileset-specific special behavior, slopes, water, P-Switch substitutions and exceptions still apply.

In the ground-check branch, if neither foot probe meets the floor threshold and Mario was previously grounded, the routine can zero Player_YVel and set Player_InAir. On contact it can realign Player_Y, clear Player_InAir, zero Y velocity and reset other state. Head collisions and walls follow distinct branches.

Source routines: PRG008 Player_DetectSolids, Level_CheckGndLR_TileGTAttr; PRG030 Player_GetTileAndSlope_Normal, Fill_Tile_AttrTable_ByTileset; PRG015 Tile_Attributes_TS1.

## 4. A nine-frame gravity fit — numerical test, not direct observation

Source behavior:
- Player_JumpFlyFlutter can add 5 to Player_YVel in an airborne update. When certain upward-motion and held-jump conditions are met, it may instead add 1. Power-up and water paths can differ.
- Player_ApplyVelocity treats signed velocity as 4.4 fixed-point and accumulates the fractional component before updating the position.
- Player_ApplyYVelocity caps ordinary positive falling velocity at FALLRATE_MAX = 0x40.

A **specific hypothetical state** fits all nine captured screen-Y values exactly:

1. At frame 448400, screen Y is 98, vertical velocity is zero, fractional position accumulator is 0x80, and vertical camera offset remains unchanged.
2. For each subsequent frame k=1…8, gravity increments velocity by 5, then fixed-point integration advances Y.
3. Predicted integer displacement after k updates is floor((128 + 40 * k * (k + 1)) / 256).

| Frame | Assumed Y velocity | Predicted Y | Captured Y |
| --- | --- | ---: | ---: |
| 448400 | 0x00 | 98 | 98 |
| 448401 | 0x05 | 98 | 98 |
| 448402 | 0x0A | 99 | 99 |
| 448403 | 0x0F | 100 | 100 |
| 448404 | 0x14 | 101 | 101 |
| 448405 | 0x19 | 103 | 103 |
| 448406 | 0x1E | 105 | 105 |
| 448407 | 0x23 | 107 | 107 |
| 448408 | 0x28 | 109 | 109 |

**Result: 9/9 predicted integer Y positions match.** The initial fractional accumulator is **not uniquely determined**: in this simplified model, initial phases 0x70–0xAF also fit. Other hypotheses (including vertical camera motion or different initial velocity) have not been ruled out. This is a strong explanatory fit, **not verification that these velocities were actually present in RAM**.

The observed camera X behavior also needs care: screen X is constant at 128, while PR #20 notes changing PPU horizontal scroll metadata. Screen X cannot be substituted for world X.

## 5. Animation is stateful, velocity-dependent, and not necessarily visually unique

Player_CommonGroundAnims selects walking tick thresholds from the magnitude of horizontal velocity, shifted right by three bits. The source threshold table begins 7, 6, 5, 4, 3, 2, 1, 1. Faster movement generally reaches its next logical walk phase sooner. For Small Mario, Player_WalkFramesByPUp defines four logical phases that alternate two recipe identities (A–B–A–B).

Therefore: a logical animation phase can advance without producing a new RGBA appearance. Repeated PNGs alone cannot prove a complete cycle or its timing. The 24 accepted captures remain a verified **window**, not a validated walking loop.

## 6. Effective collision tiles can diverge from stored and displayed tiles

PRG000 PSwitch_SubstTileAndAttr provides gameplay-time substitutions when the switch timer is active: coins can behave as bricks and bricks as coins (with other special tile variants). This is separate from persistent logical-map updates via Level_ChangeTile_ByTempVars and pending visual tile updates.

For reconstruction, distinguish:
1. **Raw ROM construction record**;
2. **Decoded/current logical tile-memory state**;
3. **Effective gameplay/collision tile** at the sampling point;
4. **Rendered PPU pixels**, which can be affected by update timing and graphics mapping.

This distinction matters to both level verification and sprite physics.

## 7. Highest-value next native experiment (pending)

Use MesenCE 2.2.1 with the already accepted, immutable save-state and input sequence. Do **not** run PR #20’s untested observer directly until its launcher, bounded callbacks, mock tests and baseline-neutrality checks pass. Sample both frame boundaries and, where practical, relevant execution boundaries.

| CPU address | Source symbol | Value sought |
| --- | --- | --- |
| 0xD8 | Player_InAir | grounded → airborne transition |
| 0xCF | Player_YVel | signed 4.4 falling velocity |
| 0x075F | Player_YVelFrac | fractional accumulator |
| 0xA2 / 0x87 | Player_Y / Player_YHi | world vertical position |
| 0x90 / 0x75 | Player_X / Player_XHi | world horizontal position |
| 0xB4 / 0xAB | Player_SpriteY / Player_SpriteX | display-space coordinates |
| 0xEE | Player_Frame | actual selected recipe |
| 0xEC | Player_WalkFrame | logical walk phase |
| 0x0603–0x0604 | Level_Tile_GndL/R | foot-probe tile identities |
| 0x0608–0x060B | Level_Tile_Quad | relevant tile ID groups |
| 0x7E94–0x7E9B | Tile_AttrTable | active collision thresholds |
| 0x12 / 0xFC | Horz_Scroll_Hi / Horz_Scroll | camera scroll state |

**Required evidence:** frame-indexed reads at 448396–448408, observed writes to grounded/velocity/frame variables with exact physical PRG mapping, controller inputs, corresponding OAM/PPU state, and independent comparison with the uninstrumented 24-frame replay. Preserve source hashes and input/capture provenance. Do not infer live memory from this table alone.

The game RAM addresses above are **Southbird source-symbol candidates**, not live-confirmed observations in the accepted frame window. Some symbol aliases are context-dependent; capture must occur in actual gameplay.

## Result and remaining gates

**Established:** source recipe definitions, ROM-backed recipe/OAM correspondence (PR #20), collision lookup mechanism, fixed-point motion algorithm, and exact fit of one gravity model to nine observed screen positions.

**Not established:** actual frame-state RAM, exact walk-off terrain column, world X/Y and scroll relationship, executed CPU PCs, instruction timing, complete visual animation cycle, or verified end-to-end world-geometry-to-OAM causality.

Keep the original private A/B/A evidence and historical JSON unchanged. This note is an addition to the research record, not a new acceptance gate.
