# Passive MesenCE flight recorder — initial proof of concept

This standalone utility supports investigation of an NES session. It does not
extract assets, identify game objects, drive Mario, set breakpoints, or change
memory/input. No application code or existing research branch is required.

## Run on Windows

Python 3.11+ standard library only; use the existing portable MesenCE 2.2.1
runtime with Lua file/OS access enabled. The verified private runtime already
has this setting. Never enable untrusted scripts. Paths with spaces are supported.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-FlightRecorder'
$fixture = 'F:\Dev\ROMMAGE\FIXTURE\SMB3'
$emulator = Join-Path $fixture 'EmulatorRuntime\mesence-8ef403d6b9af3207-a76dbd831587ce04\Mesen.exe'
$rom = Join-Path $fixture 'GraphicsValidation\anim-right-w8-extakxfv\replay.nes'
python .\research\mesence\flight_recorder.py capture --emulator $emulator --rom $rom `
  --output (Join-Path $fixture 'FlightRecorder') --headless
```

Expected: a new UTC timestamp/unique-ID directory containing `manifest.json`,
`capture.jsonl.gz`, and a log capped at 1 MiB. Headless mode starts the ROM
normally; it does **not** play the game or attach to an existing emulator.
For normal play omit `--headless`, play in the newly launched emulator, then
close it. The recorder stops collecting after its frame/byte limit without
stopping interactive gameplay. The launcher waits at most `--timeout` + 15
seconds (default 135), then terminates **its own** emulator process and packages
available evidence. Increase `--timeout` for longer interactive sessions.

For an already-running NES session, create an empty private directory, set
`SMFR_OUTPUT` in the environment **before launching Mesen**, then load
`research/mesence/flight_recorder.lua` in its script window. This standalone
mode leaves a bounded `capture.jsonl` spool; the Python launcher is responsible
for compression/manifest generation. Existing captures are never overwritten.

```powershell
# Replace this with the session directory printed by capture.
$session = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\FlightRecorder\SESSION'
python .\research\mesence\flight_recorder.py inspect (Join-Path $session 'capture.jsonl.gz')
```

## What is captured and bounded

| Setting | Default | Effect |
|---|---:|---|
| `--interval` / `SMFR_INTERVAL` | 30 frames | Sample at first end-frame boundary, then every 30 callbacks |
| `--checkpoint` / `SMFR_CHECKPOINT` | 300 frames | Full checkpoint at the next sample after each checkpoint interval |
| `--frames` / `SMFR_FRAMES` | 3,600 | Stop collecting after this many callbacks (roughly 60 seconds NTSC) |
| `--max-mib` / `SMFR_MAX_BYTES` | 64 MiB / 67,108,864 bytes | Hard raw capture size budget; reserved footer space |
| `--events` / `SMFR_EVENTS=1` | off | One-frame CPU write/exec sampling burst after each snapshot |
| `--event-cap` / `SMFR_EVENT_CAP` | 32 per kind/burst | Retain first N events; report total seen during that burst |

The script discovers populated `nes*Ram` enums and sizes, subject to a 256 KiB
aggregate RAM budget. Empty/unavailable/over-budget regions are listed in the
header. It also records the 12 KiB side-effect-free mapped PPU pattern/nametable
view. On the SMB3 fixture: 2 KiB internal RAM, 8 KiB work RAM, 2 KiB CIRAM,
256-byte OAM, 32-byte secondary OAM, 32-byte palette, and mapped PPU memory.
Static PRG/CHR ROMs are not dumped in full; mapped CHR bytes are captured.

Each sample includes the available `getState()` table (CPU/PPU/mapper fields),
frame, CPU cycle, scanline, PPU cycle, controller-0 sampled input and cumulative
IRQ/NMI counts. Session-relative `tick` remains distinct from emulated frame
numbers. Baseline/full checkpoints contain all pages; deltas contain only
changed 256-byte pages, hex encoded. `changed_bytes` counts individual changed
bytes, with overlapping physical/mapped regions counted separately.

Memory is bounded to previous pages plus the current sample and capped events.
Writes are batched by JSON record and flushed at samples. Compression runs after
capture and is verified against the raw stream's SHA-256 before deleting only
that session's spool. Peak spool+gzip storage can approach twice the raw budget,
plus the 1 MiB emulator log and small manifest. No sockets or extra dependencies.
At a byte limit the final attempted sample is discarded whole and the footer
marks `byte_limit`; earlier complete samples remain reconstructable.

## Format and offline use

