# Controller-only World 1-1 power-up checkpoints

Private MesenCE 2.2.1 trials used the verified USA PRG1 ROM and original
World 1-1 save from the screen-8 approach. The original ROM and save remained
immutable. Inputs were sent through controller APIs. Game RAM was read through
the debugger memory domain.

## Observed progress

- Poll 452, frame 448767, world (256, 286): `Player_Suit` at CPU RAM `$ED`
  changed from `$00` to `$01` after the mushroom from column 15, row 19.
- Poll 1356, frame 449671, world (1473, 384): `Player_Suit` changed from
  `$01` to `$03` after the leaf from column 92, row 23. The trial remained
  in suit `$03` through poll 1400.
- The accepted trial's private working directory is
  `F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\raccoon-trials\lh-1205,0,1465,1400`.
  Its `route.tsv` has poll, frame, world X/Y, suit, P-Meter, flight timer,
  air state, pipe state, junction state and controller mask. The mask uses
  Right=1, A=16, B=32. The final column repeats the flight timer.
  The harness writes `suit-1-452.mss` and `suit-3-1356.mss` after the
  corresponding observed changes.

The Raccoon acquisition run ends before takeoff. P-Meter saturation,
flight to the upper mouth, pipe occlusion and the first bonus-room load are
still open. The exec host disconnected before final checkpoint hashes and
fixed-mask A/B/A could be collected.

## Route inputs

Polls are 1-based and ranges below are inclusive. Combine overlapping buttons.

- Right on 61–90, 180–191 and 427–472. A on 78–105, 180–211,
  360–391 and 433–458. Idle to poll 559 after the mushroom approach.
- Starting at 560 and before 1180, use Right+B while world X is below 1465.
  During that movement hold A when `(poll - 560) % 32 < 24` through 744.
  From 745 through 1013 hold A when `(poll - 745) % 24 < 16`.
  Hold A again on 1014–1031 while moving. This longer jump clears the hazard
  that costs the suit in several other trials.
- Jump in place on 1180–1199 to release the leaf. Wait through 1400.

The prerecorded mask column is the intended fixed-input replay source.
The existing runner can produce the native trace after converting that
column to a byte per poll. Capture artifacts and savestates are private.

## Pipe mask scope

OAM pattern `$77` in 8x16 mode selects PPU address `$1760` in window 5.
The static opacity result is **88/128 only when physical CHR page `$53` is
mapped into PPU window 5**. This route has yet to observe the runtime pipe
mask or its CHR mapping.
