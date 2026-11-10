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
