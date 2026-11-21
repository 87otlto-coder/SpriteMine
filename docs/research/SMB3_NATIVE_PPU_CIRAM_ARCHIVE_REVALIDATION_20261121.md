# SMB3 PRG1 — Original-ROM native PPU archive revalidation (2026-11-21)

**Result: PASS for the sampled World 1-1 first-entry bonus-room source staging, observed CPU $2007 write requests and captured physical CIRAM frame-boundary effects.**

This is an **independent offline reanalysis of private owner-uploaded `B.zip`** containing the complete native MesenCE 2.2.1 replay at `pipe-replay-xbhs6ijw`. The original **USA PRG1 / Revision A ROM** was also supplied privately and independently SHA-256 checked. No emulator was launched for this offline reanalysis, and the new corrected CLI has **not yet been run by the owner** at the time of this note. The captured MesenCE session is an owner-run replay; the byte comparisons below were independently executed on its archived data. Do not turn that into a claim of two independent emulator runs.

**Privacy:** Private `B.zip`, private ROM, checkpoint, screenshots, nametable RAM, sprites and extracted graphics are not committed to GitHub. Only the source hash, numeric results and reproduction path appear here.

## Private source fingerprints

| Source | SHA-256 |
| --- | --- |
| Owner-uploaded private capture archive `B.zip` | `10ce8ab9c0abb88322e0dbcc7a6edc2b9c420f1062b33c5ecaff74b05f0d1a46` |
| Private raw SMB3 USA PRG1 ROM | `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579` |
| Verified 1024-byte Plains quadrant table | `c19dfefb08bfdebaa2be3bce01abc590865da46f804ccd36f4b9d96db1bf9362` |
| Replay `report.json` | `c546b167a51e3e95ee48f7fcb2ee2b5f7e3b081a922657ee7fe4541e6d87bb77` |
| B `background-staging.tsv` | `a3805eb9e64efc3d328d25380846be53661f944db3b6d605702753ec0cf4030a` |
| B `ppu-registers.tsv` | `590be037e65f8ef0b1e4c7ce2efc5570941bf7b353f29c911c1853dd37e07fe0` |
| B `ppu-ciram-boundaries.tsv` | `d96af28fc61d33d963f90847b35f2f7648fa20b8cecc6528b2fd19e4990a4f9c` |

The three trace hashes match their own stored report fields. The manifest also records input SHA-256 `f780c7ba7e5002f9a62161486ad29e978106588571f6bf8eb268bd909681d082` and fingerprints of the executable, state and Lua scripts; those particular binaries were **not** independently checked against local originals in this reanalysis.

## Independent comparisons

| Acceptance boundary | Evidence | Result |
| --- | --- | --- |
| A/B/A neutrality | Rehashed all **314 common evidence files** in each of A, B and A2 against the report's reference signatures | **314/314 per leg, 0 differences** |
| Replayed window | Manifest: 2,590 controller polls, frames **450778–450881**, `neutral: true` | **Complete** |
| CPU Plains producer staging | Original-ROM table and 864-byte native logical map rebuilt source-modeled **32 pattern × 54 bytes + 32 attribute × 14 bytes** | **2,176/2,176 bytes match**, 0 mismatches |
| Out-of-scope producer events | 66 events total; first **2** have a nonaccepted logical-map fingerprint | **2 excluded**, not marked as passes |
| CPU bus upload address/value sequence | Matched **64** eligible native producer events to contiguous, nonoverlapping observed `$2007` write requests, requiring exact byte, address, vertical increment mode and chronological order | **64/64 events, 2,176/2,176 bytes match** |
| Across-frame transfers | Three valid uploads span native frame boundaries | Events **15 (pattern), 34 (attribute), 63 (pattern)** accepted with complete byte/address match |
| Physical 2 KiB nametable RAM | Applied all **5,491** captured nametable CPU write requests, in order under captured MMC3 mirroring, to the frame-start physical CIRAM snapshot, then compared each of 104 resulting frame-end snapshots | **104/104 frames, 212,992/212,992 physical bytes match; 0 mismatches** |
| MesenCE PPU debug nametable alias | Independently compared the four 1 KiB PPU logical nametable pages in **104** native end-frame debug views to observed physical CIRAM under the captured MMC3 bit | **425,984/425,984 bytes match; 0 mismatches** |

The entire trace contains **10,430 PPU register observations**, including **6,771 CPU $2007 requests**, of which **5,491 target nametable memory**. The B trace contains 208 physical CIRAM frame boundary records (start + end for each of 104 frames). On all these observed requests the captured `video_ram_addr` matches the reported `bus_addr`. In the captured window, MMC3 mirroring bit 0 of `$A000` is 1 for the relevant requests and CIRAM snapshots, corresponding to physical horizontal mirroring under MesenCE conventions.

## Corrections to PR #24 verifier

The original direct `python research\mesence\verify_ppu_commit_trace.py` invocation failed with `ModuleNotFoundError: No module named 'research'` because `PYTHONPATH` included `src` but not repository root. This was an **offline Python import failure after a successful native capture**, not an emulator failure.

The old verifier also falsely rejected valid writes during off-VBlank initial redraw when rendering was disabled, and falsely required each 54-/14-byte transfer to remain inside one frame. Actual first-entry World 1-1 bonus layout rebuilding has both characteristics; the capture proves three uploads cross frame boundaries.

The corrected PR #24 verifier now:
- Resolves its repository package when launched directly by full path.
- Treats $2007 callbacks as **prewrite CPU requests**, not completed hardware writes, and compares all observed physical CIRAM frame effects before accepting them.
- Correlates complete source-defined 54-/14-byte transfers across at most one frame boundary without double-counting any CPU write.
- Records limitations as `per_write_ppu_cycle_completion_verified: false` and `rendering_state_at_each_write_captured: false`.

Hosted Windows CI after code and regression-test changes: [run 44906486710](https://github.com/87otlto-coder/SpriteMine/actions/runs/44906486710), **46 passed, 4 private-fixture skips** on Python 3.11 and 3.12. That synthetic CI is not a native capture. The updated local Windows private-ROM suite is expected to run 50 tests; it has not yet been reported.

## Boundary of the claim

These results **independently establish end-of-frame physical nametable agreement for the captured replay**, not individual within-scanline hardware write timing, rendering-enable state at each individual CPU write, fetch-time MMC3 CHR mapping, palette-driven color selection, visible 256×240 background pixels or general SMB3 level coverage.

The capture makes a strong byte-level connection from the *original ROM's* bonus logical tiles, to CPU staging, to observed CPU VRAM write requests, to measured physical CIRAM and its PPU debug nametable view. Other rendering gates remain explicitly open.

Original private Windows directory (do not publish contents):

`F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-xbhs6ijw`

A formal post-fix CLI return of `passed: true` should be preserved beside these independent calculations, using the **existing** capture (no new MesenCE replay). Until then, call this an independently checked archive acceptance, not a completed post-fix CLI run.
