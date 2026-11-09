# Research log

Record date, question, source/experiment, observation, confidence and next action. Link each major result to the exact code commit, emulator version and (where possible) test fixture.

## 2026-11-08 — Source ROM identity

Observation: the supplied SMB3 ZIP contains one valid iNES file with mapper 4, 256 KiB PRG-ROM, 128 KiB CHR-ROM and matching PRG1 hash/CRC values. Verified locally against bytes, not inferred solely from filename. Confidence: high for this supplied file.

## 2026-11-08 — Static CHR

Observation: all 16 CHR-ROM banks can be decoded to 8×8 2bpp tiles (8,192 total), exported in grayscale. No game-accurate palette identification. Confidence: high for raw 2bpp interpretation; asset identity unresolved.

## 2026-11-08 — MesenCE integration candidate

Source code contains debugger-oriented tilemap/sprite/palette access and emulator state save/load capabilities. Open question: how to expose a synchronized, reproducible capture API, with an acceptable GPLv3-compatible distribution approach. **Not yet experimentally validated.** See research branch `research/smb3-emulator-feasibility`.

## Source references

- https://www.nesdev.org/wiki/PPU_programmer_reference
- https://github.com/nesdev-org/MesenCE
- https://github.com/TASEmulators/fceux
- https://github.com/captainsouthbird/smb3 (research reference; licensing review needed before reuse)

## 2026-11-09 — Lua capture feasibility spike

Source-verified capabilities at pinned MesenCE commit `4b8a196e299b3de297b204fd1208d2981562c89b`: Lua endFrame callback, NES OAM/palette memory types, side-effect-disabled PPU address-space reads, getScreenBuffer/getScreenSize, getState/getRomInfo, and per-script data folder. Confirmed from `LuaApi.cpp`, `ScriptingContext.cpp`, and bundled Lua example. File/OS access is opt-in in MesenCE. Original Lua recorder plus Python validator committed on research branch; GitHub Lua syntax + Python synthetic tests passed. These are not runtime observations; **Windows emulator execution is pending**. See `research/mesence/README.md`.

## 2026-11-09 — Mocked Lua recorder execution

Created `research/mesence/mock_mesence.lua` and updated research CI to invoke the actual recorder with synthetic, non-copyrighted OAM/palette/PPU/screen bytes. The emitted two frame captures passed `verify_capture.py`, and 7 Python validator tests passed. GitHub Actions run 42585418488 succeeded. This verifies script file output and metadata format under the mock only; MesenCE runtime sync, mapped CHR identity, save-state replay and visual correctness remain untested.
