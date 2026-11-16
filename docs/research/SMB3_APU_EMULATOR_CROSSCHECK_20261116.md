# SMB3 audio findings — authoritative MesenCE/FCEUX/NESdev cross-check

Research date: 2026-11-16  
Status: **primary-emulator source review + independent emulator/hardware corroboration**  
Scope: SMB3 **USA PRG1 / Revision A**. No new MesenCE run or APU capture was conducted during this cross-check.

This note cross-checks [SMB3 audio ROM spelunking](SMB3_AUDIO_ROM_SPELUNKING_20261116.md) and [APU envelopes and arbitration](SMB3_APU_ENVELOPES_AND_ARBITRATION_20261116.md). The audio *hardware* implementation is independently substantiated; MesenCE and FCEUX do **not** themselves prove the game-specific SMB3 note counts, tempo loops, SFX precedence or ROM-byte hashes. Those conclusions continue to depend on the verified ROM and Southbird disassembly until instrumented.

## Source policy — primary and pinned where possible

1. **Mesen Community Edition 2.2.1, exact released source commit** \`20ba206cef5ba207c21203176d02cb9f43dda9fb\`. This is the **same build/source revision** that our previous SpriteMine acceptance documents identify. See [MesenCE release](https://github.com/nesdev-org/MesenCE/releases/tag/2.2.1), [APU frame counter](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/ApuFrameCounter.h), [pulse channel](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/SquareChannel.h), [envelope](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/ApuEnvelope.h), [length counter](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/ApuLengthCounter.h), [DMC](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/APU/DeltaModulationChannel.cpp), [NES CPU/DMA](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesCpu.cpp), [MMC3](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h).
2. **MesenCE's official Lua debugger/API specification at the same commit:** [LuaDocumentation.json](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json), [LuaApi.cpp](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Debugger/LuaApi.cpp), [ScriptingContext.cpp](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Debugger/ScriptingContext.cpp).
3. **FCEUX**, independently developed emulator: [TASEmulators/fceux/src/sound.cpp](https://github.com/TASEmulators/fceux/blob/master/src/sound.cpp). This source provides corroboration for register bitfields, volume/duty, pulse muting, length counter and DMC formulas; it is **not** used to assert exact MesenCE 2.2.1 timing.
4. **NESdev hardware documentation**: [APU Pulse](https://www.nesdev.org/wiki/APU_Pulse), [APU Frame Counter](https://www.nesdev.org/wiki/APU_Frame_Counter), [APU DMC](https://www.nesdev.org/wiki/APU_DMC), [DMA](https://www.nesdev.org/wiki/DMA), [Controller reading](https://www.nesdev.org/wiki/Controller_reading_code), [APU Registers](https://www.nesdev.org/wiki/APU_registers). NESdev is the reference for *hardware semantics*, not SMB3 gameplay logic.

The original ROM is unchanged; the earlier accepted SHA-256 is \`4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579\`. It was **not** newly compared against emulator execution in this review.

## Finding A — software envelope: confirmed, with a caveat

The verified SMB3 music patch block was previously shown to have bit 4 set in all 610 bytes. MesenCE \`ApuEnvelope::InitializeEnvelope\` treats bit 4 as \`_constantVolume\`, stores \`regValue & 0x0F\` as a volume, and \`GetVolume()\` selects this stored value rather than the hardware envelope decay counter. FCEUX independently selects the constant-volume nibble when the corresponding mode bit is set. NESdev defines \`$4000/$4004 = DDLC VVVV\`, with bit 4 the constant-volume selector.

**Confirmed hardware implication:** the SMB3 source's repeated \`$4004\` or \`$4000\` control writes implement CPU-driven duty/volume changes. **Qualification:** the hardware envelope clock **continues internally** even when its output is overridden by constant-volume mode. The actual pulse reaches the mixer only when it passes the length-counter, timer-period, sweep and duty-phase gating. A predicted control nibble of 9 does **not** mean that nine units of audio are continuously audible.

MesenCE \`SquareChannel::WriteRam\` writes \`_duty=(value&0xC0)>>6\`, and \`UpdateOutput\` multiplies the duty-sequence bit by \`_envelope.GetVolume()\`. It mutes periods below eight or sweep-target overflow. Its \`GetState()\` exposes duty, period, sweep, length, envelope and current output; these are useful named internal fields **in the C++ API**, not a guarantee of stable Lua table names.

## Finding B — high timer byte includes length index: confirmed

MesenCE \`SquareChannel::WriteRam\` for \`$4003/$4007\`:

- Loads a length-counter value from \`value >> 3\` via a 32-entry lookup.
- Sets the 11-bit pulse period from \`(value & 0x07) << 8\` and the existing low timer byte.
- Resets waveform duty position and envelope start flag.

FCEUX independently uses the same 32-entry length table, including **index 1 = 254**. MesenCE's \`ApuLengthCounter\` contains the same value; the reload takes effect only if its channel is enabled and obeys delayed reload behavior. This supports the earlier correction that writing \`$4007=0x0A\` is **not** the same as writing a twelve-bit pitch period: the pitch uses high value 2 and the \`0x08\` bit sets length-counter index 1. MesenCE's reload and length-control behavior can still change the actual audible duration.

## Finding C — $4017 reset is delayed; do not model as an instantaneous write

MesenCE 2.2.1 \`ApuFrameCounter::WriteRam\` captures the value and schedules a reset **3 or 4 CPU cycles after the write** according to CPU-cycle parity. It can inhibit the IRQ immediately; when the pending mode update takes effect and bit 7 is set, it calls \`FrameCounterTick(HalfFrame)\`, which clocks both the quarter-frame units and the half-frame units (length/sweep). A small blocking counter prevents coincident double clocks.

Consequences:

- The earlier claim that SMB3's \`$4017=$FF\` triggers hardware frame-counter synchronization is **confirmed**, but a simple model that clocks all units at the write's exact CPU timestamp is **incorrect for this pinned emulator**.
- Because Southbird's SMB3 engine writes \`$FF\` on its sound-engine entry and executes the engine on the normal per-frame path, there is a source-based hypothesis that it repeatedly resets the 5-step sequencer *before its free-running final step*. This has not been confirmed by a full run of actual \`$4017\` writes; capture the register timing first.
- NESdev reference pages have historically disagreed about describing this as “2/3” versus “3/4” cycles. For **our exact emulator acceptance**, use the pinned implementation's **3/4 CPU-cycle model**, not a casual paraphrase. Do not represent the model as conclusive physical hardware measurement.

## Finding D — DMC sample address/length and actual reads: confirmed

MesenCE \`DeltaModulationChannel::WriteRam\` sets:
- \`$4012\`: CPU sample start \`0xC000 | (value << 6)\`.
- \`$4013\`: sample byte count \`(value << 4) | 1\`.
- \`$4010\`: IRQ/loop/rate.
- \`$4011\`: output DAC level (which can change output immediately).
- \`$4015\` via \`NesApu::WriteRam\`: DMC enable/start/stop behavior.

FCEUX independently defines the same \`$4012/$4013\` formulas. MesenCE's DMC reader increments the sample CPU address after each byte, wrapping from \`$FFFF\` to \`$8000\`. The CPU, not a simple private PCM buffer, performs DMA reads through the memory manager. For MMC3, \`UpdatePrgMapping\` maps the last PRG bank at \`$E000–$FFFF\` in both PRG modes; this supports the earlier note that Overworld 1's specifically decoded samples at \`$E000/$E980/$EA80\` are fixed-bank sample sources.

**Boundary:** registering DMC start/length/rate writes does not itself prove which bytes the DMA actually fetched or that a sound played to completion. Detect DMC enables, IRQ, truncation/restart, DMA and mapper state separately.

## Finding E — DMC playback can interfere with controller input (new cross-domain risk)

MesenCE's \`NesCpu::ProcessPendingDma\` includes explicit special handling for DMC DMA overlapping CPU reads from \`$4016/$4017\`, including NES/Famicom-specific behavior and a \`_isDmcDmaRead\` debugger distinction. NESdev explains the NTSC DPCM-controller double-clock/bit-deletion problem, as well as DMC and OAM DMA interactions.

**Practical implication for SpriteMine:** identical recorded button *intent* is not alone sufficient to guarantee identical gameplay if DMC timing, CPU parity, save state or emulator settings change. This is a hardware/emulator risk, **not evidence** that the accepted 24-frame Mario replay suffered such corruption. For A/B/A validation, preserve controller-read behavior, emulator build/config, cycle timing and audio/DMC state; never “disable audio for speed” in an input-dependent acceptance test without checking neutrality.

## Finding F — Lua capture design: important hazards verified in official API

The pinned MesenCE Lua docs and \`ScriptingContext::InternalCallMemoryCallback\` confirm:
- \`emu.addMemoryCallback\` supports \`read\`, \`write\`, \`exec\`, with optional NES CPU/memory-space arguments. **Writes run before the actual write**.
- The callback receives \`address,value\`, and **returning an integer can replace the value** used for a read/write. A forensic observer should return **no value**; it must never return an integer or mutate emulator memory.
- CPU-memory \`emu.read\` can have side effects. The official enum provides \`emu.memType.nesDebug\` for CPU debug reads **without read side effects**. This matters especially for \`$4015\`, controller ports, PPU registers and DMA-sensitive paths. \`emu.read\` with default CPU-memory space is not inherently harmless.
- \`emu.getCpuCycleCount()\` is documented as elapsed CPU cycles; the NES console implements its “master clock” as CPU cycle count. \`emu.getState()\` explicitly constructs a **uint32** \`masterClock\` value, which can wrap/truncate. Prefer \`getCpuCycleCount()\` (and verify its Lua numeric representation) for long captures.
- \`emu.getState()\` is officially warned to expose version-dependent internal fields. Do not hardcode an undocumented \`state.apu.*\` schema as a stable public API. Also avoid serializing the whole console state inside every CPU memory callback.
- \`emu.addEventCallback\` can capture frame boundaries and input-polling events; **frame-end only** is insufficient for queue variables that SMB3 clears earlier in the frame.

Source: the official [Lua API specification](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json), [implementation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Debugger/LuaApi.cpp), and [callback execution](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Debugger/ScriptingContext.cpp).

## Finding G — emulator configuration can change interpretation

The pinned pulse source conditionally swaps hardware duty-cycle mapping when \`SwapDutyCycles\` is set; the DMC source checks options such as \`ReduceDmcPopping\`, \`ReverseDpcmBitOrder\`, and \`EnableDmcSampleDuplicationGlitch\`. These are source-visible configuration-dependent branches. **Do not assume** the current user's settings or whether they are enabled. A faithful original-SMB3 audio validation needs the effective console model, region, APU settings, audio filter/mixing settings and emulator revision captured alongside every test. Distinguish any emulator audio-enhancement option from actual ROM hardware behavior.

## Reconciliation with existing SpriteMine research

| SpriteMine claim | Cross-check status |
| --- | --- |
| 610-byte patch block, 14 source patch tables, 8 selector slots and shared source family | **Game-ROM claim from earlier original-ROM research**; emulators establish how resulting bytes are interpreted, not the SMB3 count |
| \`$4004\` / \`$4000\` patch changes pulse duty and constant-volume output | **Hardware confirmed** by MesenCE, FCEUX, NESdev |
| Opening Overworld 1 predicted patch writes \`99 9A 9A 99 98 97 95 93\` | **Source/ROM-derived test vector only**; emulator semantics make it plausible but live APU log is pending |
| \`$4007=0x0A\` produces period-high=2 and length-table index=1 | **Hardware confirmed**; audible output also depends on channel enable, length/sweep, phase and rest of APU state |
| \`$4017=$FF\` resets 5-step counter | **Confirmed with 3/4 CPU-cycle delay in pinned MesenCE**; not instantaneous |
| DMC tables give CPU address/length using hardware formulas | **Hardware confirmed**; exact SMB3 cue tables remain original-ROM work |
| Source music position can advance while SFX masks note/patch updates | **SMB3 disassembly-derived only**, not independently provable from a generic emulator |
| Lua write callbacks are passive by default | **Conditionally true only when observer does not return integers or modify state**; current implementation allows replacements |
| Captured inputs always replay identically regardless of DMC state | **False as a general hardware claim**; input/DMC DMA interlock exists |

## Practical, bounded next validation

When native MesenCE work resumes, use one focused APU event trace around the **first Overworld 1 Pulse 2 note**. Log CPU-cycle count, frame number, \`$4017\`, \`$4015\`, \`$4004–$4007\` writes and a small read-only snapshot of sound RAM (\`0x04D4/0x04D5/0x04E2/0x04FE/0x07F7\`), plus the active ROM bank/CPU code mapping. No broad \`$0000–$FFFF\` instruction callback is needed. Validate the expected timer and eight \`$4004\` patch writes against the baseline run; add a separate intentionally overlapping Level 1 SFX test only afterwards.

Never claim cycle-accurate register playback, DPCM waveform fidelity or input neutrality from static documentation alone. Before accepting instrumentation, compare observed gameplay frames, controller reads and event hashes with the known uninstrumented replay.

## Licensing

Sources are linked and interpreted, not copied. No third-party code, copyrighted ROM, note stream, samples or game audio has been committed. Check source licenses separately before integrating emulator algorithms into SpriteMine.
