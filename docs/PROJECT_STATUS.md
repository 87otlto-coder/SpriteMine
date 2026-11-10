# Project status

**Current work — 2026-11-10:** The research branch now contains a paired start/end frame recorder (spritemine_phase_capture.lua) and read-only same-session MMC3 validator (verify_phase_capture.py). It records four full 8 KiB PPU boundary snapshots with OAM, palette and intervening bank writes, and compares captured hashes with ROM-derived bank mapping when supplied the verified ROM. Synthetic tests and a full mock execution are in CI. **Real MesenCE execution of this new recorder remains pending.** See research/mesence/README.md.

**Latest research snapshot — 2026-11-09:** Phase 0 foundation merged to main. Phase 2 static explorer is in PR #4 with real Windows launch/import/atlas/tile inspection observed; remaining export and edge-case checks pending. Phase 1 MesenCE can now capture actual SMB3 state, and independent MMC3 register traces can reconstruct **all 8 physical CHR-ROM bank mappings at sampled frame boundaries**. The predicted endFrame 8192-byte PPU image matches two private capture snapshots byte for byte, verified by SHA-256. Exact render-time Mario sprite reconstruction, save-state replay and full coverage remain unproven. See [MMC3 CHR mapping verification](research/MMC3_CHR_MAPPING_VERIFICATION.md).

**Research tools:** correlate_chr_banks.py matches captured PPU windows to physical ROM banks; decode_mmc3_trace.py models complete bank mappings at frame boundaries from timestamped writes, computes source offsets/PPU SHA-256 and can compare a private capture ZIP. Both are read-only and output metadata only. Synthetic tests cover odd 2 KiB bank alignment.

---

Updated: 2026-11-08. Source of truth: GitHub code and checks; this snapshot is refreshed with major work.

## Active milestone

**SMB3 PRG1 Phase 0 — foundation.** Feature branch `feature/foundation-rom-chr` contains the initial implementation. Merge requires PR review and any pending CI verification.

## Implemented in foundation branch

- Legacy iNES ROM/ZIP read-only parser; checksums, mapper, bank boundaries, trainer offsets and explicit errors.
- CHR-ROM 2bpp tile decoder and synthetic grayscale tile/bank PNG exporter with deterministic manifest.
- Automated synthetic parsing, bitplane, ZIP safety, provenance and CLI tests.
- GitHub Actions matrix for Windows and Ubuntu, Python 3.11/3.12; workflow status pending GitHub execution.
- Project governance and engineering docs.

## Validated locally on 2026-11-08

