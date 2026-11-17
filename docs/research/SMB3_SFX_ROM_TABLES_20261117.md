# SMB3 PRG1 — Sound-effect bytecode, table boundaries and reuse

Research date: 2026-11-17  
Scope: **Super Mario Bros. 3 (USA), PRG1 / Revision A**.  
Status: **original private ROM verified read-only; static 6502 control-flow interpretation; emulator runtime pending**.

Companion documents: [SFX handlers and channel conflicts](SMB3_SFX_RUNTIME_SPELUNKING_20261117.md), [audio structures](SMB3_AUDIO_ROM_SPELUNKING_20261116.md), [APU hardware verification](SMB3_APU_EMULATOR_CROSSCHECK_20261116.md).

This report records derived facts, source offsets, hashes and explicit limitations. It **does not publish** the ROM, music note streams, full SFX data tables, samples, sprites or save states. Source bytecode is read from the original user's immutable private ROM in memory; no file modifications or MesenCE playback took place.

## Evidence baseline

Private ZIP member `Super Mario Bros. 3.nes` was opened in memory; ZIP extraction to disk was unnecessary. Original 393,232-byte ROM SHA-256 matched:

`4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`.

Standard iNES header offset `0x10`; PRG bank 28 of 32 8-KiB banks maps its data at CPU `$A000–$BFFF` when selected. CPU-to-file translation for these records:

`file_offset = 0x10 + (28 * 0x2000) + (cpu_address - 0xA000)`.

