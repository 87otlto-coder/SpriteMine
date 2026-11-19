# Headless World 1-1 bonus-room background staging (increment 1)

Date: 2026-11-19. Branch: `feature/smb3-world11-background` (stacked on draft PR #21). Game: immutable **SMB3 USA PRG1 / Revision A**. **Status: implemented source/ROM-derived model; native staging/PPU pixel gate still open.**

## What is established already

- The 2,590-poll controller-only Raccoon replay and first bonus-room entry are recorded in [SMB3_NATIVE_RACCOON_PIPE.md](SMB3_NATIVE_RACCOON_PIPE.md), where the 864-byte model matches all 864 native first-entry Tile_Mem bytes. This is genuine **logical map** acceptance, not a rendered background.
- The Plains logical tile expansion is described by pinned [Southbird PRG015](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg015.asm#L8-L85) and [PRG030 column/attribute builder](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg030.asm#L5120-L5368). The PPU commit is in [PRG026](https://github.com/captainsouthbird/smb3/blob/09b1bd81a788de8ceec664a34094e84ddb463117/PRG/prg026.asm#L3341-L3447). Pinned [MesenCE MMC3 source](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/NES/Mappers/Nintendo/MMC3.h#L84-L141) corroborates mapper bank and mirroring semantics.

## Implemented headless code (this PR only)

`src/spritemine/background.py`:

1. For the **verified PRG1 complete image SHA-256** only, reads the 1,024-byte Plains layout table starting at original-ROM file offset `0x1E010`. Its independently checked SHA-256 is `c19dfefb08bfdebaa2be3bce01abc590865da46f804ccd36f4b9d96db1bf9362`; source bytes are never committed.
2. Treats four consecutive 256-entry tables as **UL, LL, UR, LR**, not ordinary UL/UR/LL/LR memory order. Palette group comes from the logical Tile_Mem byte's top two bits, independent of the 8x8 pattern byte.
3. Builds **54-byte vertical Scroll_PatStrip** for a chosen 16px logical tile column and left/right 8px half; two pattern bytes are emitted per each of 27 logical rows.
4. Builds **14-byte Scroll_AttrStrip** for two adjacent logical tile columns; each packed byte stores TL/TR/BL/BR palette groups at bits 0..1/2..3/4..5/6..7. Attribute 7 covers row 14's upper half only (mask `0x0F`); attribute 8 restarts at logical row 15.
5. Separately supplies nominal PPU write addresses: 30 pattern bytes from `$20xx` then 24 from `$28xx`; eight attribute entries from `$23Cx` then six from `$2BCx`. Hardware CIRAM aliases depend on MMC3 `$A000` and are modeled explicitly.
6. Can decode **16×16 indexed background pixels** using an **explicit caller-supplied 8×1KiB physical CHR page vector at fetch time**. This is not a native scanline trace, RGB render, or inferred end-frame mapping. Background 2bpp value 0 is **not sprite transparency**.
7. Can compare caller-supplied private 54-byte and 14-byte buffer captures byte-for-byte with full differences and hashes; the comparison **does not prove capture timing/provenance**.

CLI reports provide source-ROM hashes and expected output sizes; raw patterned bytes are emitted only with `--include-strips`. No PNG/artwork generated or committed.

## Windows reproduction (private ROM only)

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$env:PYTHONPATH = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\src'
$env:SPRITEMINE_TEST_ROM = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
if (-not (Test-Path -LiteralPath $env:SPRITEMINE_TEST_ROM)) {
    throw 'Original private PRG1 ZIP not present'
}
python -m pytest -q tests/test_background.py
python -m spritemine reconstruct-background $env:SPRITEMINE_TEST_ROM --column 0 --half 0
python -m spritemine reconstruct-background $env:SPRITEMINE_TEST_ROM --column 16 --half 1
```

For an **actual verified MesenCE staging capture**, and only if two private raw files exist and were captured for the same logical column / update:

```powershell
Set-Location -LiteralPath 'F:\Dev\ROMMAGE\SOURCE\SpriteMine'
$env:PYTHONPATH = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine\src'
$rom = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
$private = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation'
# Replace the following two placeholders with real verified private capture paths.
# python -m spritemine validate-background $rom '<54-byte-pat-strip.bin>' '<14-byte-attr-strip.bin>' --column 0 --half 0
```

The CLI refuses incorrect capture lengths and reports a nonzero exit status for a mismatch. **No qualifying real 54/14-byte captures have been claimed in this increment.** Runtime captures must remain in FIXTURE, not Git.

## Independently checked private-ROM expectations

Separate read-only inspection of the owner's source ZIP reproduced the accepted logical map SHA `c57b72c77899d596745065c90878327993f9a25e6289c0b22d960c58021b088a` and Plains table digest above. Independent direct table/Tile_Mem calculations produced these source-model fingerprints, now used as opt-in local ROM regression tests:

| Logical column / 8px half | 54-byte pattern SHA-256 | 14-byte attribute SHA-256 |
| --- | --- | --- |
| 0 / 0 | `7cf1d7eb4d234aa4f5e9152bc6b76147b7cb16b2c5d3674519acbfaeeac95bf9` | `7724fed24cee2826840a1934f930cc2e3501ce4f77cdf9c67f5bfd8f14e28e10` |
| 8 / 0 | `15a406545bcdd93afd2e0f14c1ba49d5aae7cbbb2fc9f2be0cb9aaf18588e507` | `db109de9de3cdbfae29f1d665a51fb3d45957818f513fe8677e1de759972eb1c` |
| 16 / 1 | `c0f2eec6558f1cc2867fa9354a4d1a1131a88aeb58a2c5f37e82af378ea3eb0d` | `e337dd9a1999e10e9d1640396d83df5bf78ccd16fa63bac4b51b1c29015b3a1d` |

All hashes here correspond to *modeled* bytes. They are **not** hashes measured from MesenCE Scroll_PatStrip or Scroll_AttrStrip yet.

## Native acceptance gate still required

Use the already successful immutable World 1-1 Raccoon pipe replay/first bonus-room entry.

1. On Windows, instrument the **producer completion points** for `Scroll_DoColumn` and `Scroll_Do_AttrColumn` with a grounded PC-to-PRG-bank identity and read **CPU RAM $0382-$03B7** (54-byte `Scroll_PatStrip`) and **$03BA-$03C7** (14-byte `Scroll_AttrStrip`). Capture `Scroll_LastCol8`, `Scroll_LastAttr`, logical column/direction, page flags, physical CHR banks and CPU cycle/frame. Do not sample both producers only at endFrame.
2. Correlate captured producer metadata with the **correct logical map column and 8px half**; compare source-derived 54/14 bytes with `validate-background`, reporting mismatches rather than forcing a pass.
3. Trace actual NMI commits: `$20xx/$28xx` pattern and `$23xx/$2Bxx` attribute PPU writes. Check the correct MMC3 mirroring from the measured `$A000` bit, not a disassembly prose label.
4. Validate PPU pattern and attribute memory after commits and **active physical CHR pages before the HUD split**, then decode selected native background indexed pixels. RGB comparisons need captured palette RAM, PPUMASK, emulator video filter and overscan settings. A post-IRQ CHR vector is not acceptable evidence for earlier gameplay pixels.
5. Verify read-only A/B/A replay neutrality and keep copyrighted dumps and screenshot outputs under `F:\Dev\ROMMAGE\FIXTURE\SMB3`.

This is the next test, not a license to declare the full bonus-room visual reconstruction complete.
