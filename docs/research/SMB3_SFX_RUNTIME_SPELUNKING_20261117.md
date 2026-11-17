# SMB3 PRG1 — Sound-effect synthesis, priorities and APU side effects

Research date: 2026-11-17  
Status: **static, pinned-source reconstruction with independent NES hardware/emulator checks; no new native observation**  
Scope: **Super Mario Bros. 3 USA PRG1 / Revision A**.

Related: [audio structure](SMB3_AUDIO_ROM_SPELUNKING_20261116.md), [music envelopes and arbitration](SMB3_APU_ENVELOPES_AND_ARBITRATION_20261116.md), [MesenCE/FCEUX/NESdev cross-check](SMB3_APU_EMULATOR_CROSSCHECK_20261116.md), [player-physics trace plan](SMB3_PLAYER_PHYSICS.md).

The original ROM and private fixture remain untouched. The source below is the pinned public *disassembly* and emulator implementation. This turn **did not reopen or hash the private original ROM**, execute MesenCE, create an SFX WAV, or validate an APU trace. Every SMB3-specific finding below is **source-derived** unless independently validated as a hardware rule; it must not be promoted to runtime evidence.

## Authoritative references

- [Southbird SMB3 PRG028 at commit 09b1bd81](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg028.asm): `Sound_Process`, `Sound_PlayPlayer`, `Sound_PlayLevel1`, `Sound_PlayLevel2`, `PlayerSnd_Jump`, `SndLev1_1up`, and $4015 handling.
- [Southbird SMB3 PRG031](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm): `Music_Sq1Track`, `Music_Sq2Track`, `Music_TriTrack`, `Music_NseTrack`, shared note-on subroutines.
- [Southbird SMB3 PRG008](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg008.asm): jump and quicksand source-event queues.
- [Southbird RAM and SFX symbols](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm).
- [MesenCE 2.2.1 pinned SquareChannel.h](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/SquareChannel.h), [ApuEnvelope.h](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/ApuEnvelope.h), [NesApu.cpp](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/NesApu.cpp), [DMC SetEnabled](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/DeltaModulationChannel.cpp).
- NESdev hardware specifications: [APU status/control](https://www.nesdev.org/wiki/APU_Status), [APU Pulse](https://www.nesdev.org/wiki/APU_Pulse), [APU Noise](https://www.nesdev.org/wiki/APU_Noise).

## 1. Jump SFX is a counter-driven Pulse 1 synthesizer

Source routine `PlayerSnd_Jump` selects note code 52, stores `SFX_Counter1=0x28` (40 decimal), and writes a hardware-envelope-enabled pulse/sweep configuration through `Sound_Sq1_NoteOn`.

| Stage in routine | Pulse 1 control $4000 | Sweep $4001 | Source-derived interpretation |
| --- | --- | --- | --- |
| On entry | 0x82 | 0xA7 | Duty 50%; **hardware** envelope period 2; sweep enabled, positive adjustment, shift 7 |
| At counter 0x25 | 0x5F | 0xF6 | Duty 25%; **constant volume 15**; sweep enabled, positive adjustment, shift 6 |
| At counter 0x20 | 0x48 | 0xBC | Duty 25%; **hardware** envelope period 8; sweep enabled, negative adjustment, shift 4 |

`SquareChannel::InitializeSweep` uses **bit 3** as sweep-negate flag. The original disassembly's natural-language comments on sweep direction are not authoritative when contradictory: 0xF6 has bit 3 clear, while 0xBC has bit 3 set. Positive sweep shifts *timer period* upward and tends to decrease audible pitch; negative sweep tends to increase pitch, subject to pulse-channel sweep quirks, muting and current timer state.

**Significant distinction from music:** the previously identified 610-byte SMB3 music patch block sets bit 4 throughout (constant-volume mode). The jump effect begins in the NES hardware's automatic-envelope mode, switches to constant volume, then back to hardware envelope. Do not apply a single software-patch interpolation model to every SFX.

Writing $4000 updates hardware envelope settings but does **not** necessarily restart hardware envelope phase; the pinned emulator restarts the envelope on the high pulse timer register write ($4003). Therefore the table predicts **control/sweep writes**, not exact audible amplitude or sample waveform.

The 0x28 counter is a source initialization value, not an experimentally observed 40-frame SFX duration. Pause, preemption, and exceptional control flow can alter actual lifetime.

## 2. SFX queues, arbitration and mixed request encodings

`Sound_Process` visits: Level 2 → Player → Level 1 → Map → Music; queues are then cleared. Queue and active-effect state are **not identical**.

For conventional one-bit flags, `Sound_PlayPlayer`, `Sound_PlayLevel1` and `Sound_PlayLevel2` shift the request byte right and branch on the first set low-order bit, producing a source-derived priority among simultaneous standard requests. Some high-bit cases take special paths **before** these shifts.

Unusual Level 1 codes declared in the original game:
- `SND_LEVELPOOF=0x80`
- `SND_LEVELUNK=0x90`
- `SND_LEVELSHOE=0xA0`
- `SND_LEVELTAILWAG=0xB0`

The high-bit dispatch subsequently compares values against these exact constants. They are **not single independent power-of-two bits**. A generic sound-ID parser must not assume all values are one-hot. The result of OR'ing concurrent requests is not necessarily an independently defined SFX ID; retain the original queue byte and event provenance.

**Special priority gate:** `Sound_PlayLevel1` checks `SndCur_Level1 & 0x40` before reading the new queue. If a 1-Up sound is active, it continues that effect rather than processing newly queued ordinary Level 1 sounds. The 1-Up initializes shared `SFX_Counter2=0x30`. This protection is **within Level 1**; it does not stop the separate Player sound engine from operating on Pulse 1.

Examples of other source-initialized SFX counters (engine updates, **not validated playback durations**):

| SFX (source handler) | Channel/group | Initial counter |
| --- | --- | --- |
| Jump | Player / Pulse 1 | 0x28 |
| Bump | Player / Pulse 1 | 0x0A |
| Fireball | Player / Pulse 1 | 0x05 |
| Swim | Player / Pulse 1 | 0x0E |
| Kick | Player / Pulse 1 | 0x0E |
| Pipe | Player / Pulse 1 | 0x2F |
| Coin | Level 1 / Pulse 2 | 0x35 |
| Power-up | Level 1 / Pulse 2 | 0x36 |
| 1-Up | Level 1 / Pulse 2 | 0x30 |
| Power-up rise | Level 1 / Pulse 2 | 0x10 |
| Vine rise | Level 1 / Pulse 2 | 0x20 |
| Crumble | Level 2 / Noise | 0x20 |
| Flame | Level 2 / Noise | 0x40 |
| Boomerang | Level 2 / Noise | 0x0C |
| March | Level 2 / Noise | 0x0E |
| Skid | Level 2 / Triangle | 0x06 |

No implication that all these effects appear in World 1-1. Shared counters mean effects within a group can overwrite each other's lifetime state.

## 3. Level 2 effects and a second type of music conflict

PRG028 identifies Level 2 synthesis using the **Noise** registers (crumbling brick, flame jet, boomerang and march) and **Triangle** registers (skid). These are not independent sampled audio streams; the engine constructs time-varying register states.

PRG031's Pulse 1 music path explicitly checks active `SndCur_Player|SndCur_Map`; Pulse 2 music checks `SndCur_Level1`. However, the entire PRG031 file has **zero references to `SndCur_Level2`** and its Triangle/Noise music interpreters do not gate their register writes on Level 2 activity.

Because PRG028 calls Level 2 before music in a normal sound update, a due Triangle or Noise music event can **overwrite a Level 2 SFX register write within the same update**. When no new music event is due, the effect's register values can remain. This makes the proper model **ordered APU writes plus channel state**, not a blanket priority flag.

This remains source-derived until tested with time-stamped write captures. The Noise channel additionally has hardware envelope, timer and LFSR state as specified by NESdev and implemented by MesenCE's `NoiseChannel.h`; a control change is not a complete audible waveform.

## 4. Sound completion can reconfigure unrelated channels, including DMC

Normal Player SFX completion (`PlayerSnd_Stop`) writes `$4015=0x1E` then `$4015=0x0F`. Level 1 completion uses `0x0D` then `0x0F`. NESdev defines `$4015` as `---D NT21`; MesenCE `NesApu::WriteRam` applies all five enable bits, not just the effect channel.

- 0x1E: disables Pulse 1, enables Pulse 2, Triangle, Noise, **and temporarily DMC**.
- 0x0D: disables Pulse 2, enables Pulse 1, Triangle and Noise, **DMC remains disabled**.
- 0x0F: enables the four waveform channels, **disables DMC**.

Thus an effect **on a pulse channel can change DMC state** as a side effect. Clearing DMC enable stops new sample-byte fetches but existing shift-register/sample-buffer bits can continue; do not equate 0x0F to immediately forcing DAC output zero. MesenCE also has phase-dependent delayed DMC enable/disable handling. These transitions may affect DMC music percussion or DMA timing, but **no observed truncation, controller corruption or audible bug is claimed**.

For validation, do not only trace `$4000–$4007` and the relevant pulse control. Include `$4015`, the active DMC state, `$4010–$4013`, and where possible DMA reads and DMC enable changes.

## 5. Jump queue is not unique to ordinary jumping

PRG008 `Player_JumpFlyFlutter` ORs `SND_PLAYERJUMP` into `Sound_QPlayer` after the allowed jump-input checks. A **separate quicksand escape path** in PRG008 also ORs the same sound request when the player presses jump to escape.

Therefore a queued jump sound is evidence of an event taking one of several game branches, not proof of a unique movement origin. The presence of `Player_Frame=0x40` with the jump cue would still need ROM-location, player-state and CPU-path correlation; absence of a pending queue in a frame-end snapshot is non-evidence because PRG028 clears it.

## 6. Candidate narrow native trace

The following CPU RAM addresses were calculated by counting `.ds` declarations from the pinned disassembly's `.org $04D0` sound block:

| CPU RAM | Meaning |
| --- | --- |
| 0x04E0 | `SFX_Counter1` (Player) |
| 0x04E1 | `SndCur_Player` |
| 0x04E2 | `SndCur_Level1` |
| 0x04E3 | `SndCur_Level2` |
| 0x04E8 | `SFX_Counter2` (Level 1) |
| 0x04E9 | `SFX_Counter3` |
| 0x04EA | `SFX_Counter4` (Level 2) |
| 0x04F1 | `Sound_QPlayer` |
| 0x04F2 | `Sound_QLevel1` |
| 0x04F3 | `Sound_QLevel2` |

Candidate experiments:

1. **Jump synthesis:** bounded, passively trace `$4000–$4003`, `$4015`, relevant active counters and `$04F1` write events. Check the initial register sequence and sweep/control changes at `SFX_Counter1=0x25/0x20`.
2. **Coin vs protected 1-Up:** from reproducible states, trigger a coin during an active 1-Up and record `SndCur_Level1`, `$04F2` writes and `$4004–$4007` writes; test whether the queued coin gets ignored or merely postponed, without guessing.
3. **Noise/Triangle ordering:** trigger a Level 2 effect during music, recording `$4008–$400F` in write order with CPU cycle count. Check whether a music note overwrites an effect write in the same update.
4. **DMC side effects:** trace `$4015` and actual DMC samples around Player and Level 1 SFX completions; assess whether any enable/disable or sample-read effect is observable.
5. **Mario walk/fall:** collect `Player_InAir`, `Player_Frame`, underfoot logical tiles, `$04F1` queue writes and `$04E1` active effect over frames 448396–448408. Preserve immutable baseline and fail closed if callbacks produce errors.

MesenCE 2.2.1's official Lua write callback runs **before** hardware writes; callbacks that return integers can **change** the write. A passive observer returns **nothing**, never mutates state, uses debug memory reads for unrelated RAM state and retains cycle/frame/bank provenance. No unbounded CPU execution callbacks. Native A/B/A acceptance is required before promoting any source hypothesis to a verified gameplay effect.

## Engineering takeaway

Treat source effect identity, request, active group/state, synthesis program, **ordered APU register writes**, DMC DMA side effects and resulting sound as separate provenance layers. Player and Level 1 pulse effects coexist with music differently from Level 2 Noise/Triangle effects. This makes an SMB3-only SFX inspector tractable without prematurely generalizing to other NES games or distributing original sound/ROM data.

**Verification boundary:** all SMB3-specific behavior here is static disassembly reasoning; hardware bit semantics are independently confirmed by pinned MesenCE and NESdev. No private ROM validation or live emulator trace was produced in this session.
