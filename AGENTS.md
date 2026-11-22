# SpriteMine engineering instructions (source of truth)

## Current product mission — CREATIVE PRODUCTION FIRST (2026-11-22)

**Owner M1 revision (2026-11-22) overrides the earlier section-GIF criteria below:** a complete **11-screen × 27-row main World 1-1** panorama (nominal **2,816×432** logical pixels), including vertical world/scroll coverage, correct art/placement and no texture defects, must precede animation. The entire level is one stationary scene (no repeated sections); Mario none or one; **enemies last**. Existing enemy object records are already documented in `W101O` research, but not in GIF code. See [full-level acceptance](creative/SMB3_WORLD11_FULL_LEVEL_M1_ACCEPTANCE.md).

**Owner-approved realignment:** SpriteMine is a Windows-first **creative asset extraction, composition, animation and export kit**, starting only with **Super Mario Bros. 3 (US PRG1 / Revision A)**. Our goal is to produce usable animated stages/wallpapers, sprites and audio — **not** to reverse engineer the whole game.

**Required reading:** [docs/PRODUCT_DIRECTION.md](docs/PRODUCT_DIRECTION.md) is the authoritative product brief; [docs/ROADMAP.md](docs/ROADMAP.md) defines the current output-first milestone sequence. These override stale research-first directives in older PRs, docs and chat threads. Prior verified research remains valid, but it is supporting infrastructure, not the goal.

**FIRST deliverable:** a **compiled, animated, seamlessly looping World 1-1 stage GIF**, constructed with a repeatable headless browse → extract/capture → compose → animate → preview → export workflow. It must be a visually inspected, playable GIF, not merely tests, JSON, screenshots, or a PPU validation report. Do not prioritize UI or audio until this first creative output is accepted.

Be SpriteMine's technical lead and make routine implementation decisions proactively. Avoid unrelated games, consoles, AI recognition or needless abstraction.

## Working rules
- At the start of every development task, inspect branch/PR history and read **this file, `docs/PRODUCT_DIRECTION.md`, `docs/ROADMAP.md`, `docs/PROJECT_STATUS.md`**, and the most recent creative outputs. Treat GitHub as authoritative over chat memory.
- Identify the **next working exported asset** and a minimal blocker before researching internals. Prefer using existing ROM decoders, emulator capture, manual composition and visual QA rather than recreating gameplay or PPU details.
- Never modify a source ROM. Never commit or distribute ROMs, extracted copyrighted assets, save states, or captures. Verify Git status before committing.
- Preserve source SHA-256, ROM offsets/bank mappings, frame and scanline indices, decoder versions, emulator states, and controller input histories as applicable.
- Preserve evidence labels `raw`, `captured` and `decoded`; label creative assemblies `composed/edited`. Never claim an OAM component is a full character; distinguish native captured art from constructed animation. Screenshot assembly may be valid **creative composition**, but must not be called complete decoded level data.
- Grayscale CHR visualizations are not authentic NES colors. Preserve palette and sprite transparency explicitly when rendering live assets.
- Keep extraction code separate from UI; isolate emulator integration behind an adapter. MesenCE is a candidate, not an assumed stable drop-in API.
- Validate game-specific decoders used in exports against the verified SMB3 ROM; don't invent memory mappings or native asset identities. **Do not require exact game-internal reconstruction** when a captured or hand-assembled asset meets the visual/audio acceptance requirement with honest provenance.
- Check licenses before copying third-party code. Pay particular attention to MesenCE GPLv3 and SMB3 disassembly redistribution limitations.

## Implementation workflow
- Use `feature/*` branches for implementation and `research/*` branches for experiments. Prefer PRs targeting `main`; never push directly to `main` without explicit instruction.
- Make small reviewable commits, add deterministic tests, and document behaviors/unsupported cases. Preserve historical research evidence but prioritize work on the creative output pipeline.
- Complete for a production milestone means an **actual playable/visible/audible exported file**, inspected for visual/audio quality, with an editable/reproducible recipe and provenance. Tests and private Windows validation support this; neither alone is a finished deliverable.
- **Research gate:** Before investigating deeper ROM/PPU/gameplay internals, identify the specific blocked output, a simpler extraction/capture/manual alternative, the smallest experiment needed, and how its result will improve the current export. If this cannot be answered, defer research.
- Update `docs/PROJECT_STATUS.md` after substantive changes; update `docs/ROADMAP.md`, `docs/DECISIONS.md`, and these instructions if the approach changes. Keep the `docs/PROJECT_INSTRUCTIONS.md` ChatGPT summary aligned.
- Give complete copy-paste PowerShell commands with explicit working directories and expected outcomes. Report what changed, what passed, what is unresolved, and what comes next. Avoid emojis.

