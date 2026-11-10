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

## 2026-11-10 — 8x16 hardware component reconstruction prototype

Following the real 3/3 frame-boundary SHA comparison, implemented research/mesence/sprite_components.py as a read-only OAM/PPU component decoder. It selects a full 8 KiB capture with independently validated physical MMC3 bank mapping, processes 8x16 tile-index table-selection bit, horizontal/vertical flip, palette-slot indices, behind-background attributes and index-0 transparency, and can emit tiny synthetic grayscale RGBA previews under local FIXTURE only. Absolute ROM offsets are computed from the verified eight PPU slot mappings.

The results represent **hardware OAM entries, not automatically characters, visible sprite pixels or faithful game RGB**. Hardware sprite evaluation, scanline timing, priority, partial clipping and original display color remain separate research gates. Unit tests use synthetic bytes, not copyrighted game assets. Next step is local owner validation of the actual 265172 startFrame component previews.

## 2026-11-10 — First real component previews identify SMB3 pause-message sprites

**Private evidence:** Owner supplied metadata-only `component_report.json` and five locally exported 8x16 synthetic grayscale RGBA previews `hardware_oam_00..04_frame_265172.png`. They were derived from verified frame 265172 `startFrame` sample #3 (phase session `phase_0000265171_1794292304`) using the independently confirmed 8KiB physical CHR bank mapping.

**Observed visual result:** The five individual previews read **P A U S E** in OAM order (0–4). All five entries have Y=89, X positions 96, 112, 128, 144 and 160; tile IDs 241, 245, 249, 253, 255; palette slot 3; attribute byte 3; 8x16 height; and no flipping or behind-background bit. They point to PPU upper table addresses 7936, 8000, 8064, 8128, 8160 (upper tiles), with exact physical ROM offsets preserved per tile. Source palette RAM bytes for palette indices 1–3 are [15,54,39]. The report includes SHA-256 checksums of all five PNG files and matching capture source hashes; no bytes or artwork should be committed.

**Conclusion:** SpriteMine's 8x16 pattern/tile interpretation produces recognizable SMB3 **pause-message hardware sprite components** from actual emulator data. This is strong evidence the game was in its *in-game pause state* at the time of capture, not a gameplay frame containing Mario. It is NOT a validated composite Mario character, nor independently confirmed as the actual visible final rendered pixels.

**Next:** Resume the **game's own** pause state using the configured gamepad Start button (distinct from MesenCE emulator pause), verify Mario is visible and gameplay is advancing, then run `spritemine_phase_capture.lua` again to record a **new session**. Validate the new session against the source ROM and inspect sample #3 without assuming a character identity. Retain prior evidence unmodified in FIXTURE; do not repeat fixed session paths for new captures.

## 2026-11-10 — Gameplay Mario candidate reconstructed from two OAM components

**Private fixture:** `phase_0000442741_1794295259.json` and companion ZIP containing all twelve actual OAM/palette/PPU binary buffers. Verified SMB3 PRG1 ROM SHA-256 identity; timestamped pre-write MMC3 trace has 114 writes and no dropped events. The independently built source-ROM-backed PPU pattern images match all three modeled frame-boundary 8KiB buffers **byte for byte**, including the second startFrame (frame 442742) with source banks `[8,9,96,97,83,4,34,79]`. The fourth snapshot matches the endFrame blank-bank state as in earlier captures.

**OAM evidence:** Two candidate visible entries: OAM #10 at (87,162), tile 7, attr 0x40; OAM #11 at (95,162), tile 5, attr 0x40. Both 8x16, palette slot 0; all other OAM entries have off-screen Y. Source bank 83 maps the relevant upper PPU tile addresses, and authenticated ROM offsets are recorded in `docs/research/SMB3_FIRST_MARIO_COMPONENTS.md`. The captured palette RAM slot 0 contains 0x16,0x36,0x0F for nontransparent indices.

**Independent assembly:** Decode two tiles per component, flip horizontally and preserve pixel-index-0 transparency. Placed side by side at their actual OAM positions, they yield an unmistakable *small Mario-shaped* 16x16 candidate, with 138 nontransparent pixels. The CHR mapper write stream shows no CHR bank register changes before scanline 193, later than the sprite's rows 162–177; this makes pre-render CHR mapping a credible source for that object in this frame, although actual PPU fetches have not been traced.

