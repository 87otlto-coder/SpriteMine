# PR #19: canonical FIXTURE promotion for six complete private A/B/A captures

**Prepared November 13, 2026; not executed.** SMB3 US PRG1 only. This is a local, controlled evidence-copy step, not a new ROM extraction or animation observation. Never commit source ROMs, save states, captures, settings, or generated game graphics.

## Reason and boundaries

Work independently revalidated 18 private A/B/A capture windows. Existing canonical F: warmups 8–19 matched the private source across 948 files. Warmups 20–25 were absent, and Work's F: mount was read-only.

IMPORTANT: The earlier private sharing ZIP contains only 77 files per run. It excludes replay.nes and slot-copy.mss. The complete original private capture directories have 79 files each. Do not extract the stripped sharing ZIP into the canonical fixture or recreate the missing bytes.

The new Python helper research.mesence.promote_private_runs checks the original timeline SHA-256, revalidates all 18 source captures, checks every source and existing canonical run's 79-file manifest and ROM/state hashes, and refuses mismatches before copying. By default it only checks. Explicit --apply stages and re-hashes the six missing full captures under FIXTURE/SMB3/TransferStaging before promotion. The original source timeline and source runs are never modified. The helper revalidates all 18 canonical runs once promotion completes.

Original timeline SHA-256: 1e48bf12926edcb80e451154c4e1a7aa809480d9467e313c2ea460a452eba1eb

## Owner Windows PowerShell: read-only preflight

Run on a Windows session that can read the original complete private C: source and can write F:. Work's current read-only F: session cannot perform the later --apply step.

~~~powershell
$repo = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics'
Set-Location -LiteralPath $repo
if (git status --porcelain) { throw 'Preserve local changes before switching branches' }
git fetch origin 'refs/heads/research/smb3-long-animation-resume:refs/remotes/origin/research/smb3-long-animation-resume'
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
if (git branch --list 'research/smb3-long-animation-resume') {
    git switch 'research/smb3-long-animation-resume'
} else {
    git switch --track 'origin/research/smb3-long-animation-resume'
}
if ($LASTEXITCODE -ne 0) { throw 'Branch switch failed' }
git pull --ff-only origin research/smb3-long-animation-resume
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }
$python = Join-Path $repo '.venv\Scripts\python.exe'
$old = 'C:\Users\87otl\Documents\ChatGPT\SpriteMine\PR19-private\FIXTURE\SMB3\Animations\right-8-25-bad20ce00c\timeline.json'
if (-not (Test-Path -LiteralPath $python)) { throw 'Research Python venv missing' }
if (-not (Test-Path -LiteralPath $old)) {
    throw 'Private COMPLETE timeline unavailable; do not use the stripped sharing ZIP'
}
& $python -m research.mesence.promote_private_runs --timeline $old --target-root 'F:\Dev\ROMMAGE'
if ($LASTEXITCODE -ne 0) { throw 'Private evidence preflight failed; do not apply' }
~~~

The recorded C: path is historical. If it no longer exists, locate the ORIGINAL complete 79-file capture tree under private FIXTURE, not the 77-file sharing ZIP.

Expected read-only result: ready_for_explicit_write, 18 verified original windows, 12 identical canonical source runs, six missing names for warmups 20–25, and 79 files per capture. No writes occur.

## Explicit promotion, only after matching preflight

~~~powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics'
$python = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\.venv\Scripts\python.exe'
$old = 'C:\Users\87otl\Documents\ChatGPT\SpriteMine\PR19-private\FIXTURE\SMB3\Animations\right-8-25-bad20ce00c\timeline.json'
& $python -m research.mesence.promote_private_runs --timeline $old --target-root 'F:\Dev\ROMMAGE' --apply
if ($LASTEXITCODE -ne 0) { throw 'Promotion failed; preserve private staging evidence' }
& $python -m research.mesence.promote_private_runs --timeline $old --target-root 'F:\Dev\ROMMAGE'
if ($LASTEXITCODE -ne 0) { throw 'Read-only postflight failed' }
~~~

Expected apply: promoted_and_reverified, six newly promoted complete run directories, 18 independently revalidated canonical source windows. Subsequent read-only postflight should show 18 identical canonical runs and zero missing runs. On a failure, do not delete or overwrite original or partially staged captures to force a pass.

## Remaining test requirements

Work must first test the new helper on Windows (synthetic tests plus source read-only preflight). If Work continues to have read-only F: access, the owner must execute the explicit promotion step on a Windows session with the necessary permissions. Work cannot launch new captures into canonical F: until that access limitation is resolved. The next bounded real experiment remains warmups 26–31, potentially producing 24 consecutive emulator frames 448385–448408. Do not claim any newly observed Mario pose or full animation loop until the emulator experiment and private validation actually succeed.
