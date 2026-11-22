# SMB3 PRG1 — Native bonus-room background RGB gate

**2026-11-22 acceptance: PASS for the bounded World 1-1 bonus gameplay background — original-ROM private archive and owner's Windows execution of the committed verifier agree. PR #25 remains draft and unmerged pending integration review.**

## Exact scope and baseline

The previous gate [PR #24](https://github.com/87otlto-coder/SpriteMine/pull/24) passed the owner's corrected native CLI on 2026-11-21: **51 private-ROM tests**, **64/64 source-pattern/attribute uploads**, **2,176/2,176 bytes**, **104/104 physical CIRAM frames**, **5,491 modeled nametable write requests**, **zero physical and mirroring discrepancies**. It did **not** validate visible background pixels.

New offline analysis used the existing **native A/B/A capture** `F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-xbhs6ijw` and the owner's original **USA PRG1** ROM. No MesenCE process was launched, no save state replayed, and no copyrighted graphics were added to GitHub.

For **13 consecutive native frames, 450869–450881**, the independent background model reproduced **638,976 / 638,976 exact RGB pixels (zero mismatches)** in the **256×192 gameplay region**, scanlines 0–191. The HUD/status bar (scanlines 192–239), other frames, active player/OAM composition, arbitrary scroll transitions and per-dot timing are not included in the claim.

The first, narrower check matched 47,616/47,616 pixels on frame 450880 excluding the leftmost eight columns. The expanded check includes those eight columns using the recorded PPUMASK left-edge background flag. Each of the 13 frames matches **49,152 / 49,152 pixels**. RGB was compared directly with `B/<frame>-end-rgb.bin`, not interpreted by screenshot recognition.

## Independent reconstruction inputs

- Original ROM CHR-ROM SHA-256: bound to the accepted PRG1 ROM; **pattern pixels are decoded directly from the ROM**, never copied from Mesen's PPU pattern snapshots.
- Physical **2 KiB CIRAM** from native `ppu-<frame>-start-ciram.bin`, with observed MMC3 `$A000` mirroring bit. Logical PPU nametable aliases are independently recomputed.
- MMC3 `$8000/$8001` register-write history in `B/events.tsv`: recomputes the eight physical CHR 1-KiB bank pages at every captured `start` event. For all 13 accepted frames, mapping is **[8, 9, 96, 97, 0, 4, 34, 79]**, with no changes affecting CHR during visible gameplay scanlines 0–191. The original PPU CHR debug snapshot is used as a **cross-check**, not a source for the renderer.
- NES PPU temporary scrolling register `ppu.tmpVideoRamAddr`, `ppu.xScroll`, `ppu.control.backgroundPatternAddr` and PPUMASK flags. The accepted frames start at **coarse X=1, coarse Y=29, fine Y=7**, equivalent to viewport scroll X=8 / Y=239. PPU scrolling wraps from logical nametable 0's final row into the next vertical nametable after the first screen row.
- Native per-frame **32-byte palette RAM** and background mask. Start/end palettes match in accepted frames and there are no logged palette `$2007` writes during sampled visible lines.
- An externally supplied **MesenCE 2.2.1 default 2C02 RGB profile** parsed from pinned `Core/NES/NesDefaultVideoFilter.cpp`. MesenCE is GPLv3; this source is used locally and **its table is not copied into SpriteMine's proprietary code**. The CLI reports the separately supplied source file SHA-256.

The independent renderer implements NESdev's coarse/fine scrolling, two-bank vertical nametable wrap, 16×16 attribute quadrant palette selection, hardware 2bpp CHR decoding, background index-zero backdrop and left-eight-pixel masking. It does not use screenshots to calculate its output, and does not patch emulator data.

Relevant primary references:

- [NESdev PPU scrolling](https://www.nesdev.org/wiki/PPU_scrolling)
- [NESdev PPU rendering](https://www.nesdev.org/wiki/PPU_rendering)
- [NESdev nametables](https://www.nesdev.org/wiki/PPU_nametables)
- [Pinned MesenCE MMC3 register mapping](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h)
- [Pinned MesenCE 2C02 video reference](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesDefaultVideoFilter.cpp)
- [Previous accepted native PPU/CIRAM gate](SMB3_NATIVE_PPU_CIRAM_ARCHIVE_REVALIDATION_20261121.md)

## Reproduce using only existing private files (Windows PowerShell 5.1)

This downloads **only public MesenCE GPLv3 source** to `TOOLS`; ROM and capture files remain private in `FIXTURE`. Do not add the downloaded emulator source, raw capture, palettes or game graphics to SpriteMine's public Git repository.

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $root = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation'
    $python = Join-Path $root '.venv\Scripts\python.exe'
    $rom = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
    $capture = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-xbhs6ijw'
    $mesenDir = 'F:\Dev\ROMMAGE\TOOLS\MesenCE-Source'
    $paletteSource = Join-Path $mesenDir 'NesDefaultVideoFilter-20ba206c.cpp'
    $paletteUrl = 'https://raw.githubusercontent.com/nesdev-org/MesenCE/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesDefaultVideoFilter.cpp'

    if (-not (Test-Path -LiteralPath $root)) { throw 'SpriteMine validation worktree missing.' }
    if (-not (Test-Path -LiteralPath $capture)) { throw 'Verified private replay missing.' }
    if (-not (Test-Path -LiteralPath $rom)) { throw 'Private PRG1 ROM missing.' }
    if (-not (Test-Path -LiteralPath $python)) { throw 'Project Python interpreter missing.' }

    New-Item -ItemType Directory -Force -Path $mesenDir | Out-Null
    if (-not (Test-Path -LiteralPath $paletteSource)) {
        Invoke-WebRequest -UseBasicParsing -Uri $paletteUrl -OutFile $paletteSource
    }

    Set-Location -LiteralPath $root
    if (git status --porcelain) { throw 'Validation worktree contains uncommitted changes.' }
    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed.' }
    git switch --detach origin/feature/smb3-world11-visible-background
    if ($LASTEXITCODE -ne 0) { throw 'Checkout failed.' }

    $env:PYTHONPATH = Join-Path $root 'src'
    $env:SPRITEMINE_TEST_ROM = $rom

    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed.' }

    $lines = & $python (Join-Path $root 'research\mesence\verify_visible_background.py') $rom $capture $paletteSource
    $resultCode = $LASTEXITCODE
    if (-not $lines) { throw 'Visible background verifier produced no JSON.' }
    $json = $lines -join "`n"
    $result = $json | ConvertFrom-Json
    $reportFile = Join-Path $capture 'visible-background-verification.json'
    $json | Set-Content -LiteralPath $reportFile -Encoding UTF8
    $result | Select-Object passed, scope, sampled_frames, compared_pixels, mismatches
    Write-Host "Report: $reportFile"
    if ($resultCode -ne 0 -or $result.passed -ne $true) {
        throw 'Background RGB did not pass. Preserve the private diagnostics.'
    }
}
~~~

Expected result if the committed model matches the independent prototype:
**13 frames × 49,152 = 638,976 compared pixels, 0 differences**. The private Windows CLI result is **not** represented as having happened until its output is supplied. No new emulator replay is needed.

## Accepted owner Windows verification — 2026-11-22

The owner ran the committed `feature/smb3-world11-visible-background`
at exact commit `a4624992cb7915945de46e855fd3cdcd98bf3b56` on Windows
PowerShell 5.1. The clean validation worktree
`F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation` executed
**61 passed, 0 failed, 0 skipped** local private-ROM pytest tests in
1.33 seconds.

The owner then invoked `verify_visible_background.py` against the
existing preserved private native A/B/A replay and pinned local MesenCE
default 2C02 palette source. The **official verifier returned**
`passed: true`, **`sampled_frames: 13`**,
**`compared_pixels: 638976`**, and **`mismatches: 0`**.

Exact accepted frame subset: **450869–450881**, inclusive;
**256 × 192** gameplay pixels per frame. Native report is stored privately:
`F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-xbhs6ijw\visible-background-verification.json`.
The owner's console output establishes these results. The private
JSON, ROM, captured RGB, PPU state, and third-party palette source
are **not** committed to the public repository.

This result is a real end-to-end **original-ROM CHR + MMC3 register-derived
CHR mapping + physical CIRAM + scroll + palette → exact native RGB**
acceptance for the stated viewport. It is **not** a claim of sprite
composition, HUD scanlines 192–239, within-scanline PPU cycle timing,
other level sections, or full application functionality.

Hosted [Windows CI run 44959428665](https://github.com/87otlto-coder/SpriteMine/actions/runs/44959428665)
also passed Python 3.11 and 3.12, **57 public tests passed / 4
private-fixture skips per version**. Hosted CI is not the native
emulator evidence; the owner's preserved private replay provides that.

The CLI run described in the preceding reproduction block has now been
executed successfully; the block remains a reproducibility recipe.

## Explicit remaining gates

1. Complete HUD rendering: IRQ-switched MMC3 CHR, scroll/nametable state and pixels at scanlines 192–239.
2. Validate sprite/OAM occlusion and blending against the reconstructed background where sprites are visible; avoid counting invisible/ambiguous sprites.
3. Generalize only to the *main World 1-1 level*, with deterministic scrolling and level generator state, then show a usable Qt inspector/export flow.
4. Review/merge existing stacked PRs and native CHR browser PR #4 after tests; do not mark unmerged research as finished product functionality.

No audio, other NES games or speculative whole-ROM recognition is part of this increment.
