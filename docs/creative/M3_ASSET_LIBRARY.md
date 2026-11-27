# M3 private asset library — first integration slice

This is a headless index and browser preview of the existing private M1/M2
exports and the owner-approved World 1 background map test. It does not
extract new assets or claim complete SMB3 coverage. The original World 1 map
prototype remains a private extraction; its provenance manifest is retained.
Credits: Southbird SMB3 disassembly, http://www.sonicepoch.com/sm3mix/.

## Private directory contract

Create a private root under `F:\Dev\ROMMAGE\OUTPUT` (never inside Git).
Unzip the existing M1 private scene into `stage` (strip its wrapper folder),
M1 ground-actor export into `stage_export` (strip wrapper folder; frame PNGs
optional), the World 1 map pack into `map`, and M2 catalog into `audio`.
Apply the M2 naming update over `audio`. Each subdirectory must retain
its original recipe or manifest. The library does not unpack untrusted ZIPs.

From the SpriteMine checkout (Python 3.11+ with package installed):

```powershell
Set-Location "F:\Dev\ROMMAGE\SOURCE\SpriteMine"
python -m spritemine.asset_library "F:\Dev\ROMMAGE\OUTPUT\M3_Library"
```

Open `index.html` in the private root. Search names, tags, technical IDs or
source symbols, filter by type, preview graphics/animation/audio, download
original files, and expand provenance. `catalog.json` stores stable scoped IDs,
relative paths, file hashes and dimensions or PCM properties. The importer
verifies declared file hashes and rejects missing/escaping paths, duplicate
IDs, and conflicting known ROM hashes. The stage GIF provenance is inherited
from its export report, which has no direct ROM hash field. Hash checking
is integrity checking, not proof of native gameplay equivalence.

`composition.json` references two catalog IDs. It can be edited to choose a
different animation and music; rerun the command to update the preview.
Visual and audio loops run independently. To produce a finite video preview
using optional separately installed FFmpeg (must support H.264/AAC):

```powershell
Set-Location "F:\Dev\ROMMAGE\SOURCE\SpriteMine"
python -m spritemine.asset_library "F:\Dev\ROMMAGE\OUTPUT\M3_Library" --video "F:\Dev\ROMMAGE\OUTPUT\World1_Map_With_Music.mp4" --seconds 14.4
```

Video is a lossy convenience derivative at 30 fps, not a seamless joint
loop or lossless original. The source GIF/WAV remain untouched. No need to
rerender the accepted M1 or M2 assets. Metadata outputs are generated in the
private root; do not edit source manifests merely to bypass hash checks.

## First private validation

292 entries: 200 stage graphics, one stage panorama GIF, six map assets,
85 audio files. One unavailable resume request is retained as metadata.
Stage artwork has authored alignment/motion; map is background only, no
HUD or sprites, without native emulator pixel comparison. Audio has the
existing source-loop precision and clipping limitations. 14.4-second
1024x576 MP4 uses the actual World 1 map music, not Ground Theme. Full M3
acceptance requires owner review of this second composition and library,
more flexible editing/import, and Windows browser/FFmpeg testing.

Public tests use synthetic graphics/audio only. No ROM, game art, audio,
private recipes containing copyrighted content, or generated library files
are committed to public GitHub.
