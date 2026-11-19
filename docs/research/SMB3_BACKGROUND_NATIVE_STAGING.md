# SMB3 PRG1 — Native World 1-1 bonus PPU staging acceptance

**Status:** native first-entry bonus CPU staging **PASSED on owner's Windows replay (2026-11-19)**: 32 × 54-byte pattern and 32 × 14-byte attribute strips; 2,176 bytes matched, zero differences, two events excluded. Final PPU and RGB remain unverified. See [the evidence checkpoint](SMB3_BACKGROUND_NATIVE_STAGING_ACCEPTANCE_20261119.md).

This is a focused follow-up to the verified 2,590-poll Raccoon Mario route in
[SMB3_NATIVE_RACCOON_PIPE.md](SMB3_NATIVE_RACCOON_PIPE.md) and the static
World 1-1 bonus-room background model.

## Capture points and neutrality

SMB3 computes 54 8x8 pattern bytes and 14 PPU attribute bytes in CPU staging
RAM before committing them to PPU VRAM. End-frame snapshots do not establish
these producer-buffer bytes or their update order.

The optional **read-only** Lua observer is appended as one chunk to the
original pipe replay script. Only leg B produces additional evidence.
The standard A/B/A legs still compare controller, timing, Tile_Mem and RGB
evidence, and any divergence fails the capture.

The two producer completion triggers are:

- Pattern: writing $20 to Scroll_ToVRAMHi ($0380), after constructing 54
  Scroll_PatStrip bytes ($0382-$03B7).
- Attribute: writing $23 to Scroll_ToVRAMHA ($03B8), then clearing
  Scroll_UpdAttrFlag ($0707), after the 14 Scroll_AttrStrip bytes
  ($03BA-$03C7) and Scroll_LastAttr are ready.

MesenCE memory-write callbacks run **before** the write. The probe defers
capturing to the next CPU execute callback, returns nil, and never changes
gameplay. The capture stores source columns, direction, 8-pixel half, PPU
destinations, frame/cycle timestamps, and private 864-byte logical Tile_Mem
snapshots, with a maximum of 256 producer events.

PRG030 can select nonadjacent attribute source columns across scroll-screen
boundaries. The verifier reproduces these selections instead of assuming
all attributes use an even column and its immediate right neighbor.

Authority: original Southbird PRG030 and smb3.asm at pinned commit
09b1bd81a788de8ceec664a34094e84ddb463117; MesenCE 2.2.1 pinned at
20ba206cef5ba207c21203176d02cb9f43dda9fb.

## Windows reproduction

Use the clean Background-Validation worktree; the original SpriteMine checkout
has research modifications that should not be discarded.

~~~powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation'
$root = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation'
$python = Join-Path $root '.venv\Scripts\python.exe'
$fixture = 'F:\Dev\ROMMAGE\FIXTURE\SMB3'
$source = Join-Path $fixture 'GraphicsValidation\anim-right-w8-extakxfv'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
$env:PYTHONPATH = Join-Path $root 'src'
$env:SPRITEMINE_TEST_ROM = $rom

if (git status --porcelain) { throw 'Worktree has local edits; stop before switching.' }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed.' }
git switch --detach origin/feature/smb3-world11-staging-capture
if ($LASTEXITCODE -ne 0) { throw 'Could not switch to staging branch.' }

& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Regression suite failed.' }

$inputFile = Join-Path $fixture 'RuntimeInvestigation\world11-raccoon-controller-2590.bin'
& $python 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation\research\mesence\raccoon_route.py' --output $inputFile
if ($LASTEXITCODE -ne 0) { throw 'Raccoon input verification failed.' }

& $python 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation\research\mesence\pipe_replay.py' --root 'F:\Dev\ROMMAGE' --rom (Join-Path $source 'replay.nes') --slot (Join-Path $source 'slot-copy.mss') --emulator (Join-Path $fixture 'EmulatorRuntime\mesence-8ef403d6b9af3207-a76dbd831587ce04\Mesen.exe') --input $inputFile --events --background-staging
if ($LASTEXITCODE -ne 0) { throw 'Native A/B/A capture failed; retain its private logs.' }
~~~

Copy the capture_dir path from the successful JSON output. Run:

~~~powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation'
$python = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation\.venv\Scripts\python.exe'
$env:PYTHONPATH = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation\src'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
$capture = Read-Host 'Paste capture_dir from the successful replay report'
& $python 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation\research\mesence\verify_background_staging.py' $rom $capture
if ($LASTEXITCODE -ne 0) { throw 'Native staging acceptance not yet passed.' }
~~~

## Acceptance scope

- Verified original ROM and immutable replay source fingerprints.
- A/B/A comparison passes with the passive observer active only in B.
- Log SHA-256 and event count match the capture manifest.
- At least one matching native pattern and one matching native attribute
  producer event use the original **first-entry bonus logical map**.
- Every checked CPU staging byte and destination metadata value matches.

Out-of-model columns, missing producer events and modified logical maps are
not silently counted as successful comparisons. A byte mismatch remains
reported with frame, CPU cycle and index.

**Passing this gate does not validate final VRAM state, fetch-time CHR mapping,
palette RGB or the visible background framebuffer.** Those are separate gates.
No copyrighted ROM, capture, screenshot or save-state data belongs in GitHub.
