# PR #19: MesenCE portable replay and 24-frame acceptance test

**2026-11-12. Prepared; NOT executed.** SMB3 US PRG1 only. Work is the independent tester, not the implementer. Report defects to the original ChatGPT thread without rewriting PR #19 or merging it. Keep the previous 18-frame private evidence intact.

## Why

The prior private capture covered 18 consecutive emulator frames 448385–448402 (warmups 8–25): A for 5 frames, B for 6, A for 4, and C for at least 3. At 448402 C retained its RGBA appearance while Y changed by one pixel. No complete loop is established.

MesenCE 2.2.1 failed once at warmup 20 with UnauthorizedAccessException to C:\Users\87otl\Documents\MesenCE. Official MesenCE source (tag 2.2.1, UI/Config/ConfigManager.cs) shows that an existing settings.json beside Mesen.exe selects portable HomeFolder. A later private capture was successful with a portable configuration. This PR now stages a checksum-verified copy of the SAME executable and an explicitly supplied, valid settings.json under FIXTURE/SMB3/EmulatorRuntime, without modifying installed Mesen or source settings. The A/B/A verifier compares the settings fingerprint across legs. Prior captures had no such recorded config SHA, so do not claim historical identical configuration.

The 18-frame evidence was made in private C: workspace. New explicit --rehome-archive revalidates byte-preserving copied capture directories under F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation. It only normalizes source absolute run_dir locators; all A/B/A provenance and pixels must match. The ORIGINAL 18-frame timeline JSON is never edited. A new continuation.json receipt preserves its SHA-256.

## Source fingerprints

- Prior 18-frame timeline.json SHA-256: 1e48bf12926edcb80e451154c4e1a7aa809480d9467e313c2ea460a452eba1eb
- Original ROM bytes SHA-256 (inside ZIP): 4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579
- Slot-1 state: 31f5f5ae97d9f8c5d8aa3fded0c6a2d64f2c19c9fedad1d7237d81d264d759f2
- Mesen.exe: 8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7
- Original Lua probe: 8b50620cc322893a272fdf07292f83aeb0690ff2a595efdd9081d9f5b0722283

## Gate 1: Checkout and automated tests

Use F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics on Windows when accessible. Record git status, remotes, fetch refspecs and HEAD; do not discard local changes. The old checkout lacked origin/research/smb3-emulator-feasibility; fetch the actual PR branch explicitly:

~~~powershell
$repo = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics'
Set-Location -LiteralPath $repo
if (git status --porcelain) { throw 'Preserve uncommitted changes before checkout' }
git fetch origin 'refs/heads/research/smb3-long-animation-resume:refs/remotes/origin/research/smb3-long-animation-resume'
if ($LASTEXITCODE -ne 0) { throw 'Explicit fetch failed' }
if (git branch --list 'research/smb3-long-animation-resume') {
    git switch 'research/smb3-long-animation-resume'
} else {
    git switch --track 'origin/research/smb3-long-animation-resume'
}
if ($LASTEXITCODE -ne 0) { throw 'Branch switch failed' }
git pull --ff-only origin research/smb3-long-animation-resume
if ($LASTEXITCODE -ne 0) { throw 'Pull failed' }
git rev-parse HEAD
$python = Join-Path $repo '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Create a supported Windows Python 3.11/3.12 research venv first' }
& $python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed' }
& $python -m compileall -q research tests
if ($LASTEXITCODE -ne 0) { throw 'Syntax check failed' }
& $python -m pytest -q tests/test_graphics_harness.py tests/test_animation_windows.py tests/test_animation_timeline.py tests/test_animation_resume.py tests/test_animation_portability.py
if ($LASTEXITCODE -ne 0) { throw 'Targeted regressions failed; do not capture' }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Full suite failed; do not capture' }
~~~

Exercise invalid/corrupt portable settings, altered staged executable, mismatched config across A/B/A legs, invalid or tampered relocated sources, bad archive hashes, and startup failure preservation. No Linux/macOS runners, public artifacts, excessive workflow runs, or copyrighted fixtures in GitHub.

## Gate 1a: Regression failure correction (2026-11-12)

Work's first independent Windows run at commit `3956f236983c1510bd87ab5290376a5745653bb8` reported **57 passed, 3 failed, 0 skipped** in targeted tests and **143 passed, 3 failed, 2 skipped** in the complete suite. Compilation passed; no new emulator processes or captures were launched. The failures were limited to the relocation tests: the shared synthetic fixture used `synthetic-w8` directory names, whereas relocation accepts the `anim-` prefix used by real captured A/B/A runs. No source-archive relocation has passed on real private evidence yet.

