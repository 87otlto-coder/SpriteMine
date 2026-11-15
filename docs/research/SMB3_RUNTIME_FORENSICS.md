# SMB3 runtime forensics — 2026-11-15

## Findings and limits

Research baseline: PR #19 head `d9aa7adf2bb35b917ce0305cf6878ec7c394e521`.
The existing research branch already adds `runtime_patterns.py` and its four
tests at `0aca0c961fb460f8c05630b8c8db83050a9d236d`. This increment reuses
that reader and adds recipe-offset interpretation, header decoding and evidence
analysis. No new emulator
capture was made: creating `F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation`
returned access denied twice. Private experiments were not moved elsewhere.
The separate writable source checkout preserves the accepted baseline ancestry.

### Player assembly: source data verified, execution still unresolved

The complete 486-byte, 81-entry player pattern table in Southbird's PRG029
matches exactly one location in the accepted ROM. Related offset and CHR-page
tables are fingerprinted by `research/mesence/player_recipe.py`.

| Record | File offset | Bank / CPU address | Length |
| --- | --- | --- | --- |
| Biased half-offset lookup | `0x3AC10` | 29 / `0xCC00` | 81 |
| Six-pattern recipes | `0x3AC61` | 29 / `0xCC51` | 486 |
| Recipe CHR-page offsets | `0x3AE47` | 29 / `0xCE37` | 81 |
| Player draw routine entry | `0x3AEAF` | 29 / `0xCE9F` | entry only |
| Recipe pointer calculation | `0x3AF2E` | 29 / `0xCF1E` | source + ROM inspected |
| Store to candidate Player_Frame | `0x109B1` | 8 / `0xA9A1` | instruction inspected |

Bank numbers are physical 8 KiB PRG banks; CPU addresses require the stated
bank mapping. File offsets include the 16-byte iNES header. `convertAddress`
returns PRG-relative offsets, so an observed PRG mapping needs the header
added before comparison with these file offsets.

The lookup doubles a stored byte and indexes a pointer biased four bytes
before the pattern table. Carry increments the pointer high byte. The first
three table patterns are written to relative OAM slots 3/4/5; the remaining
three to slots 0/1/2. `0xF1` is a game suppression marker. It is not universal
NES transparency. The routine additionally handles mirroring, palette,
priority, clipping, flashing, suit changes and special poses.

Historical source windows were independently revalidated with the accepted
validator: **24/24 passed**, without writing to the archive. The new restricted
analysis checked **144/144 OAM tile fields** across slots 10–15. All six
attributes are `0x40` in each accepted frame; four suppressed slots have Y=248.
The two visible components independently agree with physical CHR offsets
predicted by the small-suit root page plus recipe page offset (1 KiB bank 83).

| Captured frames | Matching recipe | Source interpretation |
| --- | --- | --- |
| 448385–448389 | `0x3E` | small-player walk recipe |
| 448390–448395 | `0x3F` | second small-player walk recipe |
| 448396–448399 | `0x3E` | first recipe again |
| 448400–448408 | `0x40` | standard small-player jump/fall recipe |

These are verified recipe correspondences, **not observed RAM frame IDs**.
The disassembly's ground-movement path tests Player_InAir and selects the
standard jump/fall frame. The store at bank 8 / A9A1 matches ROM bytes, but its
execution during this capture was not observed. Falling after a terrain edge
is a strong hypothesis; the collision trigger, velocity and causative code
path remain unresolved. Nine repeated jump/fall images are not a walking loop.

The PPU temporary horizontal scroll encoding changes from 65 to 89; its
vertical encoding stays 239. Mario remains at screen X=128 while Y eventually
increases. These latch observations support investigating horizontal camera
tracking; they are not automatically world coordinates or a complete raster
scroll history. Current captures contain no CPU RAM snapshots or executed PCs.

### Timing correction

Installed Mesen.exe reports `2.2.1+20ba206cef5ba207c21203176d02cb9f43dda9fb`;
its SHA-256 is `8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7`.
The local source is the exact same commit and tag 2.2.1.

`Core/NES/NesConsole.cpp` returns CPU cycle count from GetMasterClock and the
NES CPU rate from GetMasterClockRate. `Core/Debugger/LuaApi.cpp` narrows that
counter to uint32 in getState. Thus existing deltas 29,780/29,781 are **CPU
cycles**, not PPU dots. The API clock wraps modulo 2^32 (about 40 minutes at
NTSC rate 1,789,773). Existing 24-frame ordering is unaffected. New observers
must retain full `cpu.cycleCount`, API clock, clockRate, region and boundary.
Do not silently rewrite the historical timeline schema or claim it sampled
full-width CPU clocks.

### World 1-1: source/header established

Southbird's `PRG/levels/Plains/1-1.asm` identifies original CPU address BB82.
Its complete 264-byte layout stream uniquely matches ROM file `0x1FB9B`,
immediately after the nine-byte header at `0x1FB92` (physical bank 15).
Stream SHA-256: `ef2d1e5a95cd51391e5651af0cdd9ab0cba36985e4cf971d3eed7c34d506892a`.

`level_header.py` reads the verified ROM and decodes pointers and bit fields:
11 screens, initial X=24/Y=384, palette selectors 0/8, alternate tileset 1,
horizontal orientation, scroll mode 0, background-bank index 1, initial action
0, music selector 0 and timer 300. The tileset nibble describes the **alternate
area**; treating it as the current area's tileset would be an error.

