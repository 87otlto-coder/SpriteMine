# MesenCE source-level interoperability inventory

Research date: 2026-11-09  
Target upstream revision: `4b8a196e299b3de297b204fd1208d2981562c89b` (MesenCE `master` at inspection)  
Status: **source-inspected only; no compiled adapter or runtime validation**.

## Objective

Assess the smallest reproducible path to capture the **same** SMB3 PRG1 emulator state required for sprite reconstruction, including 64 OAM entries, palette memory, effective MMC3 CHR mapping, PPU state/frame/scanline/cycle, renderer output and repeatable replay.

## Upstream functions identified

| File / exported function | Source-level observation | Unresolved integration question |
|---|---|---|
| `InteropDLL/DebugApiWrapper.cpp::InitializeDebugger` | Starts debugging through `_emu->InitDebugger()` | Need lifecycle/ownership and debugger-enabled build |
| `IsExecutionStopped`, `Step`, `ResumeExecution` | Debugger controls execution | Need a provably stable pause point, not just successive asynchronous API calls |
| `GetConsoleState`, `GetCpuState`, `GetPpuState` | State output into `BaseState&` | Confirm structure layout/version, scanline/cycle and whether snapshot is atomic |
| `GetPpuToolsState` | Captures PPU tooling state | Distinct from `GetPpuState`; confirm required size and state generation |
| `GetMemorySize`, `GetMemoryState` | Read selected memory region via `MemoryType` | Verify OAM, palette RAM, effective CHR and mapper memory types; debugger mutation must be avoided |
| `GetSpriteList` | Accepts supplied state, VRAM, OAM, palette and multiple output buffers | Buffer sizes, struct layout and state coherence need an executable probe |
| `GetTilemap`, `GetPaletteInfo` | Tilemap and palette tooling exists | Viewer output is not proof of final composited pixels |
| `SetViewerUpdateTiming` | Viewer scanline/cycle update controls | Does not itself guarantee a single synchronized multi-source capture |
| `InteropDLL/EmuApiWrapper.cpp::LoadRom`, `Pause`, `SaveStateFile`, `LoadStateFile` | ROM/load and state operations exist | Need deterministic input replay and clear emulator frame boundary |
| `RegisterNotificationCallback` | Notification callbacks available | Determine whether a suitable stable frame-complete event exists |

Sources pinned to revision:
- https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/InteropDLL/DebugApiWrapper.cpp
- https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/InteropDLL/EmuApiWrapper.cpp
- https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/NES/Debugger/NesPpuTools.cpp

## Key technical finding: debug sprite preview is not the final screen

In `Core/NES/Debugger/NesPpuTools.cpp`, `GetSpritePreview` loops over the 64 `DebugSpriteInfo` entries and draws nonzero sprite preview pixels into a separate output buffer. It does **not** independently establish that those pixels survive all NES rendering effects, including background priority and the hardware's per-scanline sprite limit. Therefore a perfect match to the debugger sprite-only preview **would not** prove a pixel-perfect composite frame.

The same source uses `Y + 1` for the display position of a sprite entry. `GetSpriteInfo` handles 8×8 vs 8×16 layout, pattern table selection, palette bits, horizontal/vertical flips and sprite priority as distinct fields. These are useful implementation references, but should be validated against captured SMB3 behavior.

Also note that exported `BaseState&` C++ structures in an interop function signature do not imply a stable Python-callable ABI. ctypes should **not** assume their layout; investigate a tiny versioned C ABI shim if no safe documented interop binding exists.

## Initial experiments

1. Build upstream pinned revision on Windows; record toolchain, build flags, produced binaries, and exact license notice.
2. Start a debugger-enabled process and stop at an identifiable frame/scanline, then capture two consecutive snapshots. Check same-frame invariants and unchanging hashes while stopped.
3. Prove `GetPpuState`, `GetPpuToolsState`, OAM, palette, effective CHR mapping and screen image are from one coherent instant; explicitly report missing fields.
4. Replay from saved state and recorded inputs; compare hashes of non-copyrighted **metadata**. Keep raw screenshots/state files local.
5. Reconstruct one Mario sprite from hardware components, compare both sprite-only and composited screen observations. Record mismatches due to priority, sprite limits, timing or mapper bank changes.

## Stop/go criteria

**Go:** Repeatable same-frame OAM/palette/CHR state and independently reconstructed Mario tile/pixel data with documented screenshot comparison, plus a small stable adapter contract and licensing plan.

**Stop and reconsider:** Native API lacks atomic state capture, cannot safely manage state layouts, or cannot produce reproducible frame identities. Investigate minimal C++ instrumentation in that case; keep all emulator code outside SpriteMine until license obligations are understood.

## Open questions

- Which `MemoryType` values expose raw OAM, palette RAM, CHR mapping and mapper state simultaneously?
- Can final unfiltered frame pixels be captured with a frame-complete callback rather than a screenshot file race?
- Does MMC3 PRG1 rendering require scanline-sensitive mapper event tracing for accurate graphics provenance?
- Is MesenCE integration best as an in-process C++ shim or controlled external recorder? No decision until the runtime spike.

**Do not treat this inventory as integration validation.**
