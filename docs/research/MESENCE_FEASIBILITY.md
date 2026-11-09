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

[research/mesence](../../research/mesence/README.md) contains an original, small Lua `endFrame` recorder and stdlib Python capture validator. It exploits verified upstream API *declarations*, but MesenCE runtime behavior and frame synchronization are **not yet proven**. Both independent research CI workflows passed: stock Lua 5.4 syntax check and synthetic capture validation, plus the normal Python matrix. The emulator's bundled Lua version is different from the stock parser, so runtime execution remains a separate gate. File I/O/OS permission must be explicitly enabled in MesenCE for the probe to save data; do not turn on network access.

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

Keep emulator sources outside SpriteMine, which should never contain a copied GPL core or copyrighted ROM:

```powershell
Set-Location -Path $HOME
git clone https://github.com/87otlto-coder/SpriteMine.git "$HOME\SpriteMine"
Set-Location -Path "$HOME\SpriteMine"
git fetch origin
git switch research/smb3-emulator-feasibility

Set-Location -Path $HOME
git clone https://github.com/nesdev-org/MesenCE.git "$HOME\MesenCE-research"
Set-Location -Path "$HOME\MesenCE-research"
git rev-parse HEAD
```

Expected: the first checkout contains this research plan; the final command prints the exact MesenCE source revision. Build instructions and results remain TBD until verified on Windows.

## Experiment log

| Date | Experiment | Status | Evidence |
|---|---|---|---|
| 2026-11-08 | Source API surface reconnaissance | Source inspected; integration unproven | Source links above |
| 2026-11-09 | Pinned interop API and debugger-preview analysis | Source inspected; no runtime proof | [API inventory](MESENCE_API_INVENTORY.md) |
| 2026-11-09 | Lua probe syntax / structural validator | Automated checks passed; actual MesenCE run pending | [Lua experiment](../../research/mesence/README.md) |
| TBD | Windows build, reproducible state | Not started | — |
| TBD | Atomic OAM/palette/CHR capture | Not started | — |
| TBD | Independent Mario frame reconstruction | Not started | — |