This does not decode variable-length object commands, metatiles, collision,
dynamic objects or final terrain. Do not split this stream into arbitrary
three-byte records. Header meanings are source-backed; loader execution and
independent gameplay comparison remain pending.

### Audio: source reconnaissance only

PRG028 contains the first sound-engine bank; PRG031 includes Music_PlayDMC.
The latter has a source/ROM-corresponding path at E2E1 (file 0x3E2F1), loading
DMC register-control/address/length tables and writing 4010/4012/4013/4015.
Its address rule is C000 | (register << 6), length (register << 4)+1.
The source calls out an anomalous length for one reused sample. This has not
been independently reproduced as audible behavior. No music, sound effect,
APU event trace, WAV, sequence decoder or musical transcription was produced.

## Instrumentation capability audit

| Facility | Exact-version source finding | Native status this session |
| --- | --- | --- |
| Frame/input callbacks | LuaDocumentation + LuaApi registration | established historical harness; no new run |
| CPU exec/read/write watchpoints | address-filtered addMemoryCallback | new observer unexecuted |
| Write callback semantics | callback runs before write; integer return replaces value | observer returns no replacement |
| CPU state and mapping | getCpuState/getState; convertAddress returns address + memType | source checked |
| Side-effect-free reads | nesDebug/nesPpuDebug; ReadMemory masks debug flag | source checked |
| Primary/secondary OAM | 256-byte and 32-byte memories registered by NesPpu | source checked; secondary OAM not newly sampled |
| Palette, nametable, screen | existing probes and real historical comparisons | historical sampled gates passed |
| Access counters / CDL | getAccessCounters/getCdlData exported | not exercised |
| MMC3 bank/IRQ registers | memory callbacks can observe writes | historical bank traces; IRQ execution not proven |
| APU register writes | CPU write callbacks cover registers | prepared only; no audio capture test |
| Debugger UI breakpoints/trace logger | debugger implementation present | not exercised |

Secondary OAM is scanline-dependent; a frame-boundary dump cannot prove
per-scanline visibility. No C++ instrumentation is justified yet: targeted Lua
observations can address the immediate questions, subject to native validation.

## Reproduction and next experiment

Run from a checkout containing this branch; private inputs stay on F:.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m unittest discover -s tests -p test_player_recipe.py -v
python -m unittest discover -s tests -p test_level_header.py -v
python -m research.mesence.inspect_runtime_baseline 'F:\Dev\ROMMAGE\FIXTURE\SMB3\Animations\right-8-31-e6bd441caa\timeline.json' --revalidate-sources
```

Expected: 6 recipe tests and 4 header tests pass; JSON reports 24 source
windows, 144 matched fields and the explicit limitations. The command prints
metadata and does not create files. Full pytest/hosted CI was not run here;
pytest is absent from this Windows Python 3.14.7 environment.

`runtime_observer.lua` is a **prepared, unexecuted adjunct**, not a new accepted
capture format. It is designed for concatenation between graphics_replay.lua
and spritemine_render_probe.lua in an isolated copy of the existing harness.
It records bounded frame snapshots, watched RAM/OAM/APU/mapper writes, CPU
controller reads and the actual last exec callback's address/mapping. It has a
10,000-record/8-MiB cap and explicit truncation footer. Do not manually edit
an accepted capture.lua or assume the existing launcher loads this adjunct.
A launcher integration and Lua mock/native tests are still required.

Once canonical write access works: add and test isolated observer launching,
then replay the exact accepted right-input state through frame 448408. Compare
instrumented and baseline screen/OAM/input hashes. Trace candidate addresses
D8 (air), EE (frame), CF (Y velocity), A2/87 (world Y), 542/543 (scroll), and
58E (OAM root offset). Verify instruction mappings at the transition and OAM
producer. Capture neutral versus right next, changing only input. RAM names
remain source candidates until code-path evidence confirms their role.

## Coverage and engineering handoff

| Objective | Result |
| --- | --- |
| Preserve/revalidate 24-frame baseline | fully verified for existing gates |
| Player pattern format/source offsets | verified static data; narrow reader implemented |
| Six-component historical correspondence | verified in this specific archive |
| Input→RAM→instruction→movement transition | partially investigated; new capture blocked |
| Camera/world/subpixel state | unresolved; candidate addresses identified |
| Enemy/item/power-up assembly | not investigated dynamically |
| World 1-1 header/source stream | verified source identity; partial decoder |
| Terrain/metatiles/collision/runtime geometry | unresolved |
| Audio engine | source reconnaissance; dynamic work blocked |
| Native observer neutrality/repeatability | not tested |

Next implementation priority: establish the state-transition capture, then
promote the player recipe reader into a runtime-aware component model. Keep
raw table components, captured OAM and visible pixels distinct. Add full
clock provenance before time-based animation export. Level work should next
follow actual loader dispatch and object-length rules, not screenshot stitching.

References: [Southbird SMB3 research disassembly](https://github.com/captainsouthbird/smb3)
(credit to Southbird; original project link http://www.sonicepoch.com/sm3mix/),
[MesenCE 2.2.1](https://github.com/nesdev-org/MesenCE/tree/20ba206cef5ba207c21203176d02cb9f43dda9fb).
The disassembly has no repository license declaration; no third-party assembly,
tables, ROM bytes or assets are included in this change. MesenCE is GPLv3;
no emulator source is copied or modified.