- 12 synthetic Python unit tests passed; the optional SMB3 integration test passes when supplied with the ROM (13 total).
- User-provided SMB3 ZIP: iNES, mapper 4, PRG 256 KiB, CHR 128 KiB, whole-ROM SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`.
- PRG/CHR CRC32 `A0ED7D20`/`C2928C49`; combined CRC32 `2E6301ED`.
- 16 exported 8 KiB CHR bank PNGs represent 8,192 tiles. Grayscale values are synthetic.

## Not yet implemented / verified

- No PySide6 interface or user-facing installer.
- No MesenCE integration, OAM/palette capture, animations, decoded levels or audio.
- No emulator state synchronization experiment or tested native Windows desktop UI.
- Coverage beyond raw CHR tile count has not been assessed.
- GitHub CI and native Windows validation are separate gates and must not be assumed passed.

## Next steps

1. Review and merge the foundation PR after checks.
2. Use the `research/smb3-emulator-feasibility` branch to prove synchronized capture of OAM, palettes, CHR mapping and rendered pixels at known frame boundaries.
3. Only then settle the emulator adapter boundary and start the static PySide6 explorer.

## 2026-11-09 — MesenCE Lua research probe (research branch only)

- Added `research/mesence/spritemine_frame_probe.lua`, a two-frame NES endFrame capture experiment for OAM (256 B), palette RAM (32 B), PPU pattern read space (8,192 B), and video-filtered RGB screen.
- Added `research/mesence/verify_capture.py` with strict filename, dimension, size and frame-identity validation, plus optional SMB3 PRG1 ROM SHA-256 confirmation. Never emits or commits captured pixel data.
- Lua syntax checking with stock Lua 5.4 and all synthetic validator tests passed on GitHub Actions; normal Python matrix passed too.
- **Still unverified:** any real MesenCE file export, exact memory mapping, screen-buffer/frame alignment, input replay, MMC3 bank provenance, and semantic Mario reconstruction. Lua I/O needs explicit user permission.
- Runtime instructions: `research/mesence/README.md`. This branch is experimental; do not merge into `main` as finished integration.

### Mocked Lua capture execution — verified 2026-11-09

GitHub Actions [run 42585418488](https://github.com/87otlto-coder/SpriteMine/actions/runs/42585418488) successfully executed the original Lua probe against a synthetic stand-in for MesenCE's Lua `emu` API, emitted two complete frame capture sets (100 and 101), and structurally validated the binary payloads and manifests. Seven independent Python validator tests also passed. The normal cross-platform tests passed separately. **This is software/mock validation, not an actual emulator observation.** The next required evidence is an on-device MesenCE capture and playback/snapshot comparison.

## Local environment alignment — 2026-11-09

The owner confirmed `F:\Dev\ROMMAGE\SOURCE\SpriteMine` was refreshed successfully, and `F:\Dev\ROMMAGE\TOOLS\SpriteMine-research` already holds the up-to-date research branch. MesenCE is installed in `TOOLS`. The Lua probe now defaults to `F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE` for local capture output (the folder must exist). CI uses `SPRITEMINE_CAPTURE_DIR` to override the path. No real emulator captures have been verified yet. See `research/mesence/README.md`.

## 2026-11-09 — Real SMB3 capture received and structurally verified

The owner provided a MesenCE capture ZIP with **two real SMB3 PRG1 frames** (29276–29277, 10 files). The Python structural validator passed and ROM SHA-1/SHA-256 identities match the locally supplied verified ROM. This completes the first *real capture creation and file-integrity* gate, **not** the synchronization or sprite-reconstruction gate.

Important: OAM shows two potentially on-screen 8×16 entries corresponding spatially to Mario; their odd tile IDs select PPU `0x1000–0x1FFF` in 8×16 mode. The captured upper pattern table contains only zero bytes. The endFrame snapshot **cannot reconstruct these visible Mario tiles**. Hypotheses: a different MMC3 CHR bank mapping at the rendering scanline, or unexpected debug read behavior. Neither is confirmed. Screen buffers change by 3 pixels while OAM/palette/pattern snapshots remain identical. The next task is a time-separated PPU mapping experiment. See `docs/RESEARCH_LOG.md`.

Only metadata findings are stored in GitHub. All game asset bytes remain out of the repository.

## 2026-11-09 — Mapping phase dependence verified on device

The owner supplied metadata-only MesenCE `spritemine-mapping-phase-v1` output for frames **136117–136118**, ROM SHA-1 matching previously verified SMB3 PRG1. At **startFrame** (PPU scanline -1), upper PPU 4 KiB contains **2,991 nonzero bytes**; at **endFrame** (scanline 240) the same range has **0**. Lower 4 KiB goes **3,211→3,735**. All 5 potential on-screen odd-tile 8×16 OAM entries change from **0 blank referenced patterns** to **5 blank**. Both frames reproduce these counts. This confirms phase-sensitive effective PPU pattern content, **not** exact MMC3 register writes, scanline-specific mapping, or sprite pixel reconstruction.

The next blocker is identifying rendering-time physical CHR bank provenance. See `docs/RESEARCH_LOG.md`; do not mark live Sprite Inspector complete. 

## 2026-11-09 — Next instrumentation implemented

Research branch contains `research/mesence/spritemine_mmc3_trace.lua`, a bounded, metadata-only trace of CPU writes to MMC3 $8000–$9FFF during two sampled frame intervals. It records PPU scanline/cycle, frame/clock, write address/value and the bank-select versus bank-data classification. The callback observes **pre-write** state; it cannot itself establish mapped CHR data after each write. The synthetic Lua mock and generated JSON checks passed GitHub research CI (run 42692943952); cross-platform Python checks also passed (run 42692943950). **Real MesenCE execution remains pending.** Run instructions are in `research/mesence/README.md`. Preserve all ROMs and rendered graphics exclusively in FIXTURE.

## 2026-11-09 — Physical CHR-ROM bank identity verified for captured mapping

Independent private-ROM byte comparison identified all 8 earlier endFrame PPU windows exactly as physical 1-KiB CHR banks `[92,93,94,95,126,126,126,126]`. Bank 126 is genuinely blank. The real MMC3 register trace from a separate gameplay interval repeatedly writes that same configuration at scanline 193 (R0=92, R1=94, R2..R5=126). VBlank register values predict `[8,9,102,103,83,4,34,50]` whose nonzero counts exactly agree with the independently captured pre-render mapping phase. This is a high-confidence **cross-session configuration explanation**, not a verified same-scanline Mario sprite reconstruction.

Implemented reproducible metadata-only correlation tool `research/mesence/correlate_chr_banks.py` with synthetic regression tests. Further evidence needed: same-session rendering-scanline capture and independent visible-sprite pixel reconstruction. See `docs/RESEARCH_LOG.md`.

## 2026-11-10 — Actual paired-phase MesenCE metadata received; binary verification pending

Owner supplied private `phase_0000265171_1794292304.json` for frames 265171 and 265172. Manifest has the four expected startFrame/endFrame observations, 62 MMC3 register writes and zero drops. Mesen-reported source SHA-1 matches independently verified SMB3 US PRG1. The event clock sequence is coherent, and physical CHR mappings can be modeled at 3 of the 4 boundary events from this **same session**.

With the verified ROM and register-write model, the *predicted* second startFrame bank sequence is `[8,9,102,103,83,4,34,50]`, full 8 KiB SHA-256 `ff1fed9ebea0ff45c17ae1ddb93bf3205ee591438cc8d45af83167a80d4f69b5`. Both endFrame configurations model `[92,93,94,95,126,126,126,126]`, full 8 KiB SHA-256 `0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918`. The first startFrame state is not reconstructable because its earlier writes were not observed.

**Unresolved:** The owner uploaded the JSON manifest only; none of its 12 referenced binary snapshots were available in this review. Therefore do **not** label any *same-session full 8 KiB* capture hash as verified. Next run `research/mesence/verify_phase_capture.py` locally against the exact 13-file session and verified ROM, and share only its JSON metadata report. No ROM, raw captured binaries or visuals were committed.

## 2026-11-10 — Same-session full PPU hash gate PASSED

Owner ran `research/mesence/verify_phase_capture.py` locally with the verified SMB3 PRG1 ROM and uploaded its metadata-only report for session `phase_0000265171_1794292304` (frames 265171/265172). **Result: `pass_structural_phase_capture_validation`, `mapper_model_status=matches_known_boundaries`, `model_matches=3`, `model_mismatches=0`, `model_unknown_snapshots=1`, `dropped_writes=0`.** All 12 binary blobs were structurally checked locally. The known startFrame for frame 265172 and both endFrame observations matched the *entire* modeled 8,192-byte PPU pattern SHA-256. The first startFrame mapping is legitimately unknown because its register writes predate the trace; its observed hash happens to equal the other startFrame hash but is **not** independently reconstructed from same-session register history.

**Gate cleared:** independent ROM-backed physical CHR mapping at captured frame boundaries. **Remaining:** actual visible-scanline tile usage, 8x16 OAM hardware sprite components, palette fidelity/transparency/priority, reproducible emulator save-state/input replay. No real user ROM or capture binary was added to GitHub.

## 2026-11-10 — 8x16 OAM hardware component decoding prototype implemented

Added research/mesence/sprite_components.py, which takes **verified startFrame sample #3** from the private phase capture, decodes individual 8x16 hardware OAM entries, and preserves flip flags, palette slots, behind-background priority, transparent pixel index 0, PPU tile addresses, source-ROM offsets and capture SHA-256 provenance. Optional local previews are synthetic grayscale RGBA PNGs; the exporter refuses to place captured game graphics in Git checkouts or overwrite prior files. Synthetic unit tests cover bitplanes, flips, alpha, positioning, source offsets and output safety.

**No character or visible-sprite reconstruction is yet proven.** Final scanline visibility, hardware sprite limits, authentic palette RGB and correspondence to rendered gameplay remain unresolved. This research tool is not integrated into the PySide6 desktop UI. Windows owner validation has not been performed for this prototype.

Procedure: research/mesence/README.md. Phase 3 acceptance remains open.

## 2026-11-10 — Real 8x16 hardware component preview: pause lettering, NOT Mario

The owner successfully ran `sprite_components.py` on the verified `startFrame` sample #3 of frame 265172 and uploaded its metadata-only report and five local PNG previews. The five hardware sprite components spell **PAUSE** (OAM indices 0–4) at Y=89, X=96/112/128/144/160, all using palette slot 3, 8x16 height and recorded physical CHR-ROM tile offsets. This demonstrates that the captured PPU and OAM interpretation can recreate recognizable in-game graphical lettering with transparency, but the session was likely paused in **SMB3 itself**, so these are not Mario sprite parts. The visual identity comes from human inspection of the grayscale previews, not automated asset classification.

**Next phase 3 evidence:** repeat the paired-phase experiment during *unpaused, visibly moving World 1-1 gameplay*, then use the verified sample #3 and metadata-only component diagnostic to inspect Mario-position OAM entries. Sprite-to-screen pixel correspondence, priority, clipping, save-state replay and authentic RGB remain unresolved. The pause capture is a reproducible source-evidence fixture, not a successful Mario sprite.

## 2026-11-10 — First real Mario candidate 16×16 OAM composition

Received second private actual SMB3 phase capture `phase_0000442741_1794295259.json` plus ZIP holding **all 12** associated binary buffers. Verified independent ROM SHA-256, full 8KiB PPU buffer hashes and **3/3** reproducible same-session MMC3 physical mappings; 114 register writes, 0 dropped. At second startFrame (frame 442742), CHR PPU slots `[8,9,96,97,83,4,34,79]`, 8KiB SHA-256 `3262677cd7ad5e9401f48044596532477a605f3fd7eb050dda4d43456bd05c64`. Both endFrame buffers match the expected 8KiB hash `0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918`. Initial startFrame mapping is not independently traced.

**New game-specific finding:** only potentially on-screen OAM entries #10 and #11 occupy X=87/95, Y=162, use 8x16 tile IDs 7/5, are both H-flipped and select palette slot 0. Independently placing these two decoded, alpha-preserving components yields a 16x16 bitmap **visually recognizable as small Mario** (138 opaque pixels). The corresponding physical ROM tile offsets are documented. This is a **candidate hardware character composition** derived from captured and ROM-backed data, not yet a pixel-perfect rendered sprite.

Implemented an explicit-index `--group-oam 10,11` diagnostic composition option with synthetic CI tests. Human inspection of the composite is evidence for the visual identity, but the code does not auto-label actors. See `docs/research/SMB3_FIRST_MARIO_COMPONENTS.md`.

**Still open:** actual framebuffer match, MesenCE RGB palette values, background priority/clipping, scanline sprite-limit behavior, reproducible save state / input history and Phase 3 UI integration.


## 2026-11-10 — Rendered RGB comparison prototype implemented; real runtime pending

New experimental Lua capture (research/mesence/spritemine_render_probe.lua) records 2 complete screen RGB24 buffers at MesenCE endFrame along with four PPU/OAM/palette boundary observations and same-session MMC3 register writes. Original phase capture format remains intact; the read-only verify_phase_capture.py accepts the separately versioned render schema with screen buffer size and SHA-256 checks. New analyze_render_capture.py uses independently matched ROM-backed CHR mapping, an explicit 8x16 OAM group, documented palette-index transparency and a real 256x240 MesenCE screen to report per-index observed RGB consistency. It reports geometry incompatibility and CHR updates before sprite rows rather than assuming pixel-perfect agreement.

Synthetic MesenCE mock tests deliberately change MMC3 banks late in a frame while retaining the correctly rendered pre-switch sprite in the screen RGB buffer. This establishes the tooling/test pipeline, not real Windows end-to-end correspondence. Next owner input: a screencheck_render_*.json report from the new on-device Lua recorder. Implementation and runbook: docs/research/RENDER_RGB_CORRESPONDENCE.md. Do not mark pixel-perfect Mario reconstruction complete without independent rendered-pixel and calibrated color evidence.


## 2026-11-10 — Actual RGB consistency proven; independent default palette check implemented

The owner supplied the **real** MesenCE render session render_0000450823_1794339466.json and the local screencheck_render_0000450823_1794339466.json diagnostic. In frame **450824**, OAM #10/#11 at X=128/136, Y=162 provide a 16×16 small Mario candidate. The source ROM SHA-256 matches verified SMB3 PRG1, full PPU bank mapping is independently verified, startFrame/endFrame OAM and palette RAM are unchanged, no CHR updates occur before the candidate sprite's bottom, and screen resolution is 256×240.

**Observed fitted RGB consistency:** all **138/138** expected opaque pixel positions agree with the modal RGB for each decoded index; ±1-pixel displacements reduce agreement to 55–81/138. Observed RGBs #B53120 (37 pixels), #FECCC5 (31), #000000 (70) independently equal MesenCE's built-in default 2C02 table colors for NES codes 0x16, 0x36, 0x0F. **Crucial:** the screen-only modal score is self-fitted; same-session palette RAM codes are *not present* in the uploaded diagnostic. The independent per-pixel check must be run on the owner’s saved local palette and RGB binaries before a full opaque pixel-color match is marked verified.

**Implemented:** research/mesence/nes_palette_reference.py defines exactly three researched upstream RGB references; analyze_render_capture.py now performs a separate, non-fitted independent_default_palette_check from same-session palette RAM. Unrecognized code values and mismatches are explicit. sprite_components.py optionally emits local reference-colored Mario PNGs under FIXTURE with --reference-colors, retaining index-0 transparency; grayscale default remains unchanged. Synthetic tests added for exact colors, mismatch rejection, unknown codes and local preview alpha.

**Still open:** independent local check execution, 118 transparent/background positions, video settings provenance, actual background/priority composite, sprite limit cases, save-state replay and full animation coverage. Source/runbook: docs/research/SMB3_MARIO_INDEPENDENT_PALETTE.md.

## 2026-11-10 — VERIFIED: default 2C02 Mario opaque RGB, 138/138

The owner reran the local independent default-palette analyzer on the saved real SMB3 PRG1 MesenCE render session `render_0000450823_1794339466` and uploaded `screencheck_independent_render_0000450823_1794339466.json` plus six local PNG previews. **The independent check PASSED:** status `reference_opaque_pixels_exact`, expected/compared/exact **138/138/138**, mismatched **0**, out-of-bounds **0**, at the original OAM coordinates for frame 450824. Actual captured palette RAM codes `0x16` (37/37), `0x36` (31/31), `0x0F` (70/70) map to the fixed upstream MesenCE default 2C02 RGB `#B53120`, `#FECCC5`, `#000000`, not colors fitted to the screenshot.