`manifest.json` records settings, exact invocation, UTC start, wall duration,
source paths/hashes (ROM, emulator, core DLL, settings, script), unchanged-source
check, capture hash, byte counts, completion/error status and summary.
The gzip contains UTF-8 JSON Lines, schema 1:

- `header`: configuration, region sizes, availability, initial state and ROM info.
- `sample`: contiguous `seq`, `full`, `time`, state/input/interrupts, region→page
  offset→hex data and byte-change counts. Empty maps are JSON objects, not arrays.
- `burst`: timing, retained write-intent/exec events and actual per-burst totals.
- `end`: termination reason and final accepted sample count.

Import `flight_recorder.py` and call `snapshots(path)` to iterate reconstructed
`(record, {region: bytes})` pairs. It validates sequence, baseline, checkpoint
completeness, page sizes and offsets. `inspect` lists the ten largest change
intervals. These are candidates for investigation, not semantic area names.
An absent footer means interrupted/incomplete; valid earlier JSON lines are
still useful. A truncated line is an error, never silently accepted as complete.

## Verified API and limits

Checked against MesenCE **2.2.1, commit
20ba206cef5ba207c21203176d02cb9f43dda9fb**, then executed on the private Windows
binary SHA-256 `8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7`.
Primary references:
[Lua documentation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json),
[Lua API implementation](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Debugger/LuaApi.cpp).
No upstream implementation code was copied.

- `read(address, memType)` with physical RAM or `nesPpuDebug` avoids bus side
  effects. Never use ordinary CPU/PPU bus reads for this recorder.
- `addMemoryCallback(fn, type, start, end, cpuType?, memoryType?)` uses **CPU type
  as the fifth argument**. Writes are pre-write intent; callbacks return nothing.
  Hooks cover the NES CPU address space only during sampled bursts and are removed
  at the next frame boundary, outside the memory callback. No manual breakpoints.
- Recording caps bound stored events, not callback dispatch within a sampled
  frame. First-N samples are biased; bursts are not an instruction trace. Shorter
  intervals and event mode cost more. Off remains the low-impact default.
- PPU bus callbacks do not universally cover CPU-driven VRAM writes in this
  version (see existing PR #24). This utility makes no such coverage claim and
  observes PPU changes through snapshots. Frame-boundary mapped CHR is not
  scanline/fetch-time bank evidence; palette snapshots can miss mid-frame effects.
- No audio capture, full controller history, save-state replay package, full
  mapper model or complete machine dump. Values that change and revert between
  samples are invisible. `getState().masterClock` is truncated to 32 bits in this
  API; use recorded `cpu.cycleCount`, not masterClock, for long-run CPU timing.
- Manual reset/state-load events force checkpoints. Programmatic savestate loads
  need not emit `stateLoaded`; the separate smoke driver installs the recorder
  only after restoring its starting state. General rewind/replay analysis is not
  validated. Frames/CPU cycles may go backwards across externally loaded states.
- `scriptEnded` is best effort: native `emu.stop()` can exit before that callback.
  The frame limit provides a reliable footer in tested headless runs. Shutdown
  without a footer is reported incomplete, even if the emulator exits zero.

## Native SMB3 transition test

The optional `smoke_flight_recorder.py` reuses the existing PR #21 controller-only
pipe replay **as an external test driver**. Game-specific labels belong to that
test, never to the recorder. The complete 2,590-poll route is fingerprint-gated.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-FlightRecorder'
$fixture = 'F:\Dev\ROMMAGE\FIXTURE\SMB3'
$source = Join-Path $fixture 'GraphicsValidation\anim-right-w8-extakxfv'
python .\research\mesence\smoke_flight_recorder.py `
  --emulator (Join-Path $fixture 'EmulatorRuntime\mesence-8ef403d6b9af3207-a76dbd831587ce04\Mesen.exe') `
  --rom (Join-Path $source 'replay.nes') --slot (Join-Path $source 'slot-copy.mss') `
  --input (Join-Path $fixture 'RuntimeInvestigation\world11-raccoon-controller-2590.bin') `
  --driver 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\research\mesence\pipe_replay.lua' `
  --output (Join-Path $fixture 'FlightRecorder')
# Add --events to test optional bursts as well.
```

It compares A/B/A (recorder off/on/off), controller/timing logs, 104 start/end
logical snapshots, 104 RGB frames, and 12 independently read memory snapshots.
Run results are in [the validation note](MESENCE_FLIGHT_RECORDER_VALIDATION.md).
Private sessions, ROM, states and captures stay under `FIXTURE`, never Git/CI.
