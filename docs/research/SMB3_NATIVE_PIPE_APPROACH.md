# World 1-1 screen-8 native approach

The recorded controller replay reached screen 8 from the existing private
World 1-1 slot. The Down attempt began at poll 1152, frame 449467, CPU cycle
13385319850. Mario stopped at world (2272, 336). Pipe movement and junction
flags stayed zero. The observed $77 mask count for OAM slots 0–3 was zero
across 72 start/end snapshots. This is a blocked approach.

The 432-byte screen-8 checkpoint snapshot has SHA-256
2350433e1fd9a54b7a1ae7c90390d4520974a70ce7b615034a5d07def16cedc4.
At columns 141–142, it contains $AD/$AE at row 7 and $79/$79 at both rows 19
and 23. The lower apparent entrances are blocked. The relevant alternate-level
entry is the upper row-7 mouth. The small-Mario route reached the lower
platform. An authentic upper approach still needs a flight-capable or other
legitimately reached route.

## Repeat on Windows

The following generates the verified 1,350 poll bytes, SHA-256
00f4e5ba1e6eae96529a5f965282a25f0d2890c735a277054efe5fd7887bed4d.
Each byte is a controller mask, with Right=1, Down=4, A=16 and B=32.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$env:PYTHONPATH = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\src'
$fixture = 'F:\Dev\ROMMAGE\FIXTURE\SMB3'
$source = Join-Path $fixture 'GraphicsValidation\anim-right-w8-extakxfv'
$env:SPRITEMINE_PIPE_ROUTE = Join-Path $fixture ('RuntimeInvestigation\screen8-input-' + [guid]::NewGuid().ToString('N') + '.bin')
@'
from pathlib import Path
import hashlib
import os

def mask(poll):
    if poll <= 60:
        return 0
    if poll >= 1152:
        return 36
    if 735 <= poll < 775:
        return 33
    t = poll - 40 if poll >= 775 else poll
    if t < 370:
        jump = (t - 61) % 24 < 15
    elif t < 770:
        jump = (t - 370) % 26 < 18
    else:
        jump = (t - 760) % 26 < 18
    return 33 + 16 * jump

data = bytes(map(mask, range(1, 1351)))
assert hashlib.sha256(data).hexdigest() == "00f4e5ba1e6eae96529a5f965282a25f0d2890c735a277054efe5fd7887bed4d"
Path(os.environ["SPRITEMINE_PIPE_ROUTE"]).write_bytes(data)
'@ | python -
if ($LASTEXITCODE -ne 0) { throw 'Input generation failed' }
python 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\research\mesence\pipe_replay.py' `
  --root 'F:\Dev\ROMMAGE' `
  --rom (Join-Path $source 'replay.nes') `
  --slot (Join-Path $source 'slot-copy.mss') `
  --emulator (Join-Path $fixture 'EmulatorRuntime\mesence-8ef403d6b9af3207-a76dbd831587ce04\Mesen.exe') `
  --input $env:SPRITEMINE_PIPE_ROUTE --first 449458 --last 449493
```

A/B/A matched controller-bus and boundary traces, start/end logical snapshots,
and filtered RGB. Detailed leg B collects hardware and shadow OAM, PPU memory
and state, palette, mapper writes, IRQ/NMI, pipe flag writes, and a private
checkpoint at frame 449458, CPU cycle 13385054099. The checkpoint SHA-256 was
34040a291835c1f1c6209d9594babf0f690c6351640a3763cdc546040834b926.
The detailed leg also has a source/ROM-correlated hook at $89A0 for the
instruction immediately after layout construction. It did not fire on this
route. Consequently there is no bonus-room capture comparison or independent
pipe occlusion comparison yet. Boundary PPU snapshots and write timestamps
alone do not establish fetch-time CHR for every pixel.

For a future successful replay, compare the resulting 864-byte layout-complete
dump with `python -m spritemine validate-level $rom $dump`. All differences
are reported with screen, row, column, and expected and observed byte values.