Static control-flow interpretation follows Southbird's pinned disassembly commit `09b1bd81a788de8ceec664a34094e84ddb463117`:
- [PRG028: world map and SFX handlers/data](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg028.asm)
- [PRG031: frequency and note-on routines](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm)
- [Source constants and RAM state](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm)
- Hardware semantics corroborated by [NESdev APU pulse](https://www.nesdev.org/wiki/APU_Pulse) and [APU Noise](https://www.nesdev.org/wiki/APU_Noise), as implemented in pinned MesenCE 2.2.1.

**Distinct evidence classes:**
- **ROM checked:** exact source byte positions, table pointers, neighboring bytes, block lengths/hashes, source-driven counts in a bounded static interpreter.
- **Source-derived:** event scheduling and index math based on assembled 6502 routines.
- **Not established:** dynamically executed instruction PCs, effects actually triggered in World 1-1, observed channel output, true wall-clock length, waveform/rate fidelity or audio completeness.

## 1. World-map sound bytecode and two-channel envelope

The map-SFX ROM has one 8-entry selection table (offsets to 2-byte source-track headers), followed by **seven 2-byte header pairs** and 74 contiguous bytes of track-program data. The eight selectors point to six playable program identities and two selections of one zero-byte program.

For the **primary Pulse 1** map-SFX stream:
- `0x00` ends the entire map effect;
- bytes `0x01–0x7F` write the *low period timer byte* at `$4002` and preserve the current event duration;
- bytes `0x80–0xFF` set a hold of `byte & 0x7F`, then consume the next timer byte in the *same sound-engine update*.
- The next event is processed after the hold expires. This is not a 1:1 note-byte-to-frame mapping.

Original-ROM lookup headers at CPU `$A1AF` have two separate entries that both point to `SndMap_Data_Unused`, an `0x00` byte immediately following the preceding program. They correspond to source-map request IDs `0x20` and `0x40`. Selecting either yields **zero pitched events**, but still visits the `MapSound_Stop` code, which writes `$4015=0x08` then `$4015=0x0F`. Thus "empty" does **not necessarily mean no APU side effects**; no runtime use of either unused request is established.

| Map SFX request | Interpreted name | Primary pitch events | Programmed ticks before primary 0x00 |
| --- | --- | ---: | ---: |
| 0x01 | World entrance | 15 | 45 |
| 0x02 | Move along path | 2 | 15 |
| 0x04 | Enter level | 12 | 54 |
| 0x08 | Inventory flip | 3 | 17 |
| 0x10 | Bonus appears | 5 | 30 |
| 0x20, 0x40 | Empty/unused alias | 0 | 0 |
| 0x80 | Denied action | 3 | 26 |

These are *program-level* durations assuming one processed Sound_Engine call per update with no pause or replacement—not measured audio length. This program also writes pulse control/sweep/high-timer registers to change sound on note events.

### Enter-level second track (Pulse 2)

The `0x04` header references a second stream; all other map headers use second-track offset zero. The second stream begins with a **2-tick no-new-frequency/silent-control event**, then schedules 12 low-timer pitch writes (including a 10-tick final hold), giving **56 nominal ticks**.

**Boundary finding:** The primary track is terminated at tick 54, when `MapSound_Stop` returns before dispatching the secondary track and reconfigures `$4015`. The second track's final 10-tick hold began at tick 46 and is cut off by the primary stop with **2 nominal ticks remaining**. Its trailing zero byte is not reached in this normal path. This is a source-derived scheduling prediction; validate with APU writes before claiming observed audibility.

The level-entry program also explicitly clears `SndCur_Music2` (background music) when initially selected, differentiating a map sound from background music.

### Raw-block evidence without extracted data

| CPU source span | iNES file offset | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Map selection + seven headers, 0xA1AF | 0x381BF | 22 | `096e918b51d7eb565a4bd6d556c5f69a4fabd9e2113e6d1f6d55495380cfdb2a` |
| All map sound programs, 0xA1C5 | 0x381D5 | 74 | `6b228855bb4a5c914a7df626f45598e7d00bbf663b4f7561754d3e881dd13289` |

## 2. Level 1 — four additional scripted effects

The `SndLev1_SuitLost2` handler selects a source-relative start offset based on the high-bit request code, saves the byte index in `SFX_Counter2`, and **increments the index before fetching**. High-bit values within the stream change `SFX_Counter3`, which is then written to `$4004` as the pulse-control configuration. Such control changes are consumed in the *same* update as the following ordinary event.

Every ordinary event issues a note-on request through `Sound_Sq2_NoteOn_NoPAPURAMP` unless the event is `0x7E`. A `0x7E` event **suppresses a new frequency write**, but the handler has still written a control byte, so it is not universally an instantaneous silence. On a subsequent update, `0x00` terminates the script and runs the group's cleanup.

Four source program ranges were scanned from the verified ROM through their zero terminators:

| Program label | CPU start | Bytes incl. terminator | High-bit control commands | Pitch events | 0x7E no-new-pitch events | Event-bearing updates |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Unknown / lost | 0xA55B | 31 | 6 | 24 | 0 | 24 |
| Lost-suit poof | 0xA57A | 56 | 11 | 40 | 4 | 44 |
| Lost shoe | 0xA5B2 | 21 | 4 | 12 | 4 | 16 |
| Tail wag | 0xA5C7 | 25 | 6 | 14 | 4 | 18 |

The **133-byte contiguous block** 0xA55B–0xA5DF (iNES file offset 0x3856B) has SHA-256 `4fbe07a4d1d366d3eb9d5cc7b49d73c2fc8dd24d3a499b4c306bc8ae65e2af9c`.

These are **script event counts**, not independent sound samples. The event-bearing updates exclude the subsequent terminator/cleanup call and any preemption by other Level 1 effects. The actual effect identity named "unknown" remains unverified.

## 3. Level 1 — a 1-Up and two kinds of rising effect

The standalone `SndLev1_1upData` source table has **six frequency bytes**; handler `SndLev1_1upCont` initializes `SFX_Counter2=0x30`, and only updates its low timer/shape when the three lowest counter bits are all zero. Since the table address is `SndLev1_1upData-1,Y` with `Y=counter>>3`, it uses table indices **5,4,3,2,1,0** at counter values 48,40,32,24,16,8. The source counter terminates after 48 updates. Do not mistake the byte order in ROM for order of playback.

The ordinary power-up initializes `SFX_Counter2=0x36` and selects source pitch data at `SndLev1_PUpData-1,(counter>>1)` when the counter is even. It therefore requests **27 notes in 54 updates**, using table indices **26 down to 0**. The named source table itself contains 31 bytes; four entries are not used by this ordinary power-up count path. Other routines may still read adjacent bytes; don't label them dead data.

The rise/vine handler is different. It initializes `SFX_Counter3=0`, then increments it on each update and calculates `Y=SFX_Counter3>>1`; it stops as soon as Y reaches 16 for a rising power-up or 32 for a vine. Therefore:
- Power-up rising: **31 event-bearing updates** (counter 1–31), then stop on counter 32.
- Vine rising: **63 event-bearing updates** (counter 1–63), then stop on counter 64.
- The first event computes `Y=0`, then reads `SndLev1_PUpRiseData-1,0`: the byte immediately **before** the named table, equal to **0x30** in the verified ROM. The table's previous neighbor is the 31-byte ordinary power-up data block.

The contiguous three-table block, CPU 0xA385–0xA3C8 (68 bytes, iNES file offset 0x38395), has SHA-256 `395f53665d50884c49376f87395adf3a7851c237f5a9340c586e407a371bc2c0`. It contains 1-Up (6), normal power-up (31) and rise/vine source data (31) in that order.

**Caveat:** "table[-1]" is an actual CPU address calculation, not inherently memory corruption or a proven bug. Preserve the neighboring physical source byte and label its provenance precisely.

## 4. Level 2 — further index-overrun and waveform interactions

The Level 2 Noise/triangle source handlers use counter-driven reads that can cross the labels assigned in the disassembly:

| Effect | Initial counter and computed lookup | Source read beyond named table |
| --- | --- | --- |
| March | `SFX_Counter4=14`, reads `SndLev2_MarchData[14]` | Named table has 14 bytes, so initial byte is **next Boomerang table's first byte** (0x11). |
| Boomerang | `SFX_Counter4=12`, reads `SndLev2_BoomerangData[12]` | Named table has 12 bytes, so initial byte is **next noise-frequency table's first byte** (0x01). |
| Crumble | counter initialized 32, initial even update skipped; at 31 reads `SndLev2_SkidNFreq[15]` | Named frequency table has 15 bytes, so first active lookup reads **following triangle-frequency table's first byte** (0x0C). |
| Flame | counter initialized 64, reads curve at `PRG028_A709-1 + (counter>>1)` | Final counter=1 gives Y=0 and reads **0xEC** immediately before 32-byte flame table, a ROM code byte. That update immediately executes SFX stop/cleanup, writing another Noise-control value (0xF0), so audible influence is **unproven**. |

The first three are source-code calculations verified against adjacent original ROM bytes. No evidence establishes that these are original developer errors; some may be deliberate zero-/one-based lookup conventions or shared implicit leading entries.

**Packed nibble format:** March and Boomerang source bytes contribute two independent Noise-register settings: `$400C=0x10 | (byte>>4)` (constant-volume nibble) and `$400E=0x10 | (byte & 0x0F)` (noise period nibble). The engine processes this on its countdown schedule, with a different source byte per invocation. Source table indexing can select a neighbor's first byte before reaching its own named data.

**Duplicated bytes vs shared address:** The 16-byte `SndLev2_SkidNCtl` table at CPU **0xA729** is **byte-for-byte equal to the first 16 bytes** of the separate 32-byte flame curve at **0xA709**. These are two distinct ROM locations with identical content. Their hashes must not cause SpriteMine to erase distinct source offsets/identities in its provenance catalog.

Checked private ROM data:

| CPU source | iNES file offset | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| First Level 2 source tables at 0xA5E0 | 0x385F0 | 48 | `89e47de15e33b2a89615e543ed3f07013a675af2c2052284b955b3c3c3fe88e8` |
| Flame curve at 0xA709 | 0x38719 | 32 | `b27b272a8999427b563d06792827544cbb6d1bd0fd429960fab864ca25124cea` |
| Crumble Noise control at 0xA729 | 0x38739 | 16 | `cd873b4e270a3b5a9c46db8c7358f84ee5e84e575039725dcde8e52eb59ce139` |

NESdev [APU Noise](https://www.nesdev.org/wiki/APU_Noise) confirms `$400C` contains envelope/volume parameters, `$400E` the mode and period, and `$400F` triggers a length-counter reload and envelope restart. MesenCE implements the same hardware. Raw writes are **not** equivalent to full audible-waveform evidence.

## 5. Decoder requirements and falsifiable experiments

**Smallest useful implementable feature:** an SMB3-only, bounded, read-only original-ROM **SFX instruction inspector**, not an audio exporter. Include:
- A mapping from source request value to group, handler, track or data location, physical PRG bank, selected source bytes and original-ROM fingerprint.
- Per-effect interpreters, **not** one shared grammar: map length/pitch; Level 1 counter-indexed notes; Level 1 control+note+0x7E scripts; Level 2 packed nibble and indexed curves; hardware register side effects.
- Explicit source-access records for each read, including **cross-label reads**, rather than forcing a virtual `table[0:n]` boundary that changes the game's behavior.
- Logical SFX updates and predicted ordered APU register writes separately from observed MesenCE register writes.
- Shared bytes at distinct ROM addresses retained as distinct provenance entries; deduplication of content must not collapse source identities.
- Explicit `0x00` terminators and counter stop events; fail on unbounded streams, invalid pointer mapping or unsupported paths.

### Suggested native acceptance vectors

1. Normal Map `0x04` (enter-level): verify that Pulse 1 schedules 12 pitch updates over 54 engine updates, Pulse 2 has an initial two-update silent event, and the secondary track's final scheduled 10-update hold is truncated after eight. Trace `$4000–$4007`, `$4015`, queue and active state.
2. Six-note 1-Up: verify six source-index reversals and eight-update spacing, plus its special Level 1 priority protection.
3. Rising item/vine: record the **first data read** from the predecessor table and validate 31/63 event-bearing updates.
4. Level 2: log the initial physical ROM source read for March, Boomerang and Crumble and the final Flame read; do not claim register-level or audible playback until confirmed.
5. Mixed effect/music replay: prove whether Level 2 Noise writes are overwritten by same-update music events, or whether any `$4015` cleanup affects DMC sampling.
6. Run A/B/A with immutable save state, known inputs and preserved CPU-cycle/mapper provenance. Use MesenCE 2.2.1 passive callbacks returning nothing, and debug memory reads only; verify no instrumentation changes gameplay.

**No new tests, emulator run or audio output were produced for this documentation increment.** The only direct verification performed here is the read-only fixture hash, ROM pointer/payload matching and deterministic static interpretation of the pinned engine code. Keep hypotheses explicitly distinct from native observations.

## License and distribution

Source disassembly and emulator implementations are linked for research, not copied into SpriteMine. Do not include third-party assembly, private ROM bytes, copyrighted audio samples, extracted graphics or save states in the public repository. Audit licenses before porting code.


## 6. Source event producers and apparent loops (supplementary PRG investigation)

Looking at **gameplay callers**, rather than only the PRG28 audio-engine interpreter, provides additional source-derived provenance:

- In [PRG011's airship world-map movement routine](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg011.asm), the game tests `SndCur_Level2 & 0x08`. If not already active, it ORs `SND_LEVELAIRSHIP` into `Sound_QLevel2` again. The Level 2 airship SFX sets `SFX_Counter4=0x40` on entry. Thus the airship's seemingly continuous noise can be **a series of repeatedly requested, finite effects**, not an internally looping ROM sample or music segment. The caller's updates are conditional on airship world-map movement state. No live loop boundary has been observed.
- In [PRG008 `Player_TailAttackAnim`](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm), a new tail attack queues `SND_LEVELTAILWAG`. The airborne-tail/flutter routine also queues it, but compares the Player sound queue to `SND_PLAYERJUMP` to avoid requesting a tail wag in a particular just-jumped state. This is **gameplay event arbitration before audio-engine arbitration**. The identical sound request can originate from two different animation/gameplay triggers.
- In [PRG000's suit/shoe damage code](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg000.asm), `SND_LEVELSHOE` is queued at a shoe-loss path. The disassembly also contains a Japanese-version suit-loss code path labelled by Southbird as dead in the US build; do not treat every symbol occurrence as a reachable US PRG1 event without execution evidence.
- A repository search for the symbol `SND_LEVELUNK` returned declarations and the audio handler in `smb3.asm` and `PRG/prg028.asm`, but **no additional symbol-named gameplay caller**. This is *not* proof the effect is unreachable: literal numeric requests and disassembly omissions remain possible. Its gameplay identity remains unresolved.

This adds a fifth catalog concept to the prior SFX layers: **producer context** (the gameplay routine and condition that queues an event). Two identical request bytes can have distinct triggering contexts; a long audible background SFX can arise from repeated short requests; and symbolic names alone do not establish that a branch is exercised in the verified US PRG1 ROM.

Suggested native evidence for producer attribution: read-only, physically bank-mapped CPU execution probes at just the known producer PCs plus `$04F1–$04F3` queue write callbacks, with frame and cycle numbers. Avoid broad CPU exec tracing. For the airship experiment, separately log `SndCur_Level2` transitions and `SFX_Counter4` resets to detect actual repetition.
