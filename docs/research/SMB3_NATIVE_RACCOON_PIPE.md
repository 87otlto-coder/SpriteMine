# Native Raccoon flight and World 1-1 bonus-room capture

The fixed controller replay starts from the verified USA PRG1 slot in
`GraphicsValidation/anim-right-w8-extakxfv`. The ROM, emulator, slot and
settings hashes match the blocked-approach reference. No memory or ROM writes
were used to move Mario or acquire suits.

| Event | Poll | Frame | Evidence |
|---|---:|---:|---|
| Mushroom | 452 | 448767 | Suit $01, world (256, 286) |
| Super Leaf | 1356 | 449671 | Suit $03, world (1473, 384) |
| Full P-Meter | 2223 | 450538 | $7F, world (2376, 384), running left |
| Takeoff | 2225 | 450540 | Flight timer $80, world (2371, 384) |
| Upper pipe | 2466 | 450781 | Down+B, world (2260, 80), pipe $0E |
| Junction request | 2526 | 450841 | Junction $03, pipe $82 |

The route goes right past the pipe and reverses at poll 2110. After the
leftward runway and takeoff it flaps with two A polls per six. At 2432 it
countersteers right for five polls while holding Down+B, then releases Right.
The first actual pipe write ($02, then $0E) occurred in frame 450780.
The first layout completion was frame 450860, CPU cycle 13426820944.

The complete 2590-byte controller sequence hashes to
`f780c7ba7e5002f9a62161486ad29e978106588571f6bf8eb268bd909681d082`.
The independently captured 1400-poll power-up prefix hashes to
`22b31cc102424b21fc343eac3c9e7eca1a6530ce27e353a5d0be043e4152477d`
and passed A/B/A. Private savestate SHA-256 values follow.

- Mushroom: `d1649099a7df577d8ab1e5aa1d9b44483cdc6b91d0c33c6e2a2a4ec93d44c2be`.
- Raccoon: `173c7355525315962219c2d4d6dc5407296baf40046002f70b82ff4ce6206f7b`.
- Pre-entry detailed checkpoint: `14c3c48479153e66d3bb923e36a48551c977781a70437238f87128cd7e9972ca`.

## Native results

Event discovery selected 450778–450881. Normal A/B/A agreed on controller,
timing, sampled tile state and filtered RGB. A second A/B/A window covered
450782–450837 and recorded a sprites-hidden background reference whose
controller, game state and timing matched. The independent verifier uses the
start-of-frame hardware OAM and PRG1 CHR bytes, with mapper writes checked
through mask fetch scanlines. In all 56 compared frames, slots 0–3 had
pattern $77 and behind-background attribute $20. PPU window 5 mapped physical
page $04 and the glyph had 128/128 opaque pixels. Status-bar bank $7E appears
at end-frame boundaries and does not describe gameplay fetches. The
hypothetical 88/128 result applies only to page $53 mapped into window 5.

With the mask present, the model kept the background visible. With those
slots hidden in the software model, Mario would win at 7,528 pixels where
the expected RGB is distinguishable. Native RGB matched the model at all
7,528. An additional 644 overlapping samples were indistinguishable under
the RGB comparison. This passes Gate C for the sampled entrance overlap.
It does not certify all rendered pixels or entry/exit variants.

The $89A0 post-layout hook captured 864 bytes before gameplay modification.
All 864 matched the existing model with zero differences, passing Gate D for
the logical map. The combined SHA-256 is
`c57b72c77899d596745065c90878327993f9a25e6289c0b22d960c58021b088a`.
The two 432-byte screen hashes are
`08b8f5dc7f0bbfdd60a4ce22c2812c50c5bc534bbabd0eb29e275dd8b575e016` and
`2c4c866f6e77556b78370013cf605af0bd657999dfde5a1f8e63aba3ee7b0a7b`.
Logical-to-pattern, quadrant and attribute mapping remain unverified.

## Replay inputs

Each token is a decimal run length followed by a hexadecimal controller mask.
Right=1, Left=2, Down=4, A=16, B=32. Only controller input is reproduced below.

```text
60*00 17*01 13*11 15*10 74*00 12*11 20*10 148*00 32*10 35*00 6*01 26*11
14*01 87*00 24*31 8*21 24*31 8*21 24*31 8*21 24*31 8*21 24*31 8*21
24*31 1*21 16*31 8*21 16*31 8*21 16*31 8*21 16*31 8*21 16*31 8*21
16*31 8*21 16*31 8*21 16*31 8*21 16*31 8*21 16*31 8*21 16*31 8*21
23*31 76*21 72*00 20*10 200*00 16*21 28*31 8*21 28*31 8*21 28*31 8*21
28*31 8*21 28*31 8*21 28*31 8*21 28*31 8*21 28*31 8*21 28*31 8*21
28*31 8*21 4*31 21*21 20*31 39*21 26*31 39*21 20*31 8*21 20*31 8*21
20*31 8*21 20*31 8*21 20*31 8*21 20*31 8*21 17*31 114*22 2*32 4*22
2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22
2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22
2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22
2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22
2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22 2*32 4*22
2*32 4*22 2*32 4*22 2*32 4*22 2*32 2*22 5*25 154*24
```

Use the existing Windows command from [native approach](SMB3_NATIVE_PIPE_APPROACH.md)
with the reconstructed input file and `--events` instead of a fixed window.
For the RGB subset compare a second capture with
`--first 450782 --last 450837 --background-reference`, then invoke
`verify_pipe_mask.py ROM CAPTURE_DIRECTORY`. Run
`python -m spritemine validate-level ROM LAYOUT_COMPLETE_DUMP` for the logical map.
