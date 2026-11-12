# SMB3 PRG1 long animation continuation — execution and acceptance packet

**Status:** Implementation proposed on `research/smb3-long-animation-resume`. This file documents tests to be **run by Work mode** on the owner's Windows machine; it does not claim they have run or passed. Reference [Issue #18](https://github.com/87otlto-coder/SpriteMine/issues/18). No GUI is needed.

## Source evidence and expected behavior

The immutable prior timeline is:

`F:\Dev\ROMMAGE\FIXTURE\SMB3\Animations\right-8-19-fa85855b36\timeline.json`

It covers warmups 8–19, real emulator frames 448385–448396, two unique RGBA poses, and three holds A(5) → B(6) → A(1 observed). All individual PNG-file/pixel hashes and spritesheet crops were independently checked from an owner-uploaded private archive. The initial A return is **not** proof of a complete repeating walk cycle.

This change adds:

- `animation_archive.read_verified_timeline`: verify frame records, exact PNG SHA-256s and RGBA hashes, spritesheet pixels and geometry, contiguous emulator frames/warmups/clocks, and held-frame summaries **without emulator execution**.
- `animation_archive.verified_timeline_runs`: reassemble the referenced prior A/B/A runs read-only and compare all provenance and output metadata before any new emulator session.
- `animation_windows --reuse-timeline PATH`: source prior runs from a trusted timeline rather than listing all `--reuse-run` paths manually; permit >12 total timeline frames, while still limiting **new** captures to 2–12 per invocation and warmups to 2–120. `--reuse-run` remains available, but cannot be mixed with `--reuse-timeline`.
- `animation_preview --timeline PATH`: generate a new, private, offline HTML viewer beside the PNGs, with frame stepping, zoom and illustrative playback speed. It refuses to overwrite a previous preview and does not assert verified loop timing.
- Synthetic regression tests for continuation, archive corruption, state mismatch, no-overwrite, interruption and hold preservation.

**Substantive limitation:** The supported subject is still the explicit small Mario OAM pair #10/#11. This is not general sprite grouping or complete animation coverage. Each newly verified frame still costs three independent MesenCE launches; no new optimizer/fast path is claimed.

## 1. Verify repository state before checkout (PowerShell)

Do not assume that `origin/research/smb3-emulator-feasibility` is present locally; a previous checkout failed with `fatal: invalid reference`. The owner has multiple Git checkouts, potentially using restricted fetch refspecs.

~~~powershell
$repo = "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics"
Set-Location -LiteralPath $repo
git status --short
git branch --show-current
git remote -v
git config --get-all remote.origin.fetch
git branch -a
~~~

If any local changes are present, preserve/reconcile them **before switching**. Avoid force checkout/reset. To explicitly fetch the tested research feature branch even when the remote's configured refspec is restricted:

~~~powershell
Set-Location -LiteralPath "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics"
git fetch origin "refs/heads/research/smb3-long-animation-resume:refs/remotes/origin/research/smb3-long-animation-resume"
if ($LASTEXITCODE -ne 0) { throw "Explicit branch fetch failed" }
if (git branch --list "research/smb3-long-animation-resume") {
    git switch "research/smb3-long-animation-resume"
} else {
    git switch --track "origin/research/smb3-long-animation-resume"
}
if ($LASTEXITCODE -ne 0) { throw "Checkout failed" }
git pull --ff-only origin "research/smb3-long-animation-resume"
if ($LASTEXITCODE -ne 0) { throw "Fast-forward pull failed" }
~~~

Expected: checked-out feature branch, no uncommitted changes and the new archive/preview modules exist. Do not silently switch back to an older branch after a checkout error.

## 2. Test synthetic functionality before using the private ROM

~~~powershell
Set-Location -LiteralPath "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics"
$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Existing research venv missing" }
& $python -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Python dependencies failed" }
& $python -m compileall -q research tests
if ($LASTEXITCODE -ne 0) { throw "Python syntax check failed" }
& $python -m pytest -q tests/test_animation_windows.py tests/test_animation_timeline.py tests/test_animation_resume.py
if ($LASTEXITCODE -ne 0) { throw "Animation regression suite failed" }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Complete synthetic regression suite failed" }
~~~

Work should also review the existing Windows-only research Python 3.11/3.12 and Lua 5.4 checks. Never switch Actions jobs to Linux/macOS or upload ROM/artifact ZIPs. Record exact commands, counts and failures. **Fixes belong back in the original chat**, rather than silently redesigning the code under test.

## 3. Validate existing 12-frame archive without capturing new frames