Independent inspection of all six private PNGs confirmed the 16x16 group's **138 opaque and 118 alpha-zero pixels**, identical masks between grayscale and color reference; each 8x16 hardware component's pixel counts match the group. Source ROM and captured screen/PPU hashes remain traceable. This clears the **single-pose default-2C02 opaque-pixel RGB verification gate**, not the 118 transparent/background pixels or a full hardware compositor. It does not establish alternative palettes, filtering, sprite priority, all poses, or stable save-state/input replay. See `docs/research/SMB3_MARIO_OPAQUE_RGB_VERIFIED.md`.

**Next:** research a non-destructive background-only reference under the same save-state/input/camera state so the 118 source-transparent positions can be compared independently; then test sprite priority and composition. No raw game images or ROM bytes committed to GitHub.


## 2026-11-10 — Background reference replay tool implemented; real test pending

After the independent 138/138 opaque-pixel RGB PASS, the remaining single-pose gate is comparing the other 118 source-transparent pixels against a separately captured background-only render of the *same emulator frame*. Source inspection of MesenCE revision 4b8a196e299b3de297b204fd1208d2981562c89b confirmed a NES Video > Disable Sprites option mapped to the emulator's sprite-output gate, distinct from changing hardware PPU sprite mask or editing the ROM. A deterministic save-state and input replay is required to compare normal versus sprite-hidden output; the current capture does not include a second background render.

