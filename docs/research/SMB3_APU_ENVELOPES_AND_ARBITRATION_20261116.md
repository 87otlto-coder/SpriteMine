# SMB3 PRG1 — APU patch envelopes and channel arbitration

Research date: 2026-11-16  
Status: **direct private ROM byte checks + static source interpretation; live APU trace pending**  
Scope: **Super Mario Bros. 3 USA PRG1 / Revision A only**.  
Companion: [SMB3 audio ROM research](SMB3_AUDIO_ROM_SPELUNKING_20261116.md), [research handoff](SMB3_ROM_SPELUNKING_20261116.md).

This report is a **read-only forensic research note**, not an audio exporter or a claim that MesenCE reproduced the predictions below. The original ROM, original note sequences, DPCM samples and generated game audio are **not included** in GitHub.

## Source and fixture

Original verified private ROM: `Super Mario Bros. 3.nes` (393,232 bytes), SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`. The ROM was opened read-only in the current environment.

Pinned disassembly (research reference only): Southbird [PRG028](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg028.asm) instrument patch tables and sound processing; [PRG031](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm) music notes/patches/track arbitration; [PRG022](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg022.asm) periodic sound-engine call; [smb3.asm](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm) hardware aliases.

Hardware: [NESdev APU Pulse](https://www.nesdev.org/wiki/APU_Pulse), [APU Envelope](https://www.nesdev.org/wiki/APU_Envelope), [APU Registers](https://www.nesdev.org/wiki/APU_registers), [APU Frame Counter](https://www.nesdev.org/wiki/APU_Frame_Counter).

All CPU and physical ROM addresses below have separately specified address spaces. The PRG28 audio patch source lives at CPU 0xA000–0xBFFF when MMC3 bank 28 is selected in that window. Native bank mapping still requires live confirmation at capture time.

## 1. The contiguous ROM patch block

In verified PRG1, the 14 named short/long instrument tables from PRG028 form one contiguous block:

- **Physical PRG offset** `0x39196–0x393F7` (inclusive).
- **iNES ROM file offset** `0x391A6–0x39407` (inclusive; 16-byte header).
- **CPU window when PRG28 is mapped** `0xB196–0xB3F7`.
- **Length**: **610 bytes**.
- **SHA-256 over exactly those 610 bytes**: `e9bb4a059a48ac060fac47a1a753290fff3d8d52055d9777b50baa8209dda358`.
- **All 610 values have bit 4 set**. The `constant volume` bit is set throughout this music patch block.
- Together the patch data uses all four pulse duty-cycle choices (12.5%, 25%, 50%, 75%).

This is an actual read-only original-ROM scan, **not merely source interpretation**. It is also a significant hardware distinction: in these tables, the game sets the APU pulse channel to **constant volume mode**, then writes changing volume values in software. The APU hardware's own automatic envelope-decay output is bypassed for these values, though hardware timing, length counters, duty and sweep still affect sound.

The disassembly's `Music_PatchTableShort` and `Music_PatchTableLong` provide eight selection slots, but slot 7 aliases patch family 2. There are **seven unique named source families** (1,2,3,4,5,6,8) with short/long variants, not eight independent patch-data families.

**Boundary warning**: the eight disassembly data bytes after the final `PatS8` table and before `Music_Set2B_IndexOffs` are *not included* in the 610-byte patch block. Their use is not established here; do not silently treat them as further envelope steps.

## 2. Short-note envelope pointers — direct ROM correlations

Selected source tables were matched to private original ROM bytes as unique contiguous sequences:

| Short patch | Physical PRG offset | CPU address in PRG28 mapping | Source bytes | SHA-256 |
| --- | --- | --- | ---: | --- |
| `PatS1` | 0x391D6 | 0xB1D6 | 23 | `b482a8f92991a6dc577134613a71d446dd625e7932443c289daeeeae4f9ad47b` |
| `PatS2` | 0x3922D | 0xB22D | 23 | `c2920a128d19b6e960bce931698c07f3e186965ed5da8c1b1a4f6cb9416571ce` |
| `PatS3` | 0x39284 | 0xB284 | 24 | `7670802df6c9b1190348296ce3ad6ae09ac04dceaedd953e3a03d079b1d8f5b4` |
| `PatS4` | 0x392DC | 0xB2DC | 23 | `0c78cbaa790d782f994019d4798d202c3dd0a2dc5db868e779e81d1def9562e4` |
| `PatS8` | 0x393E1 | 0xB3E1 | 23 | `ad83f8deab3d7dabdcbec729e7943f29917f52c1360460122dbf4825c1429191` |

The source's short-note path uses `Music_CalcNoteLen` to set length counter to `0x16` (22) for a note whose current event interval is below 19 ticks. `Music_Sq2Track` and `Music_Sq1Track` decrement that counter **before** indexing their patch table. Hence a newly started short note reads the indices **21, 20, 19, ...** over successive music-engine updates. Starting at patch index 0 would play an incorrect instrument curve.

For longer notes (interval >= 19 ticks), the source selects a long table and a starting note-length counter `0x3F` (63), reading indices 62, 61, ... after the decrement. The event interval and the note's envelope counter are **distinct timing concepts**; the next note may replace the current one before its programmed envelope reaches index zero.

## 3. Opening Overworld 1 Pulse 2 — bounded APU write test vector

PRG28's Overworld 1 introductory segment starts its Pulse 2 track at mapped CPU 0xB554. Its first instruction is a timing/patch selector `0xA2`, followed by source note byte `0x26`. These two bytes were checked in the private ROM; neither a full note stream nor copyrighted music audio is published.

- Timing row: 0x30 + low nibble 0x2 → Music_RestH_LUT[0x32] = **8 updates**.
- Patch selector: `(0xA0 & 0x70) >> 4 = 2` (zero-based), resolving to **PatS3**.
- Note byte 0x26 (decimal 38): the source's 12-period table and octave shifts produce pulse timer **0x023A**, approximately G3 at 195.9 Hz using an NTSC CPU clock.
- Expected Pulse 2 note-on timer writes, in source order, are **`$4006 = 0x3A` then `$4007 = 0x0A`**. The `0x08` high-byte flag selects a length-counter index; it is not part of the 11-bit timer period.
- The source's normal music path then writes a patch control value to **`$4004`** and `0x7F` to sweep register **`$4005`**.

**Predicted normal no-SFX $4004 values**, one per music-engine update:

| Update | Read PatS3 index | $4004 value | Duty | Constant volume (0–15) |
| ---: | ---: | --- | --- | ---: |
| 1 | 21 | 0x99 | 50% | 9 |
| 2 | 20 | 0x9A | 50% | 10 |
| 3 | 19 | 0x9A | 50% | 10 |
| 4 | 18 | 0x99 | 50% | 9 |
| 5 | 17 | 0x98 | 50% | 8 |
| 6 | 16 | 0x97 | 50% | 7 |
| 7 | 15 | 0x95 | 50% | 5 |
| 8 | 14 | 0x93 | 50% | 3 |

The next event occurs after the eight-update interval; the table is a **static execution prediction**, not a direct APU log. It assumes the correct initial segment, no player/map/level effect taking the channel and the expected PRG bank selection.

The remainder of this Pulse 2 intro contains **nine notes and seven rests** (192 total sequencer ticks, as documented in the companion audio report). The one initial note above uses short patch 3; the other eight note events in the intro select patch family 2 under the bounded source-guided parser. This is an analytic event count, **not verified sounding output**.

## 4. Timbre changes without changing pitch

Another source-to-ROM cross-check found these short-note patches can change the hardware duty shape within one note:

| Patch | First eight short-note control values (indices 21 down to 14) | Interpretation |
| --- | --- | --- |
| `PatS1` | 58, 17, 15, 96, 96, 95, 95, 95 | 25% → 12.5% → 12.5% → 50% duty (then 50%) |
| `PatS2` | 59, 57, 56, 55, 54, 53, 52, 52 | 25% duty with declining volume |
| `PatS3` | 99, 9A, 9A, 99, 98, 97, 95, 93 | 50% duty; small swell then decay |
| `PatS8` | DA, 19, 58, 57, 56, 55, 54, 53 | 75% → 12.5% → 25% duty (then 25%) |

All values in this table are **hexadecimal** APU control bytes. They describe conditional instrument behavior, not claims that all four appear in the intro. The duty field comes from bits 7–6, constant volume from bit 4, and volume from bits 3–0 of `$4000/$4004`.

Because the control bytes retain the constant-volume flag, these swells and decays are mainly *CPU-programmed*; the game is not simply leaving an NES hardware envelope to run automatically.

## 5. Channel-stealing affects musical state, not just mixing

The routine `Sound_Process` runs Level 2 SFX, Player SFX, Level 1 SFX, Map SFX and Music in that order. Music channel behavior is **conditional on active SFX playback**, not only on queued requests.

**Pulse 2**: `Music_Sq2Track` can read and advance the note position and rest interval before checking `SndCur_Level1`. If this active Level 1 flag is nonzero, the note-on hardware write is skipped, but the `Music_Sq2Rest` event countdown continues. At `PRG031_E5A7`, a matching later check skips the normal music patch/sweep writes and `Music_Sq2NoteLen` decrement and cancels the bend. Therefore the source playback position can advance **while an instrument envelope counter freezes**.

**Pulse 1**: a nonzero `SndCur_Player | SndCur_Map` similarly diverts music note-on and patch updates. Music event advancement continues, but the per-note envelope counter need not advance while the effect owns the channel.

This is a source-confirmed *potential state divergence*, not proof that any particular event was lost in a captured gameplay session. The audio workbench needs to preserve (a) the music-score timeline, (b) actual hardware register writes and channel ownership, and (c) effects and the sequences they suppress. A clean isolated-song export is distinct from a real gameplay audio capture.

The music interpreter's `0x7E` pulse rest only returns without a fresh note-frequency write; it is **not necessarily an instantaneous hardware silence**. A controlled instrument patch, length counter and existing channel state may continue to determine output. `Music_LOST4FB` also affects some rest-path note-length state and must not be guessed without observing its value.

## 6. APU frame-counter synchronization and unavoidable timing uncertainty

`Sound_Engine_Begin` unconditionally writes **0xFF to APU register 0x4017** at the start of the engine call, even on paths that subsequently process pause/resume state. The value selects five-step mode and IRQ inhibition.

The actual NES APU frame-counter reset and its induced quarter/half frame clocks have CPU-cycle-dependent timing. An engine-update log without CPU-cycle timestamps is **not sufficient** for bit-accurate audio reproduction, and a fixed 60 Hz per-update assumption does not specify all analog/mixing/sweep/length details. See NESdev APU Frame Counter hardware reference and note that public references have contained disagreements over the exact post-write cycle alignment; verify behavior in the pinned emulator before making per-cycle acceptance claims.

A clean song initialization path can also write APU `$4015` to reinitialize hardware channel enable state. This needs to be captured along with `$4017` and `$4000–$4013`, not inferred solely from song note data.

## 7. Specific native acceptance test to implement later

Do not start the PR #20 observer untested. Once a bounded, tested launcher exists, collect a source-identified, SFX-free Overworld 1 initial segment in MesenCE 2.2.1 with cycle-stamped APU writes:

1. Capture source ROM SHA-256; save-state hash; input history; game/emulator frame; master-clock state; mapper registers and physical PRG bank mapping.
2. Capture `$4015`, `$4017`, `$4004–$4007` in write order at the **first note-on**. Expect the `$4006/$4007 = 0x3A/0x0A` timer writes on the ordinary note path.
3. In the absence of Level 1 SFX, compare successive `$4004` writes to `99 9A 9A 99 98 97 95 93` on the corresponding eight engine updates. Preserve exact CPU cycles and event states; do **not** represent the list as an observed trace.
4. Record `Music_Sq2Patch`, `Music_Sq2NoteLen`, `Music_Sq2Rest`, `Music_Sq2TrkOff` and `SndCur_Level1` at relevant routine boundaries.
5. In a separate controlled experiment, queue an actual Level 1 SFX to overlap Pulse 2. Test whether music source position and rest counter advance while pitch writes and patch countdown pause; compare with uninstrumented run hashes and the corresponding isolated-song state.
6. Capture before/after `$4017` reset effects as exposed by MesenCE; no timing-invariant assertion before comparing exact emulator semantics. Separate event-code predictions from final mixed-audio fidelity.

Maintain three separate result classes: **ROM-decoded sequence**, **emulator-captured APU writes**, and **rendered audio**. No complete output or identical analog playback is asserted here.

## Conclusion

For SMB3 music, the original ROM and pinned disassembly establish a usable deterministic control structure: song/segment selection → channel event timing → note period and patch choice → a software-driven, reverse-indexed constant-volume/duty envelope → active-SFX arbitration → CPU write stream → APU output.

This note covers only a small, checked portion of that chain and provides falsifiable next steps. No ROM was modified; no original music stream, DPCM sample or extracted game asset was published.


## 8. Overworld 1 note-event patch usage, complete bounded Pulse 2 scan

A read-only stream-boundary audit of the original PRG28 music data for the initial **seven** Overworld 1 segment references (0x0F, 0x10, 0x11, reused 0x10, 0x12, 0x13, 0x14) identifies **81 Pulse 2 note events**, **66 rest events** and no `0xFF` bends in the bounded source tracks.

| Source segment reference | Notes | Rests | Patch 3 notes | Patch 2 notes |
| --- | ---: | ---: | ---: | ---: |
| 0x0F | 9 | 7 | 1 | 8 |
| 0x10 | 7 | 9 | 0 | 7 |
| 0x11 | 6 | 5 | 0 | 6 |
| 0x10 (reused) | 7 | 9 | 0 | 7 |
| 0x12 | 6 | 5 | 0 | 6 |
| 0x13 | 24 | 16 | 0 | 24 |
| 0x14 | 22 | 15 | 0 | 22 |
| **Total** | **81** | **66** | **1** | **80** |

This counts *event occurrences* in the selected arrangement, not unique ROM notes, pitches or assets. The decoder observes the source event/timing byte grammar but is **not verified against native APU writes**. The initial Pulse 1 stream similarly contains seven note events, with one patch-3 and six patch-2 selections, and four rest events. No conclusion about the remaining four channels' instrument use is made from this scan.

The repeated event pattern confirms that source patch identity, note identity, duration and channel-specific audio outcome should remain separate fields in SpriteMine's audio-catalog model.


## 9. Pause does not equal channel arbitration

The entry point `Sound_Engine_Begin` in pinned PRG028 always writes `0xFF` to APU frame counter `$4017` **before** checking queued pause/resume and active pause flags. When `Sound_IsPaused` is nonzero it branches to queue cleanup rather than executing `Sound_Process`, so the usual music track/rest counters do not advance through the normal music interpreter on that call. The pause-effect code can separately write to APU and disable/enable channels. On resume, it re-enables channels and returns to normal processing.

This differs from ordinary sound-effect takeover, where the music interpreter does execute and consumes source timing/events while selectively suppressing a channel's note/envelope writes. Thus "pause," "temporary channel ownership" and "music stop/restart" are different event histories. Reproducible native experiments should record all three separately, including the `$4017` writes.

NESdev documents that writing `$4017` in 5-step mode can clock APU envelope/length/sweep units as part of the reset behavior, with CPU-cycle-sensitive timing. No cycle-exact assertion is made here; source-level knowledge that the write occurs is stronger than our knowledge of its exact hardware timing at the chosen replay frames.


## 10. Source-derived audio RAM probe map and frame-end queue trap

The pinned `smb3.asm` RAM sound block begins at `0x04D0` and ends before `0x0500`. Its consecutive `.ds` declarations were independently counted from `0x04D0` (not guessed from symbol names). A compact set of research-relevant addresses follows:

| CPU address | Southbird symbol | Meaning |
| --- | --- | --- |
| 0x04D3 | `Music_Sq2RestH` | Current Pulse 2 event-duration hold |
| 0x04D4 | `Music_Sq2Rest` | Countdown to next Pulse 2 event |
| 0x04D5 | `Music_Sq2NoteLen` | Pulse 2 instrument patch countdown |
| 0x04D6 | `Music_Sq1Rest` | Pulse 1 music event countdown |
| 0x04D7 | `Music_Sq1NoteLen` | Pulse 1 patch countdown |
| 0x04E1 | `SndCur_Player` | Active player SFX; takes precedence on Pulse 1 |
| 0x04E2 | `SndCur_Level1` | Active Level 1 SFX; takes precedence on Pulse 2 |
| 0x04E6 | `SndCur_Map` | Active map SFX; takes precedence on Pulse 1 |
| 0x04ED | `Sound_IsPaused` | Pause state |
| 0x04F1 | `Sound_QPlayer` | Pending player SFX request |
| 0x04F2 | `Sound_QLevel1` | Pending Level 1 SFX request |
| 0x04F3 | `Sound_QLevel2` | Pending Level 2 SFX request |
| 0x04F5 | `Sound_QMusic2` | Pending Set 2A/B music request |
| 0x04FE | `Music_Sq2TrkOff` | Pulse 2 position in current source segment |
| 0x07F7 | `Music_Sq2Patch` | Stored current Pulse 2 patch selector |

**End-of-frame queue trap:** PRG028 `Sound_Process` processes effects before music and then clears queued `Sound_QMusic1/2`, `Sound_QPlayer`, `Sound_QLevel1/2`, `Sound_QMap` and `Sound_QPause`. Some pause paths also skip directly to queue clearing. Therefore an ordinary endFrame CPU RAM sample can display zero-valued queue variables even when an event was queued and played earlier that frame. To determine whether a jump SFX was requested during a candidate walk-off, use a **write callback** on `0x04F1` or sample the queue immediately before sound-engine processing, with physical PRG writer mapping and frame/cycle information. Use `0x04E1` as an independently sampled *active effect* indicator, but do not infer that it tracks every request's complete history.

These addresses are **source-derived candidates**, not live-confirmed values. The `0x07F7` label comes from the fixed RAM context around `0x07F0` and must also be validated during actual gameplay. Avoid confusing the game-managed music state with APU hardware state. Capture `0x4017` and `0x4004–0x4007` writes separately.

This makes an inexpensive, bounded experiment possible: first record RAM snapshots at source routine boundaries, then add targeted write tracing for just the queue/active-effect values and relevant APU register writes. Avoid an unbounded CPU execution callback. Keep all real game captures private under `F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation`.
