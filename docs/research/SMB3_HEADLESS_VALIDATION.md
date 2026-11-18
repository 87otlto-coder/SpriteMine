# Headless SMB3 PRG1 validation

## Static commands

Use Python 3.11 or later with SpriteMine and its dependencies installed. The ZIP is read directly. Output containing indexed pixels or logical tile values is private.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$env:PYTHONPATH = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\src'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
python -m spritemine inspect $rom
python -m spritemine inspect-player-recipes $rom
python -m spritemine reconstruct-sprite $rom 0x3E
python -m spritemine validate-sprite $rom
python -m spritemine reconstruct-level $rom
$env:SPRITEMINE_TEST_ROM = $rom
python -m pytest -q
```

The accepted 393,232-byte ROM image inside the ZIP hashes to
`4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`.
All 81 recipe records are inspectable. The three canonical renders match their
indexed and binary-alpha SHA-256 references and opaque counts of 138, 174 and 194.
Use `--include-pixels` or `--include-tiles` only for private output.

## Native replay

The runner uses the established graphics harness scripts from
`d9aa7adf2bb35b917ce0305cf6878ec7c394e521` and the portable MesenCE 2.2.1 build
`20ba206cef5ba207c21203176d02cb9f43dda9fb`.
The paths below use the immutable warmup-8 archive as the source of the verified
ROM image and slot copy. Outputs go to a new folder in private RuntimeInvestigation.

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$env:PYTHONPATH = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\src'
$fixture = 'F:\Dev\ROMMAGE\FIXTURE\SMB3'
$source = Join-Path $fixture 'GraphicsValidation\anim-right-w8-extakxfv'
python 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\research\mesence\player_observer_replay.py' `
  --root 'F:\Dev\ROMMAGE' `
  --harness 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics\research\mesence' `
  --emulator (Join-Path $fixture 'EmulatorRuntime\mesence-8ef403d6b9af3207-a76dbd831587ce04\Mesen.exe') `
  --slot (Join-Path $source 'slot-copy.mss') `
  --rom (Join-Path $source 'replay.nes') `
  --timeline (Join-Path $fixture 'Animations\right-8-31-e6bd441caa\timeline.json')
```

All 24 historical windows passed read-only archive revalidation. Fresh observer
A/B/A runs kept sprites enabled in every leg and enabled the passive observer
only in B. All three legs matched at every sampled boundary for timing, OAM,
palette, PPU pattern snapshots and filtered RGB. Controller bus and replay
logs matched byte-for-byte. The observer collected 24 events each for start,
end, IRQ and NMI. Start-of-frame CPU RAM `$EE` gave 5 × `$3E`, 6 × `$3F`,
4 × `$3E`, 9 × `$40`. End-of-frame RAM changed one sampled frame earlier at
each transition. Across the 24 frames the new decoder matched 4,032 native
opaque RGB samples and all 24 archived RGBA hashes, including transparent positions.
The displayed reference is video-filtered RGB24. CHR matching is scoped to the
observed player components. One repeated timing sample measured A/B/A at
1.621/1.407/1.424 seconds, which is wall-clock evidence only.

## Outstanding gates

The scanline compositor selects among the first eight in-range OAM entries,
then applies background priority to the winning nonzero sprite pixel. Synthetic
tests cover this interaction, but authentic pipe mask slots and fetch-time
banks remain unverified. Reproduce the screen-8 traversal and record OAM slots
0–3 and 10–15, fetch-time CHR banks and background indices across the entrance.

The bonus layout model matches the Expedition 12 864-byte screen-major
fingerprint. It reconstructs the two reciprocal layout/object pointers and the
bonus generators and junction descriptor. A first-entry live Tile_Mem dump is
needed to validate the model. Supply the two 432-byte screens in screen-major
order to `python -m spritemine validate-level $rom <private-dump>`. The CLI
reports byte agreement and the first differing offset. It cannot authenticate
the dump's capture provenance. Main-area clouds need RNG state and ordering.
Quadrant mapping, background CHR, palette attributes and PPU strips remain open.