Implemented research/mesence/verify_background_composite.py: metadata-only strict paired-render verifier requiring matching source ROM, frame count and master clock, startFrame PPU/OAM/palette hashes, known physical MMC3 bank mappings, same geometry, exact 138 opaque default palette pixels, exact pixels at *every* transparent location, and stable surrounding 8px control ring. Rejects mismatched replay state, unsupported palette codes and ambiguous unchanged renders. Strict success remains conditional because the Lua manifest cannot attest to the user's GUI Disable Sprites state. Deterministic synthetic regression tests passed all Windows/Ubuntu CI checks. **Real paired foreground and background-only MesenCE capture is pending.**

Runbook: docs/research/SMB3_BACKGROUND_COMPOSITE_EXPERIMENT.md. Never put source ROMs, savestates or raw screens in GitHub. Do not label the entire sprite compositor verified.

## 2026-11-10 — Slot-1 graphics replay validated on Windows

The private MesenCE 2.2.1 slot was located, copied and restored independently in nine final processes. The neutral, Right and A plans each passed a 16×16 A/B/A comparison on frame 448385, including exact palette RGB, every transparent position, surrounding controls, and repeated enabled frames. Actual CPU controller reads distinguished effective inputs from a failed Lua-only override. See [observations, build, hashes and reproduction](research/SMB3_GRAPHICS_HARNESS.md). Issue #2 remains open for broader timing, sprite interaction and audio gates.


