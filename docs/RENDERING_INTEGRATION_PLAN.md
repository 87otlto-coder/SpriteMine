# SpriteMine SMB3 — Rendering-to-desktop integration gate

**Status 2026-11-22: plan only, no production merge or Windows GUI validation performed by this report.**
Primary milestone remains **Super Mario Bros. 3 USA PRG1 / Revision A**. The current engineering branch is draft PR #25, stacked on the accepted native PPU/CIRAM research in PR #24.

## Current independently supported boundaries

| Gate | Result | Limitation |
| --- | --- | --- |
| Immutable ROM parser + raw CHR exports | Phase 0 merged to main | No semantic asset identity |
| NES player / mask research | PR #21: 81 recipes, selected canonical poses, 7,528 distinguishable pipe-mask pixels and 864-byte logical bonus map | Selected OAM poses/pipe route only; unmerged |
| Source-to-CPU background staging | PR #22/#23: 32 pattern + 32 attribute strips; 2,176 bytes match native | Selected first-entry Plains bonus room; unmerged |
| CPU writes to physical CIRAM | PR #24: owner Windows `passed: true`, 51 tests, 104 frames and zero physical discrepancies | End-frame memory states, not per-dot PPU timing; unmerged |
| World 1-1 bonus gameplay background | PR #25: original-ROM model AND owner's committed CLI matched 13 × 256 × 192 = 638,976 exact RGB pixels, zero differences; fetch-time MMC3 pages derived from native register writes | Accepted for the bounded gameplay viewport; HUD and OAM remain separate; unmerged |
| Initial CHR desktop explorer | PR #4: runnable PySide6 ROM/bank/tile viewer; owner previously opened bank 0, tile 19 | Additional Windows interaction/exports/error cases pending |
| Integrated usable Windows app | Not achieved | No consolidated navigation, editor, audio, catalog or installer |

**No percentage of total game assets is claimed.** A single thoroughly verified level/bonus subset is not a measure of global coverage.

## Read-only branch and CI integration preflight — 2026-11-22

The branch topology was checked via GitHub's commit comparison API
against current `main`. The five headless PRs have **strict linear
ancestry**, with each containing all commits from its preceding branch:

| PR | Branch relationship | Last checked hosted Windows CI |
| --- | --- | --- |
| [#21](https://github.com/87otlto-coder/SpriteMine/pull/21) | `main` → `feature/smb3-headless-player` | PASS, run `44477955575` |
| [#22](https://github.com/87otlto-coder/SpriteMine/pull/22) | #21 → `feature/smb3-world11-background` | PASS, run `44479504307` |
| [#23](https://github.com/87otlto-coder/SpriteMine/pull/23) | #22 → `feature/smb3-world11-staging-capture` | PASS, run `44514569132` |
| [#24](https://github.com/87otlto-coder/SpriteMine/pull/24) | #23 → `feature/smb3-world11-ppu-write-trace` | PASS, run `44958745616` |
| [#25](https://github.com/87otlto-coder/SpriteMine/pull/25) | #24 → `feature/smb3-world11-visible-background` | PASS on accepted implementation, run `44959428665`; newer documentation-only CI may recur |

All five are currently **open drafts**, not merged to `main`.
Comparisons show no unrelated binary source or private fixture files among
their changed paths. This is a **merge planning preflight**, not a substitute
for final review or `main`-branch regression checks.

The existing static PySide6 explorer [PR #4](https://github.com/87otlto-coder/SpriteMine/pull/4)
**has diverged from `main` (17 commits ahead, 4 behind)**. It must
be rebased or carefully reimplemented onto the final integrated code before
merging, and its prior Windows smoke results **do not** satisfy the
pending native interaction/export/error-path acceptance.

**Next decision:** integrate the headless stack in dependency order only
after review and checks, then reconcile the GUI branch. Do not blindly
merge PR #4 and do not merge divergent animation research PRs #19/#20
as part of this narrow sprint.

## Review/merge sequence (one controlled integration sprint)

1. **PR #25 native CLI gate — accepted 2026-11-22.** The owner ran the exact committed offline verifier at `a462499` against the existing private replay and original PRG1 ROM with pinned local MesenCE RGB source, obtaining **61 passed** and **13 frames / 638,976 exact RGB pixels, 0 mismatches**. The JSON report is preserved privately in `FIXTURE`. This acceptance is limited to the 256×192 bonus gameplay viewport.
2. **Review the stacked PR chain before merging:** #21 → #22 → #23 → #24 → #25. Confirm each is targeted to its immediate parent; review changed files and tests for imported third-party code, unsupported asset identities, private fixture leakage and missing provenance. Do **not** blindly merge divergent PR #19/#20 research branches.
3. **Integrate one at a time to `main`** after acceptance, retargeting the next stacked PR as needed and verifying Windows Python 3.11/3.12 CI at each step. Never assume a passing branch check proves the final integrated branch.
4. **Complete and integrate the existing PySide6 PR #4**, rebased onto the consolidated head. Owner must check bank 15, scroll/zoom, preview palette, deterministic exports into new private `FIXTURE` folders, corrupt-ROM rejection and non-destructive behavior.
5. **Build a minimal useful vertical slice**, not a new general-purpose framework: open verified ROM → browse CHR bank/tile → inspect a validated World 1-1 bonus frame (with the **separate 256×192 background/HUD limitation shown**) → export source-derived indexed/RGB PNG and JSON provenance privately. The preview must clearly distinguish `raw`, `captured` and `decoded` evidence and record source ROM, bank mappings, frame, decoder version and palette profile hash.
6. **Next graphics coverage:** independently reconstruct status-bar/IRQ split and then complete sprite/background compositing; expand to the main World 1-1 level only after the bonus viewport workflow is integrated and validated.
7. Resume the distinct Phase 4 animation-export, Phase 6 WAV/FLAC capture, catalog and Windows packaging work after this vertical slice, without declaring whole-game coverage.

## Acceptance criteria for the integration sprint

- All production changes are reviewed, hosted on Windows-only CI, and reproducible locally on the user's Windows PowerShell environment.
- The integrated application can launch, import exact SMB3 PRG1, show CHR and the **validated subset** of background, and produce a provenance-backed private output.
- A failed or unsupported reconstruction is clearly labelled, not silently substituted with screenshots or emulator output. Screenshots are never treated as source of the decoded scene.
- Test fixtures are deterministic and private; no copyrighted ROMs, graphics/audio, savestates, raw PPU dumps or external GPL source are committed to the public GitHub repository.
- The app remains modular: game/PPU decoders cannot depend on PySide6; emulator hooks remain independently replaceable; versioning and offsets are preserved.
- Complete release is still separately gated on sprites, animations, World 1-1 main-level decoding, audio, searchable catalog, and Windows package/QA.

## Repository layout

- `F:\Dev\ROMMAGE\SOURCE` — SpriteMine Git checkouts, source and technical documentation.
- `F:\Dev\ROMMAGE\TOOLS` — third-party emulator, research utilities and pinned MesenCE source (license respected).
- `F:\Dev\ROMMAGE\FIXTURE` — original immutable ROM, replay checkpoints, private image/audio captures and acceptance JSON.
- `F:\Dev\ROMMAGE\OUTPUT` — user-facing private asset exports where appropriate.
- `F:\Dev\ROMMAGE\REPORTS` — local operational and coverage summaries, excluding copyrighted raw source assets.

**Critical operational decision:** do not begin a fresh multi-week research branch before the tested branch chain has a documented, reviewable path into a usable Windows user flow.