The fixture now uses `anim-right-w{warmup}-synthetic`. The security check still rejects any archived run directory not beginning with `anim-`; a new negative test explicitly asserts that `synthetic-w8` is rejected even under an otherwise valid FIXTURE hierarchy.

**Rerun Gate 1 in full on the updated PR HEAD before Gate 2 or 3.** Require all three former failure cases to pass by name, plus the newly added negative test. Preserve exact failure tracebacks and test count. A passing suite on Python 3.14.7 does not establish supported Python 3.11/3.12 compatibility; run 3.11/3.12 on Windows when available, otherwise mark the compatibility gap unresolved. The canonical F: checkout had unusual restricted fetch configuration and could not establish a clean working tree; an isolated checkout is acceptable for *synthetic tests* if matched against GitHub SHA, but do not claim native F: capture readiness until source fixtures and the 18 A/B/A archives are accessible and independently revalidated.

## Gate 1b: interruption test isolation correction (2026-11-13)

Independent Work retest at `d494d3715a3a8e0323091f06ba471caa44510ed1` reported compilation passed, targeted **59 passed / 2 failed**, full suite **145 passed / 2 failed / 2 skipped**. The three earlier relocation failures are now fixed, and the new invalid-directory-prefix test passed.

Two unrelated interruption assertions in `tests/test_animation_resume.py` still used broad `anim-right-w2*` and `anim-right-w20-*` globs, which now pick up existing `anim-right-w20..25-synthetic` fixture directories. The first counted eight instead of two created directories. The second could not choose a unique warmup-20 capture. **No emulator ran and no real source evidence was relocated.**

The corrected tests snapshot `GraphicsValidation` before each simulated batch and take a set difference afterward. They explicitly verify exactly the two newly created run directories, select the successful new warmup-20 run for resume, and reject reuse of the failed new warmup-21 run. They retain the now-correct fixture names and invalid-name rejection test. No production validator or capture implementation was weakened.

**Retest Gate 1 in full at the latest PR head.** Require both interruption tests to pass, confirm that all four relocation/security tests from the earlier round still pass, and stop at any failure before Gate 2. The Python 3.11/3.12 verification gap remains open; Python 3.14 alone is not acceptance of supported versions.

## Gate 2: Resolve prior evidence and portable profile

Original Work private timeline location was:
C:\Users\87otl\Documents\ChatGPT\SpriteMine\PR19-private\FIXTURE\SMB3\Animations\right-8-25-bad20ce00c\timeline.json

This is historical, NOT proof that the path still exists. Locate its actual copy, or restore evidence from the privately supplied ZIP. Verify original timeline SHA, 18 PNG hashes, spritesheet integrity and 18 complete GraphicsValidation A/B/A directories. Copy only absent verified capture directories into F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation, preserving bytes and names. Never overwrite a pre-existing F: run; compare hashes or fail on conflicts. Use Python to call:

~~~powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics'
$python = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe'
$old = '<EXACT_VERIFIED_18_FRAME_TIMELINE_PATH>'
$runs = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\GraphicsValidation'
& $python -c 'from pathlib import Path; from research.mesence.animation_archive import verified_timeline_runs; import sys; runs=verified_timeline_runs(Path(sys.argv[1]), runs_parent_override=Path(sys.argv[2])); print("Verified copied A/B/A runs:",len(runs))' $old $runs
if ($LASTEXITCODE -ne 0) { throw 'Original 18-frame evidence was not revalidated' }
~~~

Expected: 18 independently revalidated windows. Identify a real existing, readable MesenCE settings.json (prefer the previously successful Work portable profile) and record its SHA-256. Do not substitute an arbitrary empty JSON object or write it beside the user's installed emulator. Confirm the Mesen binary and slot SHA values above.

If F: is inaccessible, report that limitation rather than silently claim a canonical workspace test.

## Gate 2a: canonical six-run promotion and permissions (2026-11-13)

Independent Work verification at PR #19 head 36e20202d3b03dafe18b6b53656b05aa60014cf6 reported **61 targeted passed / 0 failed**, **147 full passed / 0 failed / 2 optional skips**, and all **18 original A/B/A runs** revalidated from the private C: source. The existing canonical F: warmups 8–19 matched across 948 file SHA-256s. Warmups 20–25 were fully verified in the original C: source (79 files each) but missing from canonical F:. Work's F: mount was read-only, so **no migration, emulator startup, or new capture took place**. Last verified real frame remains 448402.

