# Research: SMB3 runtime capture feasibility

Branch: `research/smb3-emulator-feasibility`  
Research status: **open / unproven**  
Game: SMB3 US PRG1 / Revision A, mapper 4 (MMC3).

## Question

Can SpriteMine obtain synchronized, reproducible OAM, palette, effective CHR mapping, scanline/frame state, and final rendered pixels from MesenCE without tightly coupling the PySide6 application to the emulator?

A pinned source API inventory and renderer caveat analysis is available in [MESENCE_API_INVENTORY.md](MESENCE_API_INVENTORY.md).

## Known source-level observations (not a successful integration)

MesenCE's `InteropDLL/DebugApiWrapper.cpp` declares `GetSpriteList`, `GetTilemap`, `GetPaletteInfo`, and memory access functions. `InteropDLL/EmuApiWrapper.cpp` provides ROM load and save-state functions. `Core/NES/Debugger/NesPpuTools.h` contains PPU tooling. These are promising **code-level interfaces**, not evidence that a stable external bridge or atomic capture exists.

Links:
- https://github.com/nesdev-org/MesenCE/blob/master/InteropDLL/DebugApiWrapper.cpp
- https://github.com/nesdev-org/MesenCE/blob/master/InteropDLL/EmuApiWrapper.cpp
- https://github.com/nesdev-org/MesenCE/blob/master/Core/NES/Debugger/NesPpuTools.h
- https://www.nesdev.org/wiki/PPU_programmer_reference

Record the exact MesenCE commit/build in every experiment.

## Experiments (in order)

1. **Build feasibility:** Compile/run the selected MesenCE version on Windows and document the compiler/runtime and license boundary.
2. **Repeatable state:** Load the verified SMB3 ROM, enter a deterministic gameplay state, save/load state, replay a known controller sequence and record consistent frame identifiers.
3. **Single-frame acquisition:** Extract OAM (64 entries), palette RAM, CHR data and MMC3 bank mapping from the same pause point; document API calls and any race/timing limitations.
4. **Reconstruction:** Render Mario's OAM components from captured CHR/attributes/palette, checking flips, transparency, priority and 8-sprites-per-scanline behavior. Compare against the emulator frame without claiming every hardware entry is visible.
5. **Scanline mapping:** Check whether MMC3 CHR mappings / other rendering state can change during a frame; avoid treating a single frame-level snapshot as complete where it is not.
6. **Audio spike:** Capture a short, reproducible PCM section if available without introducing another emulator dependency.

### New Lua-first execution path (2026-11-09)

[research/mesence](../../research/mesence/README.md) contains an original, small Lua `endFrame` recorder and stdlib Python capture validator. It exploits verified upstream API *declarations*, but MesenCE runtime behavior and frame synchronization are **not yet proven**. Both independent research CI workflows passed: stock Lua 5.4 syntax check and synthetic capture validation, plus the normal Python matrix. The emulator's bundled Lua version is different from the stock parser, so runtime execution remains a separate gate. File I/O/OS permission must be explicitly enabled in MesenCE for the probe to save data; do not turn on network access. A second CI run also executed the Lua recorder against a synthetic `emu` API and validated two emitted frame captures in Python (7 unit tests passed). Actual MesenCE execution remains untested.

## Required evidence per experiment

- Date, hypothesis, command/build instructions and emulator commit.
- SHA-256 of user-supplied ROM and state/capture fixtures (do not commit those bytes).
- Controller input history; emulation region; precise frame/scanline.
- Raw and visual comparison results, observed limitations and failure modes.
- Conclusion: **proven**, **partially proven**, **disproven**, or **unresolved**.
- Decision: adapter API design or specific fallback experiment.

## Gate to implementation

Do not proceed with a live Sprite Inspector until one complete SMB3 frame can be reconstructed from synchronized emulator observations with demonstrable source mapping and repeatable state replay. If external interop is unreliable, investigate a minimal C++ instrumentation adapter; use FCEUX only after recording why it is preferable. Review GPLv3 obligations before distributing linked/forked emulator code.

## Windows research setup (PowerShell)

Existing owner setup: the research branch is already checked out in `F:\Dev\ROMMAGE\TOOLS\SpriteMine-research` and MesenCE is installed in `TOOLS`. No additional emulator source clone is required for the Lua experiment. Refresh the research checkout and create the capture directory with:

```powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility
New-Item -ItemType Directory -Force -Path "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE" | Out-Null
```

Expected: research checkout is current and a local capture directory exists. Follow the Lua experiment guide at `research/mesence/README.md`. Build instructions for a custom MesenCE adapter remain TBD; no C++ integration has been verified.

## Experiment log

| Date | Experiment | Status | Evidence |
|---|---|---|---|
| 2026-11-08 | Source API surface reconnaissance | Source inspected; integration unproven | Source links above |
| 2026-11-09 | Pinned interop API and debugger-preview analysis | Source inspected; no runtime proof | [API inventory](MESENCE_API_INVENTORY.md) |
| 2026-11-09 | Lua probe syntax / structural validator | Automated checks passed; actual MesenCE run pending | [Lua experiment](../../research/mesence/README.md) |
| TBD | Windows build, reproducible state | Not started | — |
| TBD | Atomic OAM/palette/CHR capture | Not started | — |
| TBD | Independent Mario frame reconstruction | Not started | — |

## 2026-11-09: First on-device capture — partially proven

**Now proven:** Real MesenCE/SMB3 Lua file output and two valid endFrame capture sets, source ROM identity, OAM and palette buffer sizes, and video buffer dimensions. A structural capture success is supported by the owner's private ZIP and local `verify_capture.py` execution.

**New blocking observation:** Two 8×16 OAM entries spatially overlap visible Mario, use odd tile numbers (5, 7), and therefore select PPU table `0x1000–0x1FFF`. At both captured endFrame moments that table is entirely zero. The mapped pattern snapshot cannot reconstruct the visible character. An MMC3 bank switch between sprite rendering and VBlank or the PPU debug read mapping is a hypothesis, **not yet a finding**.

**Next experiment:** Compare `startFrame` and `endFrame` PPU pattern state on a controlled scene; if still blank, instrument PPU rendering or mapper address resolution at scanlines that contain Mario. Maintain original capture data outside GitHub. Use `research/mesence/diagnose_capture.py` for repeatable content-free diagnostics.

## 2026-11-09: Live phase comparison succeeds

Second on-device experiment returned two matched `startFrame` (scanline -1) / `endFrame` (scanline 240) observation pairs, frames 136117–136118. At start, upper pattern area had 2,991 nonzero bytes and all 5 potentially visible OAM odd-tile references were nonblank. At end, upper pattern area was zero and all 5 referenced patterns appeared blank. Both frames were consistent. **Established:** the endFrame view is not a reliable substitute for a rendering-time CHR mapping. **Not established:** which mapper register writes cause this, exact physical ROM banks for Mario, sprite visibility, or synced frame-pixel reconstruction.

Next research task: bounded tracing of MMC3 bank selection register writes (`$8000/$8001` and mirrors) with frame/PPU position and a clear note that Lua CPU write callbacks fire **before** writes are applied. Do not infer resulting mapped bytes from pre-write samples.
