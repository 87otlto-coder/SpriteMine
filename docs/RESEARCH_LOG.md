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

## 2026-11-09 — On-device startFrame/endFrame mapping comparison (confirmed)

**Source evidence:** owner-supplied private metadata-only `mapping_probe_0000136117_1794255614.json` from MesenCE Lua script `spritemine-mapping-phase-v1`, ROM SHA-1 `6BD518E85EB46A4252AF07910F61036E84B020D1` (matches the prior verified SMB3 US PRG1 capture identity). Do not commit the private fixture itself.

**Frame 136117:** `startFrame` at PPU scanline -1 / cycle 0: upper 4 KiB has **2,991** nonzero bytes; lower has **3,211**. Five potentially on-screen OAM entries, all with odd 8×16 tile IDs, have **zero blank referenced patterns**. `endFrame` at scanline 240 / cycle 0: upper 4 KiB has **0** nonzero bytes; lower has **3,735**; all five referenced odd-tile patterns appear blank.

**Frame 136118:** precisely repeats 2,991→0 upper, 3,211→3,735 lower, and 0→5 blank odd-tile patterns. The recorded event identifiers and master clocks differ across phases. Structural self-consistency is high, although MesenCE binary/version and saved-state replay have not been recorded for this experiment.

**Proven:** the debug-visible effective PPU pattern space differs dramatically between the pre-render (startFrame) and VBlank (endFrame) observation points in this running SMB3 scene. End-of-frame pattern snapshots do not represent the pattern bytes for all potentially visible OAM sprites throughout a frame.

**Hypothesis (not yet proven):** SMB3 is changing MMC3 bank registers during frame rendering / VBlank. The source of the change (mapper writes versus a debugging effect) and exact rendering-time CHR mapping are still unknown. We must trace mapper register writes and/or record rendering-scanline PPU fetches before asserting bank identities or validated character reconstruction. Simply switching all exports to `startFrame` would be premature.

**Next:** add a bounded, non-mutating mapper register write trace with PPU scanline/cycle/frame timestamps, and validate it on real MesenCE while retaining only metadata in the repository.

## 2026-11-09 — Independent byte-for-byte CHR mapping reconciliation

