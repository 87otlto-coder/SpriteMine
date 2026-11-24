# M2 — isolated SMB3 sound engine playback

## Goal and verified scope

This path addresses the owner's rejection of mixed gameplay captures and approximate loop cuts. It runs original music/SFX code from the verified USA PRG1 ROM with Game Music Emu (GME), using a small independently written NSF adapter. It does not download an existing NSF or include game code/data in the repository. The original ROM is immutable. The NSF exists only in memory; private WAV exports must never be committed or redistributed. This is original-code emulation, not independent decoding of the song bytecode or exact reproduction of every APU state.

The Southbird SMB3 disassembly (pinned commit `09b1bd81a788de8ceec664a34094e84ddb463117`, [project](https://github.com/captainsouthbird/smb3), [author](http://www.sonicepoch.com/sm3mix/)) is the research reference. Credit to Southbird for documenting the sound engine; no disassembly source is incorporated.

* `PRG/prg031.asm`: native NMI routine maps banks 28 and 29 at $A000 and $C000 and invokes `Sound_Engine_Begin` at $A000. Bank 31 is fixed at $E000. The NSF adapter maps exactly these three original 8 KiB banks and puts a minimal init/play driver at $8000.
* `PRG/prg028.asm`: sound routine processes individual sound/music queues and clears them after consumption. The init driver queues exactly one track/event, with no gameplay loop. The native music routine remains responsible for instruments, segment progression, tempo, and DMC notes.
* `PRG/levels/Plains/1-1.asm` and `1-1Bonus.asm`: identify Overworld and Underground as the corresponding BGM selections. Queue addresses confirmed in original ROM code: music $04F5, level effects $04F2. Select Overworld $10, Underground $20, coin $01 respectively.
* Source music tables at CPU $B530/$B53C/$B548 supply segment start/end/loop indexes. `Music_NextIndex` is $04DF; `Music_Sq2TrkOff` is $04FE; loop index is $7AE2. Source loop indexing is one ahead. A separate diagnostic adapter calls the same native routine, observes its state, and emits a pulse marker on loop-segment entry. It uses offset reset to detect the single-segment Underground loop. This diagnostic audio is NEVER mixed into the normal output.

## Windows reproduction

Requirements: Python 3.11/3.12, verified PRG1 ROM, and a compatible external shared library from [Game Music Emu](https://github.com/libgme/game-music-emu). The local private integration was tested with libgme 0.6.3 (Debian package 0.6.3-7+b2); Windows DLL integration remains to be validated. GME is a separately installed LGPL library; do not vendor it, its source, or any NSF rip into SpriteMine. For Windows obtain/build a compatible DLL from the official [releases](https://github.com/libgme/game-music-emu/releases), with the C API and correct process architecture, or build its CMake shared-library target using an installed Visual Studio toolchain. Keep it under TOOLS. Retain its upstream license and required notices for any future redistribution. No new mandatory Python dependency.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Super Mario Bros. 3.zip'
$dll = 'F:\Dev\ROMMAGE\TOOLS\GameMusicEmu\gme.dll'
# Change the two paths to the actual existing ROM and installed DLL if needed.
if (!(Test-Path -LiteralPath $rom)) { throw 'Set $rom to the verified private ROM ZIP' }
if (!(Test-Path -LiteralPath $dll)) { throw 'Set $dll to the installed Game Music Emu DLL' }
$out = Join-Path 'F:\Dev\ROMMAGE\OUTPUT\SMB3' ('IsolatedAudio-' + [guid]::NewGuid())
$env:PYTHONPATH = 'src'
python -m spritemine.smb3_audio $rom $out --gme $dll
if ($LASTEXITCODE -ne 0) { throw 'Audio export failed' }
Get-ChildItem -LiteralPath $out
```

Expected: four stereo PCM16 48 kHz WAVs (Overworld with intro, Overworld loop, Underground loop, isolated coin) and a JSON manifest. No gameplay recording or original graphics capture is required. Unsupported ROM revisions fail closed. Output directory must be new.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$env:PYTHONPATH = 'src'
python -m pytest -q tests/test_smb3_audio.py
# Optional private native-audio regression; use the actual paths above.
$env:SPRITEMINE_PRIVATE_ROM_ZIP = $rom
$env:SPRITEMINE_GME_LIBRARY = $dll
python -m pytest -q tests/test_smb3_audio.py
```

## Private verification (2026-11-24)

12 synthetic tests passed. With the owner's original ROM and local GME 0.6.3, 13 tests passed, including two independent complete exports with identical bytes and manifests.

| Track | Native-state diagnostic marker times (seconds) | Recurrence (inferred engine ticks) | Exported repeating region |
| --- | --- | --- | --- |
| Overworld | 3.212, 28.776, 54.338, 79.902 | 1536 | 25.562 s |
| Underground | 0.016, 19.190, 38.362, 57.534, 76.706 | 1152 | 19.172 s |
| Coin | one isolated effect request | non-looping | 1.000 s incl. decay |

Markers are detected at 2 ms resolution from an independently instrumented playback; intervals must agree and correspond to the expected source tick counts. Cut points are 8 ms before the second and third markers. The first Overworld marker is after an intro. GME's sample scheduling and analog/filter state mean this is **source-state-anchored music looping**, not proof of identical full APU states or mathematically seamless PCM joins. No crossfade, tempo edit, gameplay audio, or waveform-based loop guessing is applied. Manifest counts full-scale samples rather than hiding them: observed zero in Overworld loop and coin, 42 in Overworld intro and 10 in Underground loop. Audible QA and evaluation of these occasional full-scale peaks remain open. GME DLL/version can change exact PCM and diagnostic timing; public CI uses only synthetic tests and doesn't require GME or a ROM.

Future: validate the actual Windows GME DLL, owner listening QA, optionally exact sample loop metadata and per-channel stems. Do not mark M2 accepted merely because the export is reproducible. The previous capture editor remains useful for WAV preview/edit and genuine captures. No further attempts to isolate music from mixed gameplay recordings unless explicitly requested.
