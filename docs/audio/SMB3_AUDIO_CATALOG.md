# M2 — isolated SMB3 audio request catalog

The owner approved the first isolated Overworld/Underground/coin renders on 2026-11-24. This extension enumerates the documented sound queue requests from Southbird's pinned SMB3 disassembly (see `smb3_audio.SOURCE_REF` and the isolated audio runbook). It executes the immutable verified USA PRG1 ROM with a private in-memory NSF adapter through separately installed Game Music Emu. It does not copy third-party source or distribute ROM, NSF, GME binaries or exported game audio in the public repository.

## Scope and coverage

- 27 music set-2 request IDs (15 set 2A and 12 set 2B), 7 music-set-1 jingle IDs (excluding stop), and 33 named sound-effect requests. These are **67 distinct queue/value pairs**, not 67 necessarily distinct sounds or exhaustive game audio.
- Every music request returned recurring loop-segment markers in isolated playback. The ending needed the longer 300-second diagnostic window. The export retains one measured repeat region, plus initial playback through the selected repeat boundary for songs with a delayed initial loop marker. The marker detector resolves events to 2 ms and uses 8 ms pre-roll; this does not prove exact APU phase continuity. No editorial crossfade is added. Loop metadata includes sample counts, observed markers and inferred game ticks. Listen before calling a loop musically accepted.
- All 7 jingle and 32/33 effect requests produced audio. The standalone resume request was silent, as expected for an effect requiring paused state; no silent WAV was labeled as a sound. P-meter ringing, time warning, other stateful requests and the three special Level 1 requests are context-dependent previews. Effect/jingle tail trimming is amplitude-based (threshold 64 PCM units, 200 ms tail), not native completion detection. P-Switch and Toad House produced byte-identical loop files in the isolated test, consistent with shared segment tables; no uniqueness or context-equivalence claim.
- Optional solo exports use GME voice mute masks. The tested NSF presents voices `Square 1`, `Square 2`, `Triangle`, `Noise`, `DMC` in that order. A solo render is not a separated recording or a guaranteed additive stem because mixing/filtering can be nonlinear.

## Windows reproduction

Use an installed Python environment for the SpriteMine repository and the same verified PRG1 ZIP. The external GME DLL must match Python's architecture and include the NSF backend; follow the isolated audio runbook for obtaining/building GME. The following commands deliberately require a unique matching ROM and a real external DLL path. They do not download anything, overwrite existing exports or modify the ROM.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
python -m pip install -e '.[dev]'
$matches = @(Get-ChildItem -LiteralPath 'F:\Dev\ROMMAGE\FIXTURE' -Recurse -File -Filter 'Super Mario Bros. 3.zip')
if ($matches.Count -ne 1) { throw 'Locate the unique verified SMB3 PRG1 ZIP under FIXTURE.' }
$rom = $matches[0].FullName
$gme = Read-Host 'Enter the absolute path to the separately installed GME DLL'
if (-not (Test-Path -LiteralPath $gme -PathType Leaf)) { throw 'GME DLL not found.' }
$output = Join-Path 'F:\Dev\ROMMAGE\OUTPUT' ('SMB3-Audio-Catalog-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
python -m spritemine.audio_catalog $rom $output --gme $gme --stems overworld underground
if ($LASTEXITCODE -ne 0) { throw 'Catalog export failed.' }
Start-Process (Join-Path $output 'index.html')
```

Expected: local `index.html`, `manifest.json` and 85 WAVs for the tested PRG1/GME 0.6.3 configuration (75 primary exports and ten solo voice files). Use `--only overworld underground coin` for a bounded smoke test. `--stems` is optional and accepts names of music requests. A fresh output directory is required. Synthetic tests need neither GME nor a ROM. To run the private smoke tests, set the two environment variables before pytest:

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$env:SPRITEMINE_PRIVATE_ROM_ZIP = $rom
$env:SPRITEMINE_GME_LIBRARY = $gme
python -m pytest -q tests/test_smb3_audio.py tests/test_audio_catalog.py
if ($LASTEXITCODE -ne 0) { throw 'Audio checks failed.' }
```

## Verification on 2026-11-27

GME 0.6.3 on the private development environment: all 75 primary WAV hashes matched across independent builds; 85 WAV metadata/manifest hash checks passed including ten solo exports. The private subset test repeats the selected music/effect exports and Overworld solo files. Eighteen combined local audio tests passed (including two private tests). Twelve primary WAVs contain a total of 342 full-scale PCM samples; the exporter reports these instead of normalizing or hiding them. Windows native DLL playback and per-asset listening review remain outstanding. Do not publish generated audio, the ROM, or private metadata/outputs in GitHub. M2 is still open pending final owner acceptance.


## Presentation names and owner review

The owner approved the expanded catalog on 2026-11-27 and flagged the ambiguous
Overworld label. The original `MUS2B_OVERWORLD` ($04F5/$10) is the Ground Theme
used by World 1-1; `MUS2A_WORLD1` ($04F5/$01) is the World 1 map theme.
`MUS2B_UNDERGROUND` ($20) is used by the World 1-1 bonus room. See the pinned
Southbird `PRG/levels/Plains/1-1.asm` and `1-1Bonus.asm` level headers and
`smb3.asm` music constants. All 27 music request entries now include
`display_name` and `source_symbol`. Stable `name`, queue/value, filenames,
loop data and WAV hashes are unchanged. An existing catalog can be upgraded
using `apply_presentation_metadata` and `make_index` without re-rendering.
Owner approval covers the creative usefulness of the library, not exhaustive
per-asset listening, exact APU state continuity or native Windows DLL playback.