**Private evidence analyzed locally, never committed:** verified SMB3 US PRG1 ROM SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`; earlier `frame_0000029277_ppu_pattern.bin` capture, and MMC3 register trace `mmc3_trace_0000189263_1794256680.json`. The second upload with suffix `(1)` has exactly the same bytes (SHA-256 `ddc586b0ed660bcc1e6302c630dc27138a8962b45708315be384bd8fd410f6d0`); it is not another experiment.

**Exact physical CHR-ROM comparison:** the 8 consecutive 1-KiB captured PPU windows uniquely match physical banks **[92, 93, 94, 95, 126, 126, 126, 126]**, every byte in every window. Bank 126 is a real all-zero 1-KiB CHR-ROM bank, not a missing read. The first 4 windows have 988, 811, 946, 990 nonzero bytes (total 3,735); the last 4 have none.

**Register trace (62 writes, 0 dropped):** around PPU scanline 193 of frames 189263 and 189264, $8000 selects registers R0..R5 and $8001 writes R0=92, R1=94, R2=R3=R4=R5=126. In MMC3 CHR mode 0, the 8 PPU windows thus become exactly [92, 93, 94, 95, 126, 126, 126, 126]. MesenCE source `Core/NES/Mappers/Nintendo/MMC3.h` confirms that **bit 7** of $8000 controls CHR inversion; bit 6 controls *PRG*, not CHR, mode. Trace bank-select values 0x40..0x47 have CHR bit 7 clear. Both modeled scanline-193 layouts match all eight observed capture windows exactly. The CPU write callbacks occur **before** the actual write, so these are modeled post-write register layouts, independently cross-checked against an observed snapshot from a **different session/frame**.

**Other recurring register configuration:** VBlank writes at scanlines 246–247 produce modeled PPU windows [8, 9, 102, 103, 83, 4, 34, 50]. Their actual physical 1-KiB CHR-ROM nonzero counts total **3,211 lower + 2,991 upper**, exactly matching the two real startFrame phase-probe readings. This independently corroborates the predicted mapping without asserting that those observations are from the same emulation instant.

**Technical conclusion:** a repeatable bank-switching sequence explains both the blank endFrame sprite patterns and the populated pre-render patterns. The original Lua recorder did not fail; it sampled a valid but inappropriate time for character reconstruction. **Still unresolved:** exact PPU fetch mapping on Mario's visible scanlines; sprite transparency/priority and pixel compositing; synchronized frame-specific physical bank attribution; reproducibility from saved state and input. Do not claim pixel-perfect Mario exports yet.

**Tooling:** `research/mesence/correlate_chr_banks.py` performs this ROM/PPU/trace comparison locally and emits metadata only. Unit tests use synthetic banks, including ambiguity handling and the MMC3 inversion bit. MesenCE source reference: https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/NES/Mappers/Nintendo/MMC3.h

## 2026-11-09 — Complete 8 KiB PPU SHA verification

A read-only bank decoder rebuilt the entire endFrame 8,192-byte PPU pattern from source ROM and traced MMC3 R0–R5 values. SHA-256 `0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918` matches both private frame 29276 and 29277 PPU snapshots byte for byte. At the second observed startFrame, predicted PPU SHA-256 is `ff1fed9ebea0ff45c17ae1ddb93bf3205ee591438cc8d45af83167a80d4f69b5`, still lacking full raw startFrame confirmation. See [MMC3 mapping verification](research/MMC3_CHR_MAPPING_VERIFICATION.md). This confirms boundary physical bank content, not render-time sprite visibility.

## 2026-11-10 — Full start/end PPU capture experiment prepared

**Question:** Can the ROM-backed MMC3 model predict a later startFrame 8 KiB PPU pattern *byte for byte* from bank writes observed in the **same** MesenCE session?

**Implemented, pending on-device validation:** spritemine_phase_capture.lua captures two complete startFrame/endFrame pairs, each with a PPU 8 KiB buffer, 256-byte OAM and 32-byte palette RAM, plus timing, source identity and bounded pre-write bank-register history. Files use a distinct session prefix and refuse overwrites. verify_phase_capture.py validates filenames, sizes, frames, SHA-256, source ROM identity and the predicted mapper slots/hashes when a verified SMB3 ROM is provided.

**Acceptance:** Confirm full second startFrame PPU SHA-256 matches its ROM-based model from writes observed between first endFrame and second startFrame. The first pre-render mapping may be legitimately unknown until all six bank registers have been observed. Full matching endFrame SHA-256 is a secondary check.

**Unproven:** physical graphics bytes fetched on each visible scanline, actual sprite visibility, save-state replay and pixel-perfect Mario rendering. Captures remain under FIXTURE.

## 2026-11-10 — Same-session MMC3 trace prediction, awaiting actual PPU bytes

**Evidence:** Private owner-uploaded `phase_0000265171_1794292304.json`, from `spritemine-mesence-phase-capture-v1`, contains four PPU boundary event records (start/end at frame 265171, start/end at frame 265172), 62 timestamped $8000/$8001 writes and zero dropped writes. The MesenCE-reported source SHA-1 `6BD518E85EB46A4252AF07910F61036E84B020D1` matches the verified SMB3 ROM. All four boundary clocks progress monotonically.

Using the recorded writes *and the owner's previously verified SMB3 ROM*:
- First startFrame: physical mapper state unknown; no writes before the observation.
- First endFrame: PPU slots `[92,93,94,95,126,126,126,126]`, expected SHA-256 `0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918`.
- Second startFrame: PPU slots `[8,9,102,103,83,4,34,50]`, expected SHA-256 `ff1fed9ebea0ff45c17ae1ddb93bf3205ee591438cc8d45af83167a80d4f69b5`.
- Second endFrame: same PPU slots and expected SHA-256 as first endFrame.

**Crucial evidence boundary:** This upload supplied **only the JSON manifest**, not the four raw 8,192-byte PPU snapshots or eight OAM/palette buffers. These expected checksums are ROM-backed model predictions, **not yet compared to same-session captured bytes**. Await the local validator report before clearing the full PPU byte-match gate. Actual Mario screen pixel identity, per-scanline rendering, and deterministic replay remain separate unresolved goals.

## 2026-11-10 — Phase-capture validator confirms exact same-session 8 KiB patterns

User supplied the **locally generated** metadata-only `phase_verification.json` from session `phase_0000265171_1794292304`. It verifies verified PRG1 whole-ROM SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`, four snapshot events in frames 265171/265172, 12 binary blobs and 62 timed MMC3 writes with zero drops.

**PASS:** `model_matches=3`, `model_mismatches=0`, `model_unknown_snapshots=1`; `mapper_model_status=matches_known_boundaries`. The *second* startFrame observed 8,192-byte PPU SHA-256 `ff1fed9ebea0ff45c17ae1ddb93bf3205ee591438cc8d45af83167a80d4f69b5` matches the ROM-based model from same-session prior writes. Both endFrame captured PPU SHA-256 values also match the ROM model: `0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918`.

**Unknown, not a failed test:** first startFrame's previous MMC3 state cannot be proven from an already-started trace. Its captured SHA-256 is equal to the second startFrame but that equality is not evidence of an independently observed initial mapping.

**Now confirmed:** physical CHR mapping at these sampled frame boundaries. **Not confirmed:** PPU fetches over the whole visible frame, hardware OAM component grouping into a character, proper sprite priority/clipping, authentic rendered colors, saved-state/input replay. Treat next sprite work as a separate evidence/acceptance gate. Captured binaries remain exclusively in local FIXTURE.
