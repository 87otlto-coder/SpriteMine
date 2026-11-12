# SMB3 animation timeline — contiguous ROM-verified frame capture

2026-11-10. **Research only** for SMB3 US PRG1. This branch is stacked on graphics validation PR #5; it does not merge or replace that PR. The new timeline is not yet validated on the owner's Windows emulator.

## Approach

PR #5 already verifies A/B/A replay of one target frame from immutable MesenCE slot 1, with sprites enabled / disabled / enabled. It verifies CPU-controller inputs, source ROM/PPU/MMC3, exact palette and opaque pixels, transparent pixels versus independently captured background, unchanged control ring, and identical enabled RGB screens. One replay records two frames, but only its *second* startFrame is guaranteed independently mapped to known MMC3 banks. This experiment therefore uses the **second frame only** from each replay.

Incrementing the existing A/B/A harness's warmup by one causes a separate replay to target an adjacent frame. The assembler independently checks actual frame numbers and start master clocks, rather than assuming the sequence succeeded. Three warmups 8/9/10 should produce three consecutive target frames; real frame counts remain an evidence-dependent outcome.

Implemented:
- research/mesence/animation_windows.py: launches the existing A/B/A harness once per requested warmup. Limits batches to 2–12 frames; checks the original slot SHA before/after each run. Stops at the first failed capture or verification gate, retaining private diagnostics.
- research/mesence/animation_timeline.py: revalidates every archived A/B/A run **read-only**. All three legs, ROM/PPU/palette/OAM, CPU controller bus, timing and background/pixel gates must pass. Rejects different slot/build/ROM/probe/input plan, nonconsecutive frame IDs, warmup gaps and inconsistent master clocks.
- Frames are 16x16 alpha-preserving PNGs from independently source-mapped OAM #10/#11, plus spritesheet.png and timeline.json with exact frame count, observed per-frame master clocks, SHA-256s, physical CHR tile source offsets, X/Y positions, tile IDs and flip flags.
- Repeated identical RGBA frames remain separate one-frame events. No loop boundaries are guessed; milliseconds, GIF/APNG playback fps and complete animation identity are deliberately *not* claimed.

## Windows: first three-frame walking experiment

Only use the existing user slot-1 backing file. Do NOT save over slot 1. Keep all extracted game bytes under F:\Dev\ROMMAGE\FIXTURE.

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics"

git fetch origin
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }

$localBranch = git branch --list "research/smb3-animation-timeline"
if ($localBranch) {
    git switch "research/smb3-animation-timeline"
} else {
    git switch --track "origin/research/smb3-animation-timeline"
}
if ($LASTEXITCODE -ne 0) { throw "Git switch failed" }

git pull --ff-only origin "research/smb3-animation-timeline"
if ($LASTEXITCODE -ne 0) { throw "Git pull failed" }

$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Missing venv. Follow docs/research/SMB3_GRAPHICS_HARNESS.md setup first."
}
$slot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) "MesenCE\SaveStates\Super Mario Bros. 3_1.mss"
if (-not (Test-Path -LiteralPath $slot)) {
    throw "Locate the existing slot-1 backing file; do not create a new save state."
}
$rom = "F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip"
if (-not (Test-Path -LiteralPath $rom)) { throw "Verified ROM ZIP missing" }

& $python -m research.mesence.animation_windows --root "F:\Dev\ROMMAGE" --slot $slot --rom $rom --plan right --first-warmup 8 --count 3
if ($LASTEXITCODE -ne 0) { throw "Animation capture did not pass all gates" }
~~~

Expected **after actual Windows execution**: three fresh GraphicsValidation run folders under FIXTURE/SMB3 and a new Animations output folder containing timeline.json, spritesheet.png and three numbered 16x16 RGBA PNGs. The CLI prints exact paths. Existing slot/ROM/run data is never rewritten. Each frame requires 3 emulator launches, so this is an accuracy-first research tool, not an optimized final capture pipeline.

The slot path comes from the previously verified MesenCE configuration on the owner's Windows machine; if changed, locate its current actual backing file. A state in slot 1 is not automatically an exported named .mss file. The installed supported MesenCE 2.2.1 build was verified in PR #5, but other emulator versions remain unverified.

## Offline assembly

