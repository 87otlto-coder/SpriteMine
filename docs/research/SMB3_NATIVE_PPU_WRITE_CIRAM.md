# SMB3 PRG1 — Native PPU register and CIRAM verification

**Current status: implemented; native Windows acceptance pending.** This is PR #24, stacked on accepted CPU staging PR #23. The prior native result was 2,176/2,176 CPU staging bytes, not PPU output.

## Source-grounded instrumentation

Pinned MesenCE 2.2.1 source: https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/NesPpu.cpp

CPU writes to $2007 are latched and applied several PPU cycles later, not immediately. On the ordinary nametable data write path the mapper's WriteVram is used **without** ProcessPpuWrite; that callback is invoked for palette writes. Therefore monitoring the Lua NesPpuMemory write callback cannot prove normal nametable writes.

Instead, PR #24 passively records CPU $2000/$2005/$2006/$2007 writes with MesenCE prewrite state fields, and $2002 status reads. It also captures Mesen's physical 2 KiB NesNametableRam at frame start/end, and the PPU debug nametable view. MMC3 register $A000 supplies the actual mirroring bit; 0 means vertical and 1 means horizontal mirroring. The source-proven state field names are derived from Serializer NormalizeName.

The Python verifier checks that 54-byte and 14-byte first-entry bonus-room producer buffers correspond to CPU $2007 write sequences at exact PPU addresses (30+24 and 8+6), then independently reconstructs physical nametable RAM and tests every PPU nametable alias against the physical bytes.

Potentially unsafe on-screen, frame-edge or bus-address-inconsistent writes are NOT automatically accepted. Only the owner can establish native results by running the deterministic private replay. Source code, tests and documentation must remain public-data-only.

## Windows PowerShell reproduction

~~~powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation'
$root = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation'
$python = Join-Path $root '.venv\Scripts\python.exe'
$fixture = 'F:\Dev\ROMMAGE\FIXTURE\SMB3'
$source = Join-Path $fixture 'GraphicsValidation\anim-right-w8-extakxfv'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
$env:PYTHONPATH = Join-Path $root 'src'
$env:SPRITEMINE_TEST_ROM = $rom

if (git status --porcelain) { throw 'Preserve validation checkout changes before switching.' }
git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed.' }
git switch --detach origin/feature/smb3-world11-ppu-write-trace
if ($LASTEXITCODE -ne 0) { throw 'Branch switch failed.' }

& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Regression suite failed.' }

$inputFile = Join-Path $fixture 'RuntimeInvestigation\world11-raccoon-controller-2590.bin'
& $python (Join-Path $root 'research\mesence\raccoon_route.py') --output $inputFile
if ($LASTEXITCODE -ne 0) { throw 'Controller hash verification failed.' }

$replayText = (& $python (Join-Path $root 'research\mesence\pipe_replay.py') `
    --root 'F:\Dev\ROMMAGE' `
    --rom (Join-Path $source 'replay.nes') `
    --slot (Join-Path $source 'slot-copy.mss') `
    --emulator (Join-Path $fixture 'EmulatorRuntime\mesence-8ef403d6b9af3207-a76dbd831587ce04\Mesen.exe') `
    --input $inputFile --events --background-staging --ppu-commits) -join "`n"
if ($LASTEXITCODE -ne 0) { throw 'Native replay failed; preserve private capture.' }
$report = $replayText | ConvertFrom-Json
$report | Select-Object capture_dir, neutral, frame_range, ppu_register_trace

& $python (Join-Path $root 'research\mesence\verify_ppu_commit_trace.py') $rom $report.capture_dir |
    Set-Content -LiteralPath (Join-Path $report.capture_dir 'ppu-verification.json') -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'Native PPU/CIRAM acceptance incomplete or failed.' }
$verification = Get-Content -LiteralPath (Join-Path $report.capture_dir 'ppu-verification.json') -Raw | ConvertFrom-Json
$verification | Select-Object passed, scope, memory, native_final_rgb_or_fetch_time_chr_verified
~~~

Private capture location is returned as capture_dir. Send the compact verifier summary, NOT the ROM or raw graphics. The original SpriteMine checkout on F: is not modified.

## Acceptance and limitations

A pass requires A/B/A neutrality, source hash integrity, accepted CPU staging, matched pattern and attribute bus write sequences, and 0 mismatches between modeled and captured physical CIRAM plus its PPU debug aliases. Every excluded or unmatched event must be counted; no silent positive coverage. Even then, rendered RGB, HUD IRQ fetch-time CHR mapping, palette timing and complete World 1-1 pixel reconstruction remain **unverified**.
