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

## 2026-11-09 — First actual SMB3 MesenCE frame capture, user-supplied ZIP

**Proven on real data:** The owner supplied a private 10-file capture archive for frames 29276 and 29277. The project `verify_capture.py` returned `pass_structural_capture_validation`, `capture_count=2`, and verified the independently supplied SMB3 US PRG1 ROM SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`. Mesen-reported ROM SHA-1 `6BD518E85EB46A4252AF07910F61036E84B020D1` matches the source NES bytes exactly. Each frame holds 256-byte OAM, 32-byte palette RAM, 8192-byte mapped PPU pattern snapshot, and 256×240×3 RGB bytes. Metadata: NTSC, 8×16 hardware sprite mode, endFrame scanline 240 cycle 0. Frame identifiers differ by 1 and master clock by 29,780.

**Captured-state comparison:** OAM, palette RAM, and the 8192-byte PPU pattern snapshots are byte-identical across these frames. The RGB screen buffers differ at only **3 pixels** (x=8–10, y=194). OAM entries #10 (x=114, Y=161, tile=7, attributes 0x40) and #11 (x=122, Y=161, tile=5, attributes 0x40) are the only two entries with an on-screen Y value; their combined 8×16 arrangement aligns with Mario as seen in the private capture. Do **not** infer complete character coverage or pixel-perfect sprite reconstruction from this alone.

**Critical finding:** In 8×16 mode, both odd tile IDs choose PPU pattern table 1 (`0x1000–0x1FFF`). The captured upper 4 KiB contains **0 nonzero bytes**, while the lower 4 KiB contains **3,735 nonzero bytes**. The tile data required to reproduce Mario is therefore *not present in the endFrame snapshot*, despite Mario appearing on screen. The debugger memory source or a different MMC3 mapper-bank state at endFrame versus the visible scanlines are working hypotheses; no cause has been proven.

**Research response:** `research/mesence/diagnose_capture.py` now reports these read-only pattern/OAM consistency checks without outputting copyrighted pixels. Next experiment: compare pattern tables at `startFrame` versus `endFrame`, then investigate scanline-sensitive CHR mapping if necessary. Do not mark sprite reconstruction complete until the actual visible-frame tile source is identified and replayable.

Archive SHA-256 (provenance only): `27e43e5dbf681ab402f27e6b61e7846b298a52ae43995277f428e01ff6879b88`. **No capture bytes or images were committed to GitHub.** MesenCE binary version not independently recorded in this archive.