The stripped-down private sharing archive has only **77 files per A/B/A directory**, omitting replay.nes and slot-copy.mss. It is not a valid migration source and should never be repaired by regenerating those bytes. Use only the original complete 79-file C: source.

A new narrow helper `research/mesence/promote_private_runs.py` plus synthetic tests `tests/test_private_run_promotion.py` was added. Before any write it verifies the original timeline SHA, all 18 original A/B/A runs, all 12 existing canonical source runs, six exact missing directory names, 79-file completeness, and copied ROM/state SHA-256. Its default CLI is read-only; `--apply` stages and checks the six absent directories, refuses overwrites, and verifies all 18 canonical source captures afterward.

**Work: test the new helper synthetically and run its read-only preflight only.** If F: remains read-only, do not attempt `--apply` from Work. Instead the owner can use the complete, copy-paste-ready local PowerShell instructions in [SMB3_CANONICAL_FIXTURE_PROMOTION.md](SMB3_CANONICAL_FIXTURE_PROMOTION.md) on a Windows session with the required read/write access. Do not proceed to Gate 3 until 18 canonical A/B/A runs verify AND Work can write canonical F: capture outputs. No automatic C: fallback is authorized by this packet.

## Gate 3: Six new real Windows captures

Run only after all earlier gates pass. Use existing verified ROM, original slot and real settings profile. The source timeline may still reside on C:; --rehome-archive handles copied run directories under F:.

~~~powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics'
$python = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe'
$root = 'F:\Dev\ROMMAGE'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
$slot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'MesenCE\SaveStates\Super Mario Bros. 3_1.mss'
$old = '<EXACT_VERIFIED_18_FRAME_TIMELINE_PATH>'
$settings = '<EXACT_EXISTING_VALID_MESENCE_SETTINGS_JSON_PATH>'
foreach ($file in @($python, $rom, $slot, $old, $settings)) {
    if (-not (Test-Path -LiteralPath $file)) { throw "Missing prerequisite: $file" }
}
$romBefore = (Get-FileHash -LiteralPath $rom -Algorithm SHA256).Hash
$slotBefore = (Get-FileHash -LiteralPath $slot -Algorithm SHA256).Hash
$settingsBefore = (Get-FileHash -LiteralPath $settings -Algorithm SHA256).Hash
& $python -m research.mesence.animation_windows --root $root --rom $rom --slot $slot --plan right --first-warmup 26 --count 6 --reuse-timeline $old --rehome-archive --emulator-settings $settings
if ($LASTEXITCODE -ne 0) { throw 'Capture failed; preserve all private diagnostics' }
if ((Get-FileHash -LiteralPath $rom -Algorithm SHA256).Hash -ne $romBefore) { throw 'ROM changed' }
if ((Get-FileHash -LiteralPath $slot -Algorithm SHA256).Hash -ne $slotBefore) { throw 'Slot changed' }
if ((Get-FileHash -LiteralPath $settings -Algorithm SHA256).Hash -ne $settingsBefore) { throw 'Settings changed' }
~~~

**Expected only after real execution:** new private timeline under F:\Dev\ROMMAGE\FIXTURE\SMB3\Animations\right-8-31-*\timeline.json covering 24 contiguous video frames 448385–448408 (warmups 8–31); only six new accepted A/B/A runs; continuation.json; 24 individual RGBA PNGs and spritesheet. Use the existing offline HTML preview CLI after successful capture, and verify frame stepping, alignment, transparency and hashes. The earlier 18-frame archive and original run reports must remain byte-identical.

If a step fails, stop. Preserve incomplete private diagnostics, verify any already successful windows before resuming, and do not recapture them automatically.

## Independent Work handoff

Return: tested commit SHA; Windows/Python/Mesen versions and hashes; exact tests passed/failed/skipped; preflight and profile observations; 18-frame source revalidation; new A/B/A validations; 24-frame timeline and SHA; exact visual holds, tile IDs, X/Y origins, first new transition; background and priority caveats; continuation receipt; private report ZIP with timeline, frames and evidence if possible. Never claim a complete walk loop without supporting captures. Do not merge PR #19 or modify code to hide failures. The owner returns the report to the original ChatGPT chat for technical analysis.