# Recorder validation — Windows, 22 November 2026

Scope: initial passive NES supporting utility, independently branched from main
at `adc6168`. No asset extraction, application expansion or merges. Original
research checkout and its unrelated documentation edit were preserved.

## Tests actually executed

- Windows Python 3.14.7, Pillow 12.3.0, pytest 9.2.0: **20 passed**, including the
  private SMB3 ROM test and seven recorder tests (four corruption subcases).
  Python 3.11/3.12 hosted CI is separate; no hosted result claimed here.
- Native MesenCE 2.2.1 cold-start smoke: 120 frames, four snapshots and capped
  events, compressed to 21,252 bytes. All fingerprinted sources unchanged.
- Default and optional event-mode 2,590-poll SMB3 replays: **326 files matched
  byte-for-byte in each A/B/A run** (off/on/off): controller bus and input/frame/
  CPU timing trace, 208 logical dumps, 104 RGB dumps and 12 independent RAM/PPU
  dumps. Recorder streams ended cleanly at tick 2,589 before the driver exited.
- Reconstructed memory at frames **450836 and 450866** exactly matched all 12
  independent dumps (internal/work RAM, CIRAM, palette, mapped PPU and OAM).
- Stress smoke: interval 1, checkpoint 10, 1 MiB budget, event cap 2. Stopped at
  tick 59 with `byte_limit`, 58 samples, **1,047,282 raw bytes** (below 1,048,576),
  72,294 compressed bytes. Stream remained reconstructable.
- Parser tests cover checkpoint/delta reconstruction, verified gzip round trip,
  invalid pages/sequences, missing baseline/checkpoint/footer, configuration
  bounds and draining >1 MiB of child output without exceeding the log cap.

## Does it identify changes when Mario enters another area?

**Yes for locating/comparing this recorded transition; no semantic recognition
claim.** The existing independently verified route requests the junction at
frame 450841 and previously observed layout completion at 450860. Without game
addresses or transition labels, the default recorder's largest change interval
was **450836 → 450866**, bracketing that event.

| Region | Changed bytes |
|---|---:|
| Internal RAM | 309 |
| Work RAM | 1,496 |
| CIRAM | 957 |
| Palette | 24 |
| Mapped PPU view | 8,513 |
| OAM | 6 |
| Secondary OAM | 0 |

These total 11,305 observations, **not unique physical bytes**, because views
overlap. Independent filtered RGB changed at 53,478 pixels between those frames.
Exact reconstruction and A/B/A equality establish useful state differences
without changing sampled replay behavior. Area meaning comes from the known
route. No area classifier was implemented; 30-frame sampling cannot identify
the exact triggering instruction or preserve every transient change.

## Cost and coverage

| Mode | Raw bytes | Gzip bytes | Wall seconds A / B / A2 |
|---|---:|---:|---|
| Default, events off | 2,372,460 | 166,144 | 8.852 / 8.985 / 8.535 |
| Optional bursts | 3,128,016 | 316,605 | 8.389 / 9.270 / 8.608 |

Both streams contain 87 samples across frames 448316–450896. B overhead relative
to the mean of adjacent controls was approximately **3.3% default** and **9.1%
with bursts**. Single trials including startup and driver reference capture,
not controlled benchmarks or guarantees for other games/settings.

Event mode retained 5,568 events across 87 one-frame bursts, at most 32 writes
and 32 execution events per burst. Callbacks saw 152,435 writes and 805,645
execution events during those bursts; the remainder were intentionally not
stored. Events outside bursts were not observed. Graphics/palette evidence
comes primarily from snapshots, not exhaustive PPU write logging.

## Private evidence

All paths are under `F:\Dev\ROMMAGE\FIXTURE\SMB3\FlightRecorder`:

- `aba-b54d4d2811\report.json`: final default A/B/A report;
  `B\capture.jsonl.gz`: default machine-readable session.
- `aba-b71d136900\report.json`: event-mode report and corresponding B capture.
- `20261122T174807Z-bd37fd92\manifest.json`: storage-limit test.
- `20261122T174154Z-3f9e7b46\manifest.json`: cold-start smoke.

Earlier pilot `aba-33b4dc1faf` lacked a footer because the driver's `emu.stop()`
bypassed `scriptEnded`. Final smoke requires a footer and stops recording before
driver exit. Abrupt external shutdown remains explicitly incomplete. Pilot
evidence was preserved; no false completeness claim is made for it.

ROM SHA-256:
`4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`.
Emulator SHA-256:
`8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7`.
Recorder Lua SHA-256:
`639c4b605bcb1f766dbae020c74c4f8db9fea24027a946229228aa70e2a877da`.
Complete source fingerprints and independent comparison hashes are in each
private report; sources were rehashed after capture. No captures, ROMs or states
are committed or uploaded to CI. Commands and limits: [runbook](MESENCE_FLIGHT_RECORDER.md).
