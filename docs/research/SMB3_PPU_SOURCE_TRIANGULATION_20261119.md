# SMB3 PRG1 source triangulation — PPU commit and initial-screen redraw

**Research date:** 2026-11-19. **Status:** primary source analysis, not a new native MesenCE verification.

**Pinned versions**:
- Southbird SMB3 PRG1 disassembly: https://github.com/captainsouthbird/smb3/tree/09b1bd81a788de8ceec664a34094e84ddb463117
- MesenCE 2.2.1: https://github.com/nesdev-org/MesenCE/tree/20ba206cef5ba207c21203176d02cb9f43dda9fb
- NESdev: https://www.nesdev.org/wiki/PPU_registers and https://www.nesdev.org/wiki/Programming_MMC3

## Findings directly relevant to draft PR #24

**1. PPU commit code is shared by steady-state NMI and initial redraw.** Southbird's
[PRG/prg026.asm Scroll_Commit_Column, around lines 3346–3448](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L3346-L3448)
shows a pattern transfer of 30 bytes at $20xx, then 24 at $28xx,
with $2000 PPU increment mode set to 32. The separate attribute branch
loads the $2006 address afresh for each of 14 $2007 writes and
increments the attribute address by 8 with a screen switch on carry.
The path **does not** have 14 contiguous hardware VRAM addresses even
though the corresponding $2007 writes can be adjacent in a filtered event
log. Distinguish these representations.

Southbird's [PRG/prg031.asm around lines 1533–1553](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg031.asm#L1533-L1553)
invokes this commit routine in the normal NMI-selected update.
But [PRG/prg030.asm around lines 4887–4927](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L4887-L4927)
shows that \`Scroll_Dirty_Update\` also generates, commits and iterates
both pattern and attribute columns during full-screen initialization.
[PRG030 around 1665–1683](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L1665-L1683)
explicitly invokes it on level entry.

**Acceptance risk:** \`research/mesence/verify_ppu_commit_trace.py\`
currently allows only scanline 240–260-ish \`$2007\` records. NESdev states
$2007 accesses are valid in VBlank **or when both rendering bits in PPUMASK
are disabled**, even during nominally visible scanlines.
Source: https://www.nesdev.org/wiki/PPU_registers ;
MesenCE [NesPpu.cpp UpdateState around 1557–1571](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L1557-L1571)
likewise permits mapper VRAM writes when \`!IsRenderingEnabled()\`.
Therefore PR #24's conservative filter could exclude legitimate
\`Scroll_Dirty_Update\` writes from the bonus-room entrance.
**This has not yet been observed in the private trace, and is not an
explanation for an emulator process exiting during capture.**
Fix the verifier only after confirming how to read effective rendering state
reliably without conflating PPUMASK writes and delayed internal state.

**2. Disassembly mirroring comments use a conflicting terminology.**
At [PRG/prg030.asm around lines 1646–1663](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L1646-L1663),
source comments label \`LDA #$01 / STA MMC3_MIRROR\` as
"vertical mirroring" for nonvertical gameplay; but
[Southbird smb3.asm label around line 316](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/smb3.asm#L316)
defines \`MMC3_MIRROR=$A000\` and describes bit 1 as vertical mirroring.
Pinned [MesenCE MMC3.h, around lines 85–87](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h#L85-L87)
calls bit 1 **horizontal mirroring**, consistent with the actual physical
pairing and with NESdev's distinction between *vertical arrangement*
and *horizontal mirroring*:
https://www.nesdev.org/wiki/Programming_MMC3

Verified physical CIRAM alias model for this mapper:
- $A000 bit 0 = 0: $2000↔$2800 (physical 0), $2400↔$2C00 (physical 1).
- $A000 bit 0 = 1: $2000↔$2400 (physical 0), $2800↔$2C00 (physical 1).
A “vertical” word from a historical assembly comment cannot override the
mapper's actual physical address mapping. The PR #24 Python alias mapping
uses the latter; preserve that choice.

**3. MesenCE native $2007 write notifications are delayed and asymmetric.**
Pinned [NesPpu.cpp at $2007 WriteRam](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L497-L523)
latches CPU writes, and [UpdateState at ~1557](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp#L1557-L1571)
calls the mapper directly for normal nametable writes; the
\`ProcessPpuWrite(NesPpuMemory)\` notification shown there is for the
palette path. Do not count callbacks or CPU bus transactions as committed
physical writes without subsequent physical-memory evidence.

## External reference triage

- **Primary:** Southbird PRG1 bit-exact disassembly, pinned MesenCE and NESdev.
- **Useful independent tooling:** https://github.com/fortenbt/Ghidra-SMB3INES-Loader
  maps PRG1 symbols into banked overlays; author explains its limitation on
  flow across overlays: https://smb3.bf0.org/ghidra-loader/ghidra-plugin/2019-08-20-ghidra-loader/
  Do not add a Java/Ghidra dependency for this narrow Python sprint.
- **Secondary derivative:** https://github.com/zmetzing/x16-smb3 converts
  Southbird's NESASM to cc65 and claims PRG1 byte matching for its NES target;
  it is not an independent account of the original game's internals.
- **Game recreations:** https://github.com/uiters/Super-Mario-Bros-3 and
  https://github.com/naulan-chrzaszcz/SuperMarioBros.3-pygame are
  simulations/clones, not original 6502 source and not emulator accuracy or
  source-offset authorities.
- **Copyright:** Southbird's disassembly and the Ghidra loader have no
  declared GitHub license; use for analysis and independently authored
  implementations, not by copying their source into the public SpriteMine
  repository. A fan clone's MIT license does not license Nintendo's original
  ROM or graphics. Historical leaks are unnecessary and should not enter the
  workflow.

## Unresolved action items

1. Diagnose the Windows exit status \`4294967295\` on PR #24 by reading
   only the **private** capture leg emulator logs in
   \`pipe-replay-c62ca5ca\`. Determine whether it is Lua compilation,
   callback/reentrancy, unsupported state key, or runtime timeout.
   **Do not assert a cause without a log.**
2. Confirm native register callback state keys and effective rendering flag.
3. Decide how to accept off-vblank writes when rendering disabled, with
   explicit uncertainty handling for PPUMASK transition delays.
4. Run bounded A/B/A replay with source hashes and compare physical CIRAM
   and mirrored nametable debug views. Never classify incomplete or skipped
   frames as a full native acceptance.
