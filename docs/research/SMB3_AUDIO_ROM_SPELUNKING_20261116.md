# SMB3 PRG1 — Native sound/music ROM research (2026-11-16)

Status: **read-only ROM fingerprint and small static event decode; no native APU capture or completed soundtrack decoder**  
Scope: Super Mario Bros. 3 USA PRG1 / Revision A only.

This note continues [the SpriteMine research ledger](SMB3_ROM_SPELUNKING_20261116.md) with audio observations. The original ROM and any extracted sequence, sound, DPCM and save-state data remain private. This document contains small derived facts and *does not* distribute music streams, copyrighted samples or code from another project.

## Sources and exact fixture

- Private original ZIP member `Super Mario Bros. 3.nes` (393,232 bytes), SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`, read-only.
- Header: standard iNES, mapper 4 (MMC3), PRG 256 KiB, CHR 128 KiB. The PRG begins at file offset 0x10.
- Source reference: Southbird SMB3 disassembly [PRG028](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg028.asm), [PRG031](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm), [PRG022](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg022.asm), [PRG008](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm), [RAM and hardware symbols](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm) at commit 09b1bd81.
- Hardware reference: [NESdev APU pulse](https://www.nesdev.org/wiki/APU_Pulse), [APU frame counter/length registers](https://www.nesdev.org/wiki/APU_registers), [APU length counter](https://www.nesdev.org/wiki/APU_Length_Counter).

All CPU addresses below refer to the relevant MMC3 bank mappings documented by the disassembly. Physical offsets assume this verified original iNES PRG layout. No runtime memory maps were captured in this session.

## 1. ROM-matched music tables

A read-only search of the PRG bytes found these exact tables. Both the physical bank and byte sequences agreed with the disassembly:

| Source structure | 8-KiB PRG bank | Offset in PRG | iNES file offset | CPU address |
| --- | ---: | --- | --- | --- |
| 12-note pulse-period table (`Square1_Table_Notes`) | 31 | 0x3E839 | 0x3E849 | 0xE839 |
| `Music_RestH_LUT` | 31 | 0x3E874 | 0x3E884 | 0xE874 |
| `Music_Set2B_IndexOffs` | 28 | 0x39400 | 0x39410 | 0xB400 |
| `Music_Set2B_Headers` | 28 | 0x3942D | 0x3943D | 0xB42D |
| `Music_Set2B_Starts` | 28 | 0x39530 | 0x39540 | 0xB530 |
| `Music_Set2B_Ends` | 28 | 0x3953C | 0x3954C | 0xB53C |
| `Music_Set2B_Loops` | 28 | 0x39548 | 0x39558 | 0xB548 |

Evidence classification: **direct original-ROM byte-match**, independently of the source's symbolic labels. Pointer structures were resolved within the proper bank. This is *not* a live trace proving selection of a particular song during gameplay.

## 2. Song selection and reusable segments

`MUS2B_OVERWORLD = 0x10` is Set 2B selection index 0. Its ROM-backed Start/End/Loop indices are 0/6/1. Looking up its index-offset table and seven-byte segment headers yields this initial segment order:

| Sequence index | Header | Data base (mapped CPU) |
| ---: | --- | --- |
| 0 | M2BSegHedr0F | 0xB554 |
| 1 | M2BSegHedr10 | 0xB5A9 |
| 2 | M2BSegHedr11 | 0xB5C3 |
| 3 | M2BSegHedr10 | 0xB5A9 |
| 4 | M2BSegHedr12 | 0xB629 |
| 5 | M2BSegHedr13 | 0xB68A |
| 6 | M2BSegHedr14 | 0xB71D |

Index 0 is introductory; indices 1–6 recur under the documented loop logic. Index 1 and 3 share identical source segment data. Source-derived topology and pointers are now independently checked against the ROM. Segment timing and all individual channel events have *not* been fully decoded or APU-validated.

The selection rows for `MUS2B_TOADHOUSE = 0x80` and `MUS2B_PSWITCH = 0xA0` both contain Start/End/Loop indices 0x1B/0x1D/0x1B. They are distinct gameplay requests with a common source arrangement. Actual in-game audible equality requires state-sensitive verification.

## 3. Introductory segment channel locations

ROM header M2BSegHedr0F at mapped CPU 0xB496 has base 0xB554 and timing row 0x30. Its per-track absolute start addresses are:

| Channel | CPU start address |
| --- | --- |
| Pulse 2 | 0xB554 |
| Pulse 1 | 0xB56C |
| Triangle | 0xB57D |
| Noise | 0xB595 |
| DMC track | 0xB599 |

The Pulse 2 stream occupies **24 bytes**, ending at 0xB56B, immediately before the Pulse 1 offset. A bounded static interpreter of this one Pulse 2 stream identified **16 ordinary events**: nine note events and seven rests, occupying **192 sequencer-update ticks** under the normal row-0x30 duration lookups. This was a small read-only analysis, not a full decoder or playback proof. The note positions and original stream bytes are not published.

## 4. Pulse pitch byte to APU timer

The engine uses a 12-word base-period table and octave shifts; the note codes are in doubled semitone units. For the ordinary pulse-note path, note byte 0x30 resolves to timer 0x01AB:

`1,789,773 / (16 * (0x01AB + 1)) = 261.36 Hz`, approximately C4.

A note byte of 0x26 resolves to timer 0x023A, about 195.90 Hz (approximately G3), and note byte 0x3E resolves to timer 0x011C, about 392.49 Hz (G4).

These are direct ROM-table calculations, using an approximate NTSC CPU clock; they are not measured audio frequencies. The engine modifies the low timer byte for note codes >= decimal 56, and has channel-specific sweep and bend branches. The triangle also shares the pitch routine but has distinct output hardware.

**Important hardware correction:** PRG031 ORs the high timer byte with 0x08 before writing 0x4003/0x4007. Bit 3 is *not* a frequency bit. The pulse timer uses bits 0–2; bit 3 contributes to the length-counter index, producing index 1 (254 length-counter clocks) with the ordinary 0x08 high-byte setting. This corrects a misleading casual comment in the disassembly.

The code treats note byte 0x7E as a rest that returns without a new note-frequency write. That does not, by itself, guarantee instant silence of a previously sounding pulse; length, envelope and channel state can persist.

## 5. Patches, timing and sound effect arbitration

PRG031 `Music_PatchGetCTL` uses the event command's patch bits to select one of eight short or long pulse-control data tables from PRG028. The current note-length countdown indexes this table and writes the control byte to 0x4000 or 0x4004. Thus the timbre can change during a held note, even without a new pitch event. The patch table is *not a PCM sample*.

Example timing from `Music_RestH_LUT`: timing row 0x30 with low-nibble index 2 returns eight update ticks; index 8 returns 24 ticks. A time-warning offset of 0x10 selects another timing row. The same song events can therefore be performed at modified pace.

`Sound_Process` handles Level 2 effects, Player effects, Level 1 effects, Map effects and Music in that order, then clears the request queues. Pulse 1 music can be interrupted by player/map effects; Pulse 2 by Level 1 effects. A gameplay capture mixes these sources and cannot automatically be presented as a clean original music sequence.

`Sound_Engine_Begin` writes 0xFF to APU frame counter 0x4017 when called, selecting 5-step frame-sequencer mode with IRQ inhibit. PRG022 calls the sound engine in its per-frame path after mapping PRG28 into the 0xA000 window. The full APU waveform depends on the frame-counter clocking, register-write timing, envelope, sweep, nonlinear mixing and DMC behavior, not just note names.

## 6. DMC and other boundaries

PRG031 defines **16 DMC playback selections** mapped to nine named DMC sample identities, with shared samples at multiple playback rates or lengths. Some named sample data appears in PRG010, other sample definitions in PRG031. A source comment flags an abnormal sample-3 length referencing DMC02: preserve it as an **unconfirmed anomaly**, not a proven secret sound.

NES DMC sample address and length formulas are 0xC000 + 64*A and 16*L + 1 for APU register values A (0x4012) and L (0x4013). Correct source provenance requires physical PRG bank mapping when the DMC hardware reads those bytes.

## 7. Implementation recommendation and validation gates

Next useful SMB3-only feature: a **read-only music-structure inspector** exposing verified song ID, segment indices, loop markers, bank/physical offsets, channel track pointers, and a limited interpreted event stream. Every event must remain linked to exact ROM offsets and decoder version.

Implement in stages:
1. Parse and verify exact Set 2B tables and seven-byte headers against private fixture, with synthetic malformed/bounds test cases.
2. Decode the introduction's Pulse 2 stream and verify all source bytes consumed and correct event/timing counts.
3. Decode other channel grammars separately, including patch selection, note lengths, noise and DMC triggering; recognize 0x00/0x7E/0xFF according to track context.
4. Capture real MesenCE 2.2.1 APU register writes at exact CPU-cycle positions in a reproducible, bounded run; compare against decoder predictions, with a controlled SFX-free playback window.
5. Only after independent native validation, consider original-sequence export or more advanced audio representations.

**Verification status:** original ROM hash and byte location matches confirmed; introductory segment pointer resolution and basic Pulse 2 event counts checked in memory; no emulator launched; no new audio or copyrighted assets exported; no new tests committed.

This is research evidence, not a claim of exhaustive music decoding or complete audio export.


## 8. Full intro channel-boundary audit (subsequent read-only confirmation)

The same verified private ROM ZIP was independently opened read-only again; ZIP CRC passed and ROM SHA-256 was rechecked. This analysis evaluated **all five** channels in the first Set 2B Overworld 1 segment. It follows PRG031's channel-specific command treatment, does not emit copyrighted note streams or sample bytes, and was not compared against actual APU playback.

| Channel | CPU start–last source byte (PRG28) | Bytes | Static result within 192 ticks |
| --- | --- | ---: | --- |
| Pulse 2 | 0xB554–0xB56B | 24 | 9 notes, 7 rests; segment-end 0x00 at last byte |
| Pulse 1 | 0xB56C–0xB57C | 17 | 7 notes, 4 rests; last rest extends beyond segment boundary |
| Triangle | 0xB57D–0xB594 | 24 | 8 notes, 8 rests over 192 ticks; final byte 0x00 not consumed by bounded analysis |
| Noise | 0xB595–0xB598 | 4 | Two-event 48-tick pattern repeated four times; 0x00 resets its own track pointer |
| DMC | 0xB599–0xB5A8 | 16 | 8 DMC trigger requests, one 0x7E stop |

The 85-byte contiguous span 0xB554–0xB5A8 ends immediately before the next segment base 0xB5A9. Read-only SHA-256 of the **source spans** (hashes only, bytes not published):

| Span | SHA-256 |
| --- | --- |
| All 85 bytes | `3014179af03a6886d82ec03ca7e17472d9cb00caf6255f6405e311ca4540e5af` |
| Pulse 2 | `3613af1720d630a0382be5b46010f0975cd787356457fd970bf720890c033fde` |
| Pulse 1 | `d5e22a2486252b615b32597f900286ccd42c3afc37e8288263c502ab1f463bee` |
| Triangle | `4572f3067c38adc994c3354cf0d6f742d8d74cc6273e0668530ee274883e8ef8` |
| Noise | `c109fdcd3a4aab92d573609bbe22b64ab09b338b28d5fe941c247517e806a381` |
| DMC track | `4b054b8c3bd0d6ac51d516810cc0ede36e82f1d2784c94185d70e4fd38406b11` |

**Important boundary behavior:** Pulse 1's final rest begins at tick 112, and its programmed duration is 96 ticks (nominal endpoint tick 208). The leading Pulse 2 channel reaches the segment terminator at tick 192; `PRG031_E48C` initializes the next segment's counters and track pointers, so that Pulse 1 rest is *not* left to finish naturally. Similarly, the Noise channel repeats its own short pattern without waiting for a segment loop. A byte-slice-based decoder without a shared sequencer clock would get this wrong.

Channel-specific rest semantics also matter: 0x7E on a pulse channel skips a new pitch update (not necessarily immediate silence); on Triangle it changes the linear-control state; on DMC it requests a stop through the DMC handler; the Noise track uses source note 0x01 for its silent event. These are not interchangeable "rest = zero audio now" operations.

## 9. Overworld 1's original Pulse 2 section lengths

Following the main Pulse 2 segment-end byte and PRG031's Set 2B header/index tables, each of the seven initial segment references was decoded independently through its first 0x00 terminator. The initial order and bounded durations are:

| Index | Header identity | Pulse 2 source span (incl. terminator) | Note events | Rest events | Music update ticks |
| ---: | --- | --- | ---: | ---: | ---: |
| 0 | 0x0F | 0xB554–0xB56B | 9 | 7 | 192 |
| 1 | 0x10 | 0xB5A9–0xB5C2 | 7 | 9 | 192 |
| 2 | 0x11 | 0xB5C3–0xB5D4 | 6 | 5 | 192 |
| 3 | 0x10 (reused) | 0xB5A9–0xB5C2 | 7 | 9 | 192 |
| 4 | 0x12 | 0xB629–0xB63A | 6 | 5 | 192 |
| 5 | 0x13 | 0xB68A–0xB6BE | 24 | 16 | 384 |
| 6 | 0x14 | 0xB71D–0xB74C | 22 | 15 | 384 |

The source-defined **initial pass totals 1,728 music-update ticks**; the repeating indices 1–6 total **1,536 ticks**. These are logical sequencer durations under the normal timing table, not independently timestamped emulator playback. Time-warning tempo substitution and game state can change wall-clock behavior.

The segment header data also shows **per-channel sharing**: headers 0x10, 0x11 and 0x12 all point their Noise track to 0xB658, while headers 0x10 and 0x11 both point their DMC track to 0xB667. Full-segment and individual-channel duplication must be treated separately in the asset catalog.

## 10. Specific DMC cues and sample-length anomaly

The intro's source DMC track requests cues 0x01, 0x05 and 0x08 (plus 0x7E stop), with repeated occurrences. The original ROM's DMC control/length/address tables are at fixed PRG31 CPU addresses **0xE32A**, **0xE31A** and **0xE30A** respectively. The relevant cue resolutions are:

| One-based cue | Sample label in disassembly | DMC CPU source address | Requested byte length | Rate register |
| --- | --- | --- | ---: | --- |
| 0x01 | DMC01 | 0xE000 | 129 | 0x0F |
| 0x05 | DMC04 | 0xE980 | 257 | 0x0F |
| 0x08 | DMC06 | 0xEA80 | 897 | 0x0F |

The MMC3 permanently maps its last 8-KiB PRG bank at 0xE000–0xFFFF, so **these three specifically used intro samples are bank-stable**. This is a useful reduction in complexity for first-frame audio validation; it does **not** apply to all SMB3 DMC cues, since some start at 0xC000–0xDFFF and depend on bank mapping.

A separate **unconfirmed suspicious cue** is 0x04: the ROM table selects the same DMC02 start address 0xE080 as cue 0x02 but with an encoded length of **1,025 bytes**, versus **449 bytes** for cue 0x02. That would request reads through 0xE480, 576 bytes farther than the shorter selection and into other bank31 contents. This is a real table-length difference, not evidence that the cue is used, audible, intentional or a "lost sample". The intro uses neither of these two cues.

Hardware DMC formulas: sample CPU start = 0xC000 + (64 × 0x4012), byte count = 16 × 0x4013 + 1, with CPU address to physical file mapping dependent on current MMC3 bank where applicable. See [NESdev DMC](https://www.nesdev.org/wiki/APU_DMC), [NESdev MMC3](https://www.nesdev.org/wiki/MMC3) and the pinned PRG031 ROM-source table.

## 11. Reproducibility / pending gates

This increment is a **private read-only analytical verification**, not a newly tested project implementation. It used the unchanged original ROM as the source, masked 8-KiB PRG offsets to translate CPU addresses, indexed the ROM-verified header and channel tables, and applied the source's rest/patch/track-end behaviors. No original note arrays, PCM sample data or copyrighted music output were exported.

Next engineering gates: implement a bounded deterministic, fixture-independent synthetic parser with explicit per-channel state and source offsets; validate its metadata counts against this ledger; confirm time/scheduling with live MesenCE 2.2.1 APU register traces before declaring note or audio export fidelity.


## 12. Quantified low-time warning tempo, checked against ROM

PRG031 `Music_GetRestTicks` computes timing lookup index `Music_RestH_Base + Music_RestH_Off + (command & 0x0F)`; the low-time-warning recovery path sets `Music_RestH_Off = 0x10` before requeuing the held Set 2B music. The original seven Overworld 1 Pulse 2 segments all use base 0x30, so normal timing reads row 0x30 and accelerated timing reads row 0x40.

Read-only redecoding of **every segment's original byte stream** under both modes gave:

| Initial sequence index | Normal timing ticks | Warning timing ticks |
| ---: | ---: | ---: |
| 0 | 192 | 160 |
| 1 | 192 | 160 |
| 2 | 192 | 160 |
| 3 | 192 | 160 |
| 4 | 192 | 160 |
| 5 | 384 | 320 |
| 6 | 384 | 320 |
| **Initial pass, indices 0–6** | **1,728** | **1,440** |
| **Repeating loop, indices 1–6** | **1,536** | **1,280** |

Each complete segment is exactly **5/6 of its original tick duration**; nominal event rate is **6/5 of normal (20% faster)**. This holds for segment aggregates, not necessarily for every individual note: the lookup entries are not all reduced at identical ratios. The note bytes, segment order and channel pointer identities are unchanged. This is a **ROM-backed sequencer-model prediction**, not a measured emulator playback or claim that the actual audio clock advances identically in all game states.

In PRG031, the time-warning Set 1 song's completion path calls the Set 2B queue logic for the held track after setting the +0x10 timing offset. Under that code path, the song's segment traversal is reinitialized at its beginning, rather than necessarily resuming a suspended note position. Test this in the native emulator before presenting it as an observed in-game transition.

This speed-multiplier finding is independently reproducible using only the verified PRG1 ROM's 0xE874 duration table, seven Set 2B headers, the Pulse 2 streams and the source-described lookup/queue semantics; no copyright-protected note data needs to be published.