## Canonical local Windows workspace

Keep all SpriteMine development and research under F:\Dev\ROMMAGE:
- SOURCE: production Git checkouts, research code, development scripts, and docs.
- TOOLS: MesenCE emulator binaries and supporting debugging utilities.
- FIXTURE: immutable original ROMs, save states, raw captures, validation fixtures, and extracted game graphics.
- OUTPUT: playable generated GIFs, wallpaper videos, audio exports and editable compositions.
- REPORTS: private visual/audio QA notes and progress/coverage summaries.

Use explicit absolute PowerShell paths. Do not create unrelated Git checkouts
or copyrighted capture/output folders under the user's HOME directory.
The main production source checkout is F:\Dev\ROMMAGE\SOURCE\SpriteMine.
A separate existing research checkout may still be under TOOLS, as documented
in the relevant historical research procedure.

## Active creative milestone ladder — supersedes previous research phase order

**M1 (active):** Headless World 1-1 **compiled animated stage GIF**. Browse/extract/capture game graphics, compose a scene from independent layers/objects, animate at least two independently controlled elements, preview and export a seamless playable GIF. Save a reusable composition recipe, output and provenance. No GUI prerequisite and **no full level/gameplay decoder prerequisite**.

**M2:** Music + SFX extraction/capture, playback, trim/loop and WAV (optionally FLAC) exports. Deliver at least one playable music loop and one sound effect, with provenance. Full music sequence disassembly is optional.

**M3:** Reusable asset/project library, browse/search, sprite sheets/GIF/APNG and wallpaper-friendly exports (MP4/WebM when practical). Reuse earlier GIF/audio assets in a second composition.

**M4:** PySide6 Windows creative interface over working headless tools. ROM → browse → compose → preview → GIF/audio export; native Windows acceptance and packaging.

The previously verified ROM/CHR, MMC3, PPU/CIRAM and 13-frame RGB research in unmerged PRs #21–#25 is valuable reusable code, **not** a requirement to deepen the reverse engineering or blindly merge all research branches first. Build a creative output from the smallest usable pieces.

**Prioritize demonstrable creative outputs over comprehensive game internals.**

## GitHub Actions storage and repository governance

Git is authoritative for source, build recipes, lockfiles, synthetic tests and shareable research records. Use review branches and pull requests. Preserve source history and repository visibility.

Keep the inputs, tool versions, commands, observations and provenance needed to reproduce a finding. Before expiring a sole copy of evidence, identify the files and their owner and pause for approval. Verify any durable, authorized copy by checksum. Keep proprietary ROMs, game files, derived assets, private fixtures and secrets out of commits, CI logs, caches and uploads. Record hashes and local reproduction instructions where appropriate.

Run each expensive check once per required event and platform. Reuse existing jobs, avoid repeated uploads and restrict upload paths to the intended deliverable. Give disposable generated builds a three-day expiry as a backup. After a new upload and its producing run both succeed, retain the newest three successful disposable builds across all repository branches. Upload first even at capacity, then serialize cleanup and delete the oldest eligible builds by exact artifact name and ID. A changed hash, commit, branch or milestone alone does not justify retention.

Before cleanup, inventory artifact IDs, names, sizes, digests and producing runs. Inspect the contents and confirm how to recover source and evidence. Delete only identified disposable artifacts. Record decisions and reasons, then re-list the inventory and reconcile deleted IDs, bytes and protected artifacts. Keep the ledger outside the expiring build.

For SMB3 research, preserve ROM fingerprints, mapper state, timing and input provenance in shareable records. Keep captures and save states local. Use synthetic data in Windows-only CI; do not reintroduce an Ubuntu OS matrix.

## Mandatory GitHub Actions incident guidance

Before editing or running CI, read [docs/ACTIONS_INCIDENT_2026-11-11.md](docs/ACTIONS_INCIDENT_2026-11-11.md). This project is **Windows-only for GitHub Actions**: use `windows-latest`, no Ubuntu/Linux/macOS jobs or OS matrices unless the owner authorizes them. Avoid redundant branch-push builds and unnecessary version combinations. Keep synthetic tests; never upload ROMs or captures. A previous statement above refers to the historical Windows/Ubuntu matrix: that matrix was intentionally retired in the incident follow-up. Do not reintroduce it.