## 2026-11-10 — Phase 4 prerequisite: contiguous Mario frame timeline (synthetic test stage)

PR #5 (graphics harness) remains a separate, open research PR. Its owner-supplied real SMB3 slot-1 results cover three distinct 16x16 poses (standing 138/118, walking-right 138/118, rising-jump 194/62 opaque/transparent pixels, all 256/256), deterministic enabled/disabled/enabled replay, CPU controller input reads and repeatable full-screen hashes from a second Windows checkout. These are **real sampled-pose gates**, not a complete walking or jumping animation.

The stacked research/smb3-animation-timeline branch adds read-only revalidation and assembly of **one verified target frame per A/B/A replay window**, with consecutive warmup values and actual frame IDs. It exports one 16x16 transparent PNG per accepted frame, a private spritesheet, and timeline.json containing frame numbers, exact PPU master clocks, ROM/OAM/CHR source offsets and checksums. Identical RGBA frames remain separate frame events, preserving holds. A bounded Windows launcher can repeat the existing proven slot-1 A/B/A harness with warmups 8/9/10 to *attempt* a three-frame walking sequence. It leaves all prior evidence immutable and new outputs exclusively in FIXTURE. Synthetic regression tests check timing/source identity, pixel fidelity, retained holds, stale archives, failure cases and output paths.

**Not yet observed on the owner's MesenCE:** new *contiguous* multi-frame animation run, complete SMB3 animation cycles, millisecond timing calibration, loop segmentation, animation UI, GIF/APNG export, sprite priority/scanline limits and enemy animations. A success in synthetic CI is not a real SMB3 sequence. Full next procedure: docs/research/SMB3_ANIMATION_TIMELINE.md.
