# SMB3 PRG1 ROM spelunking — 2026-11-16 research handoff

This is a **documentation-only, source-derived research increment** on top of draft PR #20's validated 24-frame baseline. It must not be interpreted as a newly executed MesenCE debugger session or completed level decoder.

**Dedicated reports**
- [Player physics, collision, gravity and animation](SMB3_PLAYER_PHYSICS.md)
- [World 1-1 instructions, geometry, object placements and renderer](SMB3_WORLD1_1_RECONSTRUCTION.md)
- [Earlier runtime-forensics acceptance and unresolved questions](SMB3_RUNTIME_FORENSICS.md)
- [ROM-backed music segments, pitch decoder and APU research](SMB3_AUDIO_ROM_SPELUNKING_20261116.md)

## Evidence and research continuity

| Finding | Present status | Follow-up |
| --- | --- | --- |
| 24 consecutive frames, 448385–448408; 24 private A/B/A source runs | Independently validated in preceding PR #19/#20 work | Preserve private provenance; no recapture requested |
| 144/144 player OAM recipe tile-field matches, three unique appearances, four holds | ROM/capture correlation in PR #20; **not observed live Player_Frame RAM** | Native bounded state/PC probe |
| Animation frame sequence 0x3E → 0x3F → 0x3E → 0x40 | ROM-source recipe interpretation | Verify actual RAM state and frame selection routine |
| Mario screen Y final hold: 98,98,99,100,101,103,105,107,109 | Captured evidence | Compare against world Y and camera/scroll |
| Airborne gravity model with +5 velocity units per tick | Modeled; one 4.4-fixed-point scenario fits all 9 screen-Y values | Inspect Player_InAir, Player_YVel, fractional accumulator |
| World 1-1: 9-byte header, 264-byte ROM layout source | PR #20 ROM fingerprint, partial header reader | Implement tested variable-length decoder |
| World 1-1: 86 construction records, five 4th bytes, one terminator | Static reparse of Southbird's source declaration and loader rules | Independent PRG1 ROM parse |
| Five major ground runs, three between-run gaps and one explicit pit generator | Source-derived; not verified against final game tile RAM | Dump/compare Tile_Mem at known gameplay state |
| Procedural cloud generator, hit-block memory and P-Switch substitution | Source-derived conditional map behavior | Check reproducibility from controlled RNG/flags |
| Separate 15-entry World 1-1 object placements and camera-based spawn logic | Source-derived; actual slots not observed | Trace object spawning and source-index associations |
| Logical 16x16 map → pattern/attribute strips → PPU | Source-derived renderer architecture | Validate CHR bank, palette, live PPU/pixels |

### Important scope rules

1. **Source code facts are not debugger observations.** The disassembly's code and variable labels are hypotheses about execution until synchronized live traces establish the chosen code path.
2. **Modeled predictions are not measured velocities.** The exact nine-frame fall fit admits multiple initial fractional phases and other possible world/camera conditions.
3. **Object placements are not live sprites.** Tile construction, source object records, runtime object slots, OAM hardware sprites and rendered pixels require distinct provenance.
4. **Source terrain is not the final map.** Generators have ordering/overwrites, random state, persistent collection flags and runtime substitution.
5. **No copyrighted ROM/source assembly/images/audio/save states** are included in these documents or in this Git branch. Source references link outward; original data stays under F:\Dev\ROMMAGE\FIXTURE\SMB3.

### Next decisive evidence request

The first native, read-only probe should sample frames 448396–448408 around the 0x3E → 0x40 transition. Record player world coordinates, fractional Y velocity, grounded/air state, Player_Frame, tile IDs under feet, camera scroll, OAM and the physical PRG mapping of the instructions that wrote the state. Compare an instrumented run to the accepted uninstrumented replay. The existing PR #20 runtime_observer.lua is **not** accepted as a working native capture tool until its launcher, bounding and neutrality are tested.

The project owner's ordinary Windows PowerShell session **can write** to F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation. Work's separate execution session reported access denied. Do not alter NTFS ACLs, relocate private data or claim this permission test was a native emulator capture.

### Branch/merge guidance

This research belongs on its own documentation branch and should be reviewed by Work before integration. Draft PR #20 remains the source for 24-frame recipe and World 1-1 stream acceptance. PR #19 remains the source for animation continuation. Documentation additions must not change those fixtures, rewrite the source hashes or silently mark decoder features as complete.

Provenance for the static analysis: [Southbird SMB3 disassembly pinned to 09b1bd81](https://github.com/captainsouthbird/smb3/tree/09b1bd81a788de8ceec664a34094e84ddb463117), [SpriteMine PR #19](https://github.com/87otlto-coder/SpriteMine/pull/19), [SpriteMine PR #20](https://github.com/87otlto-coder/SpriteMine/pull/20).

Source-derived facts and calculations have been checked by reading the relevant disassembly routines; **new synthetic tests, ROM-side decoder tests, live MesenCE execution and runtime state snapshots were not performed for this documentation increment**.