~~~powershell
Set-Location -LiteralPath "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics"
$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe"
$old = "F:\Dev\ROMMAGE\FIXTURE\SMB3\Animations\right-8-19-fa85855b36\timeline.json"
if (-not (Test-Path -LiteralPath $old)) { throw "Existing private timeline missing" }
& $python -c 'from pathlib import Path; from research.mesence.animation_archive import verified_timeline_runs; import sys; runs=verified_timeline_runs(Path(sys.argv[1])); print(f"Verified source windows: {len(runs)}")' $old
if ($LASTEXITCODE -ne 0) { throw "Archived timeline revalidation failed" }
~~~

Expected: exactly 12 source windows revalidated from the preserved A/B/A archives; no files changed. If older report format or ROM data causes a mismatch, report it rather than rewriting the original timeline to satisfy the code.

## 4. Bounded real capture: warmups 20–25

**Only after the preceding checks pass.** Confirm that the MesenCE installation and private slot-1 backing file are present, unchanged, and owned by the user. The fixture remains under FIXTURE. Capture six new source windows, resulting in an expected **18-frame** combined timeline; do not predict the new pose sequence.

~~~powershell
Set-Location -LiteralPath "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics"
$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe"
$root = "F:\Dev\ROMMAGE"
$old = "F:\Dev\ROMMAGE\FIXTURE\SMB3\Animations\right-8-19-fa85855b36\timeline.json"
$rom = "F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip"
$slot = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "MesenCE\SaveStates\Super Mario Bros. 3_1.mss"
foreach ($file in @($python, $old, $rom, $slot)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Missing prerequisite: $file" }
}
$romBefore = (Get-FileHash -LiteralPath $rom -Algorithm SHA256).Hash
$slotBefore = (Get-FileHash -LiteralPath $slot -Algorithm SHA256).Hash
& $python -m research.mesence.animation_windows --root $root --rom $rom --slot $slot --plan right --first-warmup 20 --count 6 --reuse-timeline $old
if ($LASTEXITCODE -ne 0) { throw "Extended capture/assembly failed; preserve private diagnostics" }
if ((Get-FileHash -LiteralPath $rom -Algorithm SHA256).Hash -ne $romBefore -or
    (Get-FileHash -LiteralPath $slot -Algorithm SHA256).Hash -ne $slotBefore) {
    throw "Source ROM or save-state hash changed"
}
~~~

The emitted JSON includes the **actual** new `timeline_json` and `spritesheet_png` paths. Verify that the new timeline contains 18 consecutive frames 448385–448402, all PNG hashes match, and the 12 old A/B/A archives remain unmodified. If any graphics gate fails, stop and preserve the private run folder; never claim an 18-frame result on the strength of partial runs alone.

## 5. Private shell preview and analysis handoff

After a successful real capture, replace `<ACTUAL_NEW_TIMELINE_PATH>` with the path emitted by step 4:

~~~powershell
Set-Location -LiteralPath "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics"
$python = "F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe"
$timeline = "<ACTUAL_NEW_TIMELINE_PATH>"
& $python -m research.mesence.animation_preview --timeline $timeline
if ($LASTEXITCODE -ne 0) { throw "Private HTML preview integrity gate failed" }
Start-Process -FilePath (Join-Path (Split-Path $timeline -Parent) "preview.html")
$data = Get-Content -LiteralPath $timeline -Raw | ConvertFrom-Json
$data.visual_holds | Select-Object first_emulator_frame,last_emulator_frame,duration_frames,rgba_sha256 | Format-Table -AutoSize
~~~

Playback speed in HTML is **illustrative, not NES frame timing**. Keep all PNG/HTML/ZIP evidence local or share privately with the owner; never publish it to GitHub Actions, Git commits or PR attachments.

Return to the original ChatGPT research conversation: the new `timeline.json`, exact source hashes and capture logs, verification/test results, and an optional privately shared image archive for independent visual inspection. Report any mismatch and whether there is sufficient evidence of repeated transitions, without declaring a complete loop prematurely.

## Other acceptance gates / intentionally unresolved

- Hardware background priority and eight-sprites-per-scanline effects remain unsupported or not tested.
- This continuation validates a constrained 16×16 Mario OAM subset, not all SMB3 characters.
- Audio, World 1-1 level decoding, a production MesenCE adapter and PySide6 integration are out of scope.
- A repeated A→B→A pattern **might** indicate periodic behavior but does not by itself establish the game's complete animation-state machine, speed-dependent variants, or an exact wall-clock duration.
- Document Windows environment, remote refspec issue, checks actually run, exact output folder names, all failures and the next bounded experiment.