**Follow-up implementation:** Added explicit hardware OAM group composer with diagnostic grayscale RGBA output; it never automatically infers actor identity and retains original component provenance. The complete user fixture remains private. Full-screen pixel, RGB palette, priority and save-state replay verification remain incomplete.


## 2026-11-10 — Screen RGB synchronization experiment prepared

Source-level observation: MesenCE NES PPU SendFrame() triggers EndFrame before dispatching the completed current output buffer; Lua GetRenderedFrame() passes current PPU frame data through the video filter and getScreenBuffer() exposes RGB values. References: Core/NES/NesPpu.cpp and Core/Debugger/LuaApi.cpp at revision 4b8a196e299b3de297b204fd1208d2981562c89b.

Implemented a distinct render_... local capture producing two 24-bit RGB screen buffers and the existing four phase-boundary OAM/PPU/palette snapshots, with bounded MMC3 writes. The read-only verify_phase_capture.py now supports versioned rendered capture manifests while retaining original phase-only semantics. analyze_render_capture.py compares indexed pixels from explicit candidate hardware OAM entries against observed screen pixel RGB at the recorded coordinates, separately for each sprite palette slot and 2bpp pixel index. It reports modal color consistency and ±1-pixel controls, does not adjust alignment, and flags possible bank changes before the hardware sprite's lower scanline.

Caution: RGB modes inferred from that same rendered image are not independent NES palette calibration and high consistency alone does not establish pixel-perfect OAM visibility. Filter resampling, background priority, sprite evaluation/limits and exact fetch phase remain uncertain. Synthetic mocks/CI can check the pipeline, but the actual owner-run MesenCE experiment has not occurred yet. Runbook: docs/research/RENDER_RGB_CORRESPONDENCE.md.


## 2026-11-10 — First real RGB screen correspondence: 138 opaque color-consistent pixels

From owner-supplied render_0000450823_1794339466.json and metadata-only screencheck_render_0000450823_1794339466.json: frame 450824, source SMB3 PRG1 ROM verified, independent 8KiB MMC3 CHR boundary mapping passed, 256x240 RGB framebuffer, OAM/palette state unchanged across start/end, no early CHR bank register writes. Two explicit 8x16 OAM entries at (128,162) and (136,162) provide 138 opaque palette-index pixels in a 16x16 region.

**Measured modal-color consistency:** 138/138 (100%) at exact OAM positions, versus 81/138 at left or right 1px, 56/138 at up 1px and 55/138 at down 1px. By pixel index: #B53120 37/37, #FECCC5 31/31 and #000000 70/70. The color classes were estimated from the same rendered pixels, so this was **not yet an independent palette-color comparison**.

**Independent source research:** MesenCE Core/NES/NesDefaultVideoFilter.cpp, revision 4b8a196e299b3de297b204fd1208d2981562c89b, confirms default 2C02 colors 0x16→#B53120, 0x36→#FECCC5, 0x0F→#000000. Exact source/color agreement is supported; same-session palette RAM code values must now be checked directly. MesenCE user palettes and color adjustments remain plausible for other captures.

Added a strict three-code MesenCE default reference and a separate non-fitted per-pixel check to analyze_render_capture.py, plus optional reference-colored indexed OAM PNGs with real index-0 alpha under local FIXTURE. Unknown palette codes are unsupported, never fabricated. The local reanalysis of actual captured binary files remains **pending**. Also, the 118 source-transparent pixels cannot be independently verified as background without a background-only capture or full background reconstruction. See docs/research/SMB3_MARIO_INDEPENDENT_PALETTE.md.

## 2026-11-10 — PASS: independent 138/138 small Mario default palette RGB

Evidence: owner-provided local `screencheck_independent_render_0000450823_1794339466.json` and six individual/group PNG previews. Frame **450824** MesenCE RGB, 256x240. The report uses real captured palette RAM, fixed upstream MesenCE default 2C02 source RGB, captured OAM/CHR and source ROM mapping. **138 expected, 138 compared, 138 exact, 0 mismatched**. Palette code 0x16 -> #B53120 (37 pixels), 0x36 -> #FECCC5 (31), 0x0F -> #000000 (70). Full 16x16 colored PNG has 138 fully opaque pixels and 118 fully transparent pixels, exactly matching grayscale's transparency mask; two 8x16 component alpha counts sum to 138.

