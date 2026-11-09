# SpriteMine — reproducible MesenCE Lua capture spike

This is an **unvalidated research experiment**, not a production emulator adapter. The Lua script uses real MesenCE API functions identified from the upstream source at commit `4b8a196e299b3de297b204fd1208d2981562c89b`, but has **not yet been run against SMB3 in Windows MesenCE**. It does not decode semantic characters or map PPU addresses to physical ROM banks.

## Why Lua first?

MesenCE already has a debugger scripting API: `emu.addEventCallback(..., emu.eventType.endFrame)`, `emu.read(..., emu.memType.nesSpriteRam)`, `nesPaletteRam`, `nesPpuDebug`, `emu.getScreenSize`, `emu.getScreenBuffer`, `emu.getState`, `emu.getRomInfo` and `emu.getScriptDataFolder`. It may let us verify a real capture without embedding a GPL-licensed emulator or guessing C++ interop struct layouts.

Important: **MesenCE disables Lua file I/O by default unless script I/O/OS access is enabled in its debugger settings.** The probe checks this and reports a clear error if disabled. Allow file I/O only for scripts you trust; it grants filesystem access. No network permissions are required.

## Windows steps

Use your existing `$HOME\SpriteMine` clone without changing its current working branch:

```powershell
Set-Location -Path "$HOME\SpriteMine"
git fetch origin
git worktree add "$HOME\SpriteMine-research" research/smb3-emulator-feasibility
Set-Location -Path "$HOME\SpriteMine-research"
git rev-parse --short HEAD
```

If the research worktree already exists, skip `git worktree add` and run `git pull --ff-only origin research/smb3-emulator-feasibility` from inside it.

Expected: a separate folder `$HOME\SpriteMine-research` containing `research\mesence\spritemine_frame_probe.lua`.

1. Open MesenCE and load the **locally owned SMB3 US PRG1 / Revision A** game.
2. Navigate to the game's level or scene you want to inspect.
3. Open MesenCE's Lua script window (from its debugger tools), enable **script file I/O / OS access** in the debugger's script permissions, and load `$HOME\SpriteMine-research\research\mesence\spritemine_frame_probe.lua`.
4. Run the script with emulation advancing. It records the next **two endFrame callbacks**. The script log prints the output folder; by design this is an automatically created per-script directory under MesenCE's `LuaScriptData` folder.
5. **Do not upload captures or extracted game images to GitHub.** The source code and validator are sufficient for collaboration; share validation summaries or error logs separately.

To validate, replace the path below with the **actual folder printed by the MesenCE script log** and point `--rom` to your local ROM ZIP:

```powershell
Set-Location -Path "$HOME\SpriteMine-research"
py -3.12 ".\research\mesence\verify_capture.py" "C:\PATH\FROM\MESENCE\LuaScriptData\spritemine_frame_probe" --rom "C:\PATH\TO\Super Mario Bros. 3.zip"
```

Expected if capture succeeds: a JSON report with `result: pass_structural_capture_validation`, `capture_count: 2`, `verified_smb3_rom_provided: true`, and SHA-256 hashes for each binary buffer. The validator outputs **only metadata and checksums**, never game art or screen pixels. A structural pass does **not** prove exact screen-frame synchronization or correct physical CHR mapping.

## Raw file contract

Each frame produces a `frame_XXXXXXXXXX.json` file and four binary streams:

| File suffix | Contents | Expected size |
|---|---|---|
| `_oam.bin` | 64 OAM entries × 4 bytes | 256 |
| `_palette.bin` | Raw NES palette RAM | 32 |
| `_ppu_pattern.bin` | Effective PPU pattern bytes 0x0000–0x1FFF (unmapped source provenance) | 8,192 |
| `_screen_rgb.bin` | Video-filtered RGB24, row-major | 3 × width × height |

Metadata stores frame count, master clock, event type, region, Mesen-reported ROM SHA-1, sprite size, optional PPU scanline/cycle values, and file names. The framebuffer may be from a different emulated phase; the program **does not** claim atomic capture.

## Key gates

- Verify the script is executable in MesenCE and records structurally valid data without crashes.
- Repeat from a saved state with the same inputs, and compare generated hashes.
- Determine whether endFrame reads and `getScreenBuffer` are synchronized to the same frame.
- Resolve physical MMC3 CHR bank mapping before claiming ROM offsets for captured tiles.
- Check background priority, scanline sprite limits and actual visible pixels in the next experiment.

## Upstream source references

- [MesenCE Lua API](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/Debugger/LuaApi.cpp)
- [Lua script I/O permissions](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/Debugger/ScriptingContext.cpp)
- [Bundled script example](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/UI/Debugger/Utilities/LuaScripts/Example.lua)
