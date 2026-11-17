# SMB3 PRG1 — Gameplay-to-sound event provenance and level persistence

**Expedition 10 — 2026-11-17**  
Scope: **Super Mario Bros. 3 (USA), PRG1 / Revision A**  
Evidence class: **pinned third-party disassembly and emulator-documentation inspection only**. No new private-ROM hash check, native MesenCE execution, APU capture, synthetic tests or Windows-local writes in this expedition. Do **not** promote these predictions to observed PRG1 behavior without a native trace.

Follows [SFX ROM tables](SMB3_SFX_ROM_TABLES_20261117.md), [SFX runtime and arbitration](SMB3_SFX_RUNTIME_SPELUNKING_20261117.md), and [World 1-1 reconstruction](SMB3_WORLD1_1_RECONSTRUCTION.md). The earlier Expedition 9 report did independently verify selected original private PRG1 ROM bytes; this document does **not** independently reverify those bytes.

## Sources / exact revisions

Southbird SMB3 disassembly, commit `09b1bd81a788de8ceec664a34094e84ddb463117`:
- [PRG028 sound dispatch](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg028.asm#L89-L111), [Level 1 arbitration](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg028.asm#L725-L752), [special-value comparisons](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg028.asm#L865-L905)
- [PRG008 coin collection/block logic](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm#L4724-L4744), [bump-block logic](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm#L4935-L5050), [vine](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm#L5286-L5295)
- [PRG001 power-up sound/timer](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg001.asm#L1799-L1818)
- [PRG002 end-card reward gate](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg002.asm#L5837-L5855), [popped-out coin](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg002.asm#L6182-L6207)
- [PRG007 laser reuse](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg007.asm#L5530-L5545)
- [PRG026 100-coin award](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L2858-L2909), [junction toggle](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L1589-L1617)
- [PRG030 collected-block bitmap recorder](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L4641-L4722), [initial clear](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L1361-L1370)
- [PRG014 coin and block persistence consumers](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg014.asm#L1119-L1216), [bit lookup](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg014.asm#L4918-L4979)
- [PRG031 sound engine caller and MMC3 mapping](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm#L1617-L1632)
- [Sound constants/RAM allocation](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm#L1346-L1383)
- NESdev [APU frame counter](https://www.nesdev.org/wiki/APU_Frame_Counter). MesenCE 2.2.1 pinned [Lua documentation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json).

## Findings 67–76

**67. Queue lifetime / dispatch order — source-confirmed.** `Sound_Process` calls Level 2, Player, Level 1, Map, Music handlers in that order and then clears the sound request queues. The engine does not provide a general persistent FIFO. Some requests can be superseded or discarded within an engine invocation. Precise ordering relative to gameplay producer writes still needs frame/CPU tracing.

**68. Playing 1-Up blocks newer Level 1 requests — source-confirmed.** `Sound_PlayLevel1` first tests `SndCur_Level1 & $40` and continues the 1-Up handler without dispatching pending Level 1 requests. Combined with queue clearing, this can suppress other Level 1 sounds; this is a special active-state override, not just lowest-bit-wins selection.

**69. Producer-to-sound relationships are many-to-many — source-confirmed examples.** Level 1 coin `$01`: collect tile coin, emitted coin, card reward, title UI; Level 2 crumble `$01`: brick break, ice-block destruction, Dry Bones; Player bump `$02`: bump/impact and rapid laser effect; Level 1 1-Up `$40`: score, card, 100-coin and end-level rewards; Level 1 vine `$04`: vine and coin-heaven-related bounce. The popped-out coin producer queues the coin effect while converting an on-screen object, not necessarily when a player takes the coin. The laser path reuses bump requests subject to a pipe/shrink guard. Sound ID alone cannot prove event identity.

**70. Composite request aliases — hypothesis grounded in bit values and special dispatch.** OR-ing Level 1 Poof `$80` and Blip `$10` forms `$90`, which is exactly the `SND_LEVELUNK` special value. Poof `$80` plus Power `$20` forms `$A0`, and all three form `$B0`. The high-bit path compares full values to the special identifiers. The source demonstrates the potential for an alias if producers OR these bits during a single pending interval. **It does not prove any such combination actually occurs or executes a particular sound program**; direct `STA` writes and path constraints may prevent it. Test queue writes with producer PCs.

**71. 100-coin 1-Up overwrites queue — source-confirmed operation, unobserved collision.** `StatusBar_Fill_Coins` increments lives and stores `SND_LEVEL1UP` directly to `Sound_QLevel1` when 100 coins is reached, unlike the many producer paths using OR. This can replace prior pending Level 1 bits; a frame-specific overwrite must be demonstrated rather than presumed.

**72. End-level card award is gated by active 1-Up SFX — source-confirmed.** `EndLevelCard_Give1UpsAndCycle` returns early when `SndCur_Level1 & $40`; otherwise it queues 1-Up, awards one life, and decrements its remaining award count. This is a gameplay-sound synchronization dependency. The exact pacing is not a measured runtime frame count.

**73. 128-byte collected-block memory — source-confirmed.** `Level_BlockGrabHitMem` is RAM `$7E02–$7E81`, organized in two `$40`-byte halves selected by `Level_JctFlag`. `Level_RecordBlockHit` derives byte index/bit from tile coordinates and sets an MSB-first flag. `PRG014` checks flags while regenerating coin runs and selected 1-Up-bearing blocks, and `PRG026` toggles the junction flag. The bitmap is cleared during initial level setup; it is **not** a persistent save game, nor does it represent all tile mutations. Do not infer the 1-Up/coin layout without rechecking individual source generators and the target level.

**74. Emergence vs collection are different sound producers — source-confirmed.** `PowerUp_DoRaise` queues rising effect `$02` when the object timer equals `$2D` (45); `PowerUp_PlaySound` queues regular power-up `$20` during collection; other suit/transform paths can choose Poof `$80`. A visible object appearing is not sufficient proof of a collection event. Native trace must check timer/animation/queue relative ordering.

**75. $4017 and MMC3 context are material to audio provenance — source-confirmed / hardware-supported.** `Sound_Engine_Begin` writes `$FF` to `$4017`, and the caller maps bank 28 at `$A000` before invocation. APU register trace limited to `$4000–$400F` is incomplete; capture `$4015` and `$4017`, and physical PRG bank mapping at producer PCs. NESdev documents frame-counter behavior. Do not mistake a $4017 write for an observed waveform result.

**76. Lua instrumentation must be strictly passive — MesenCE 2.2.1 API-documented.** `emu.addMemoryCallback` write callbacks execute before writes and may mutate values if returning an integer; callback bodies must not return replacement integers. Ordinary CPU-memory Lua reads may have side effects; use debug memory types. Passive callbacks alone do not prove nonintrusive timing; A/B/A baseline neutrality still needs native validation.

## Acceptance experiments (source-derived expectations, NOT executed)

1. Record `Sound_QLevel1` writer PC, old/new queue values, SndCur Level 1 and engine entry/exit on a known PRG1 save-state/input replay. Specifically seek `$80 | $10 = $90` and verify the producer pair before accepting the unidentified effect hypothesis.
2. Collect a coin while a 1-Up is active; distinguish queued, accepted, suppressed, active and audible events; observe APU writes.
3. Track end-card consecutive rewards and the `SndCur_Level1 & $40` gate. Do not assume an exact 48-frame cadence from the nominal 48 engine-update counter.
4. At a level junction: trace `Level_BlockGrabHitMem`, `Level_JctFlag`, initial bitmap clear, a collected coin and a hidden 1-Up, and compare regenerated tile memory. Include negative controls for unrelated tile changes.
5. Instrument rising power-up timer `$2D`, on-screen object position, queue `$02`, later pickup and queue `$20`; preserve frame, CPU-cycle and physical PRG mapping.
6. Trace `$4000–$4017` relevant writes and queue/active variables while controlling music and SFX. Never classify an effect as audible using RAM queue evidence alone.

Use immutable original ROM and reproducible MesenCE save state/input fixture; preserve hashes, emulator build, frame IDs, CPU address + mapped PRG address, and exact event sequence. No private copyrighted assets in GitHub.

## Catalog model implication

Separate entities for gameplay **producer** (bank/PC and precondition), **request** (queue/register/value and writer), **engine decision** (accept/continue/drop/preempt), **source program** (raw/counter/script and physically mapped byte reads), **APU write**, **observed sound**, **level mutation** (tile/object/bitmap state) and **capture provenance**. Record hypotheses separately from observations; do not collapse multiple producer identities onto a single SFX byte or duplicate sound bytes onto one source location.