Proven: a **single 16x16 candidate Mario pose's 138 opaque source-sprite pixels** correspond exactly to the rendered MesenCE frame under the independently documented default 2C02 palette reference; source ROM and captured PPU mappings verified. Not proven: the 118 background pixels behind transparent sprite indices, alternate display filters, background/sprite overlap priority and other frames/poses. Full independently reproducible evidence/hashes in `docs/research/SMB3_MARIO_OPAQUE_RGB_VERIFIED.md`. No copyrighted PNG or raw ROM contents placed in GitHub.


## 2026-11-10 — NES sprite-display toggle source-confirmed; controlled background replay designed

Source review: nesdev-org/MesenCE at commit 4b8a196e299b3de297b204fd1208d2981562c89b. UI/Views/NesConfigView.axaml exposes NES Video/Miscellaneous Disable Sprites; UI/Config/NesConfig.cs inverts it into NES SpritesEnabled. Core/NES/BaseNesPpu.cpp maps that into _emulatorSpritesEnabled; Core/NES/NesPpu.cpp GetPixelColor() checks the display flag before returning a sprite color, while sprite shift processing and sprite-zero-hit handling are separate. This appears suitable for background-only rendering without mutating ROMs or changing $2001 hardware mask, subject to real emulator verification.

Implemented research/mesence/verify_background_composite.py: two-session verifier for exactly replayed sprite-visible vs sprite-hidden frames. Verifies ROM/PPU/OAM/palette SHA, same second frame/clock/scanline/cycle, 256x240 unfiltered RGB, fixed NES RGB opaque pixels, all 118 source-transparent positions and an 8px scene-control ring. Must see at least one opaque pixel disappear in the reference. Cannot independently read GUI setting from current capture, so even success is labeled conditional on user-provided sprites-disabled reference. Tested synthetic exact matches, changed transparent pixels, mismatched opaque colors, displaced scene ring, identical ambiguous renders and misaligned frame IDs; cross-platform CI pass. No real sprites-disabled image yet.

See docs/research/SMB3_BACKGROUND_COMPOSITE_EXPERIMENT.md; save-state replay and observed source background remain next critical gates.

## 2026-11-10 — Slot 1, controller latch and full-region RGB

Neutral, walking and rising jump samples passed the real MesenCE A/B/A experiment. An earlier inputPolled-only trial failed the movement gate despite successful pad readback. Reassertion at controller strobe was verified from CPU-bus reads. [Runbook and proof limits](research/SMB3_GRAPHICS_HARNESS.md).


## 2026-11-10 — Animation timeline over overlapping verified slot-1 A/B/A windows

**Hypothesis:** Consecutive emulator video frames can be reconstructed, provenance-matched and exported using a series of independent already-verified A/B/A captures taken from the *same* original MesenCE slot-1 save state but incrementing the existing warmup by exactly one frame. Only each run's **second** startFrame is independently mapped from same-session MMC3 writes; first-frame mapping is unknown until writes are observed. This avoids extrapolating initial CHR mapping and avoids inventing sprite pixels.

**Implementation (research/smb3-animation-timeline):** graphics_report.validate now supports write_visuals=False for full-source revalidation without modifying the original run. animation_timeline.py requires matching saved state, ROM, emulator version/hash, probe hash, controller plan, restore timestamp, consecutively observed frame identifiers, increasing PPU clocks and passed A/B/A opaque/background gates. It emits alpha-preserving 16x16 PNGs, a private spritesheet and per-frame raw SHA/ROM offset/tile/clock provenance. Matching images remain separate one-emulator-frame entries. animation_windows.py drives the proven A/B/A harness with 2–12 consecutive warmups and refuses changing slot-1 source bytes or partial failed runs.

**Not proven:** accurate playback milliseconds, completed walking/jump cycles or native standalone animations. A first **three-frame right-input experiment** is needed on Windows before marking this timeline gate passed. Tests are synthetic; runbook docs/research/SMB3_ANIMATION_TIMELINE.md. Source ROMs, captures, states and exported images remain private under FIXTURE.
