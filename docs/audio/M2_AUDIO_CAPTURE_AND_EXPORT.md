# SpriteMine M2 — captured music and SFX to WAV (first production pass)

**Status: editor implemented; owner listening acceptance and clean isolated capture remain open.** SMB3 USA PRG1 / Revision A only. This feature is a **capture-based editor**, not an NSF/music sequence decoder or an APU emulator.

## Scope and evidence

- The CLI accepts one existing **signed PCM16 WAV** recording without other tools. For recorded MP4/AAC or other containers it can optionally call `ffmpeg` to decode to 48 kHz stereo signed PCM16 WAV first. Compressed-source conversion is **not lossless extraction of original NES samples**.
- A versioned JSON recipe selects named sound clips, source sample spans, category (`music`, `sfx`), optional fades, optional seamless **sample-level** loop crossfade. It writes trimmed 16-bit PCM WAV and manifest with SHA-256 source/output checksums, capture label and sample counts.
- The loop overlap prevents the **splice** from introducing a new waveform discontinuity. It **does not discover a musical phrase boundary** or remove concurrent game effects. Mark captured, decoded and edited provenance accurately.
- The first private fixture comes from an **owner-supplied, 23.232-second MesenCE H.264/AAC gameplay recording**. It yielded a bonus-room loop candidate (6.10s), a main-stage loop candidate (3.27s), and a goal-card pickup audio clip (1.45s); 48 kHz stereo. The music and event audios remain a *mixed gameplay capture*; the three clips are not isolated clean song/SFX stems. Source and all derived audio must remain in private `FIXTURE`/`OUTPUT`, never public GitHub.
- Synthetic local tests and Windows CI verify decoding/export format, exact sample trimming, looping, error handling and reproducibility. They do **not** prove the audio sounds good. Owner playback review and a **direct MesenCE WAV capture** are the next quality gate.

## Windows folders

Use only the canonical `F:\Dev\ROMMAGE` workspace:

- `SOURCE\SpriteMine` — this program, tests and docs.
- `TOOLS` — existing MesenCE installation, optionally `ffmpeg.exe`.
- `FIXTURE\SMB3\Audio` — read-only originals: WAV / gameplay movie, save state, game input logs, JSON recipes (private).
- `OUTPUT\SMB3\Audio` — exported WAVs and manifests (private).
- `REPORTS\SMB3\Audio` — private listening notes and validation evidence.

Do not copy the copyrighted ROM, captured audio, or exported effects into `SOURCE` or a public GitHub branch.

## Native MesenCE WAV capture (recommended over MP4/AAC)

1. Open the verified SMB3 US PRG1 ROM in **MesenCE 2.2.1** on the Windows PC. Use an existing, verified save state if it makes reaching the sound easier. Keep original ROM and state immutable.
2. Use MesenCE's **Tools → Sound Recorder** (or the equivalent WAV recording option in that installation) to begin **WAV** recording, play the desired portion, then stop. If menu labels differ, check the installed MesenCE build; this procedure has not yet been exercised on the owner's Windows instance.
3. For a clean *music* take, allow the desired soundtrack to run for at least one full musical phrase while minimizing movement, jumps, coins and other game effects. For an *SFX* take, start from a documented state and trigger the effect once; background music may still be present unless genuinely separated by the emulator.
4. Save to `F:\Dev\ROMMAGE\FIXTURE\SMB3\Audio\MesenCE_World11_Music.wav` (or `MesenCE_World11_SFX.wav`). Log the ROM SHA-256, emulator version, save-state hash, input sequence, start/end game frames, recording sample rate, and emulator audio settings. Do not claim "isolated" if another APU sound was audible during capture.
5. Use the editor below to select/loop and export. Inspect WAV playback on Windows headphones or speakers, revise the recipe for sensible musical boundaries, and record notes under `REPORTS`.

## Example editor run — PowerShell (Windows)

```powershell
$root = 'F:\Dev\ROMMAGE'
Set-Location -LiteralPath (Join-Path $root 'SOURCE\SpriteMine')
python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { throw 'SpriteMine Python installation failed' }

$fixture = Join-Path $root 'FIXTURE\SMB3\Audio'
$output = Join-Path $root 'OUTPUT\SMB3\Audio\M2_World11'
New-Item -ItemType Directory -Force -Path $fixture, $output | Out-Null

# Replace time markers below after listening to your native WAV recording.
$recipe = @'
{
  "version": 1,
  "source_kind": "captured",
  "source_context": "MesenCE 2.2.1; SMB3 USA PRG1; original WAV capture",
  "source_disclaimer": "Capture can contain effects over music until independently isolated",
  "exports": [
    {"name":"world11_music_loop", "kind":"music", "start_s":2.0, "end_s":12.0, "loop":true, "crossfade_ms":100},
    {"name":"world11_sfx_excerpt", "kind":"sfx", "start_s":13.0, "end_s":14.0, "fade_in_ms":10, "fade_out_ms":15}
  ]
}
'@
$recipeFile = Join-Path $fixture 'm2_world11_recipe.json'
[System.IO.File]::WriteAllText($recipeFile, $recipe, [System.Text.UTF8Encoding]::new($false))

$sourceWav = Join-Path $fixture 'MesenCE_World11_Audio.wav'
if (!(Test-Path -LiteralPath $sourceWav -PathType Leaf)) { throw "MesenCE capture missing: $sourceWav" }
python -m spritemine.audio_export $sourceWav $recipeFile $output
if ($LASTEXITCODE -ne 0) { throw 'Audio export failed' }
python -m pytest -q tests/test_audio_export.py
if ($LASTEXITCODE -ne 0) { throw 'Audio regression tests failed' }
Get-ChildItem -LiteralPath $output -File | Select-Object Name, Length
```

**Expected:** two actual playable WAV files plus `manifest.json`, with the configured sample spans and output hashes. The example timestamps are placeholders: never treat them as observed SMB3 musical loop or effect timestamps. Native MesenCE capture may need conversion if it is not PCM16 WAV. If importing MP4, `ffmpeg` must be installed and on `PATH`.

## Reproducibility and limits

- The source is only **read**, never edited or overwritten.
- Export names are constrained to simple filenames to prevent path traversal.
- Original output and code/recipe SHA-256 are recorded. Re-exporting from the same source bytes, recipe and decoder version should reproduce the same WAV bytes; MP4 decoding can be affected by FFmpeg version, so preserve its version separately.
- WAV is uncompressed PCM16 output. Do not claim this "restores" quality lost in the input AAC recording.
- Sample-continuous loops are not guaranteed to be *musically* seamless. Play multiple loop cycles and confirm with the owner.
- The entire sound effects/music catalog and ROM sequence decoding are **not** part of this initial acceptance.
- Do not upload private captures, extracted copyrighted sounds, WAVs or source ROMs to GitHub CI artifacts.