When independently accepted A/B/A capture runs already exist, run research.mesence.animation_timeline with --output pointing to a **new** subfolder under FIXTURE/SMB3/Animations followed by at least two actual GraphicsValidation run directories. It performs the same revalidation without launching MesenCE and refuses to overwrite the original runs or previously exported animations. All sources must represent contiguous frames and consecutive warmups.

## Acceptance boundary

**Tested synthetically:** archived run revalidation without mutation, origin/tile metadata, correct RGBA alpha, adjacent-frame timeline, retained repeated holds, regression tests for input/state/build/mapping/timing mismatches and private export no-overwrite.

**Requires owner's real Windows observation:** the new three-frame moving Mario sequence, frame IDs and master clocks, generated spritesheet and completed timeline. Until then, no claim that the 3-frame sequence or an entire SMB3 walk cycle has been captured.

**Future, separate gates:** capture complete walking/jumping cycles, calibrate clock-to-millisecond playback timing, perform animation state segmentation, support more OAM configurations, investigate sprite priority and per-scanline limits, and integrate into the PySide6 Animation Workspace. Do not put any extracted ROM graphics or reports with embedded game pixels in GitHub.


## Real three-frame SMB3 right-input result — 2026-11-10

The owner supplied timeline.json, frame_000_448385.png, frame_001_448386.png, frame_002_448387.png and spritesheet.png. Independent local Python inspection confirms all PNG SHA-256 and decoded RGBA SHA-256 match the manifest and the spritesheet's three tiles match all individual PNGs byte for byte.

**Verified:** frame IDs 448385, 448386 and 448387, warmups 8/9/10, right-input plan, emulated frame-boundary master clock deltas **29,780 and 29,781**; three distinct full-screen RGB hashes. Each 16x16 Mario candidate has 138 opaque/118 transparent pixels, unchanged sprite OAM position (128,98), tiles (7,5), flips, PPU and palette/OAM hash and exact identical RGBA bytes (SHA-256 b873f8c67626cbaef3d33d7a984b6e39450b6a9af8779846e6d5852548a380d0).

**Finding:** Only ONE visually distinct Mario pose was captured, held for THREE consecutive video frames. Distinct full-screen RGB hashes mean the scene differed somewhere, not necessarily that Mario's pose or position changed. A 3-frame timeline is now **validated on real SMB3**; the full walking animation cycle is not. To support this finding, the timeline assembler now includes unique_visual_frame_count and visual_holds summaries without collapsing source frame events.

Original verified private runs (preserve them):
- F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation\anim-right-w8-extakxfv
- F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation\anim-right-w9-bq6nc6ix
- F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation\anim-right-w10-tmyvtt1w

### Extend without recapturing the first three frames

The animation_windows --reuse-run argument (repeatable) prevalidates existing archives, input plan, slot SHA and consecutive warmups. It captures ONLY warmups 11–19 and then reassembles all 12 frames into a new local animation directory. This is a bounded probe for another pose, not a complete walk cycle guarantee.

Copy-paste PowerShell:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics"

if (git status --porcelain) { throw "Uncommitted changes present; preserve them before switching" }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
git switch "research/smb3-animation-timeline"
if ($LASTEXITCODE -ne 0) { throw "Research branch checkout failed" }
git pull --ff-only origin "research/smb3-animation-timeline"
if ($LASTEXITCODE -ne 0) { throw "Git pull failed" }

$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe"
$rom = "F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip"
$slot = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "MesenCE\SaveStates\Super Mario Bros. 3_1.mss"

$old1 = "F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation\anim-right-w8-extakxfv"
$old2 = "F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation\anim-right-w9-bq6nc6ix"
$old3 = "F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation\anim-right-w10-tmyvtt1w"

foreach ($path in @($python, $rom, $slot, $old1, $old2, $old3)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing: $path" }
}

& $python -m research.mesence.animation_windows --root "F:\Dev\ROMMAGE" --rom $rom --slot $slot --plan right --first-warmup 11 --count 9 --reuse-run $old1 --reuse-run $old2 --reuse-run $old3

if ($LASTEXITCODE -ne 0) { throw "Animation extension did not pass every verification gate" }
~~~

Expected ONLY AFTER successful real execution: a NEW local 12-frame timeline.json, 12 individual transparent 16x16 PNGs, and a 128x32 spritesheet under FIXTURE\SMB3\Animations. The original ROM, slot-1 save state and existing A/B/A evidence are not rewritten. A second distinct Mario RGBA hash would establish a pose change at its recorded emulator frame, not necessarily the complete game animation loop.
