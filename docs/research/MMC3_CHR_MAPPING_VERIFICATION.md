# Verified SMB3 MMC3 CHR bank mapping — 2026-11-09

## Evidence and scope

This report records derived technical metadata only. The original SMB3 ROM, graphics, save states and emulator captures stay in F:\Dev\ROMMAGE\FIXTURE, never in GitHub.

Compared independent evidence from three private inputs:

1. Verified Super Mario Bros. 3 ZIP: SHA-256 4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579; whole-ROM SHA-1 6BD518E85EB46A4252AF07910F61036E84B020D1. CHR starts at ROM offset 0x40010 (262160).
2. MesenCE phase probe: frames 136117 and 136118; both show startFrame lower/upper nonzero = 3211/2991, endFrame = 3735/0.
3. MesenCE MMC3 register trace: frames 189263 and 189264; 62 sampled writes, 0 dropped, matching ROM SHA-1. An earlier private capture archive has PPU pattern blobs from frames 29276 and 29277.

The experiments occurred at different moments. Cross-session agreement does not establish identical rendered frame states, but the endFrame captured bytes can be compared exactly to the ROM-derived bank mapping.

## Verified register transitions

The Lua CPU-memory callbacks report writes before they take effect. The model applies the register change after its timestamp when interpreting subsequent events.

- Scanlines 4–5: register selection values 0x46 and 0x47 update PRG registers R6 and R7. Do not classify these as CHR updates.
- Scanline 193, in both sampled frames: bank select values 0x40–0x45 update R0–R5 to **R0=0x5C, R1=0x5E, R2–R5=0x7E**.
- Scanlines 246–247, between the first endFrame and second startFrame: R0–R5 are restored to **0x08, 0x66, 0x53, 0x04, 0x22, 0x32**.
- The bank-select values have bit 7 clear, indicating CHR inversion mode 0: R0/R1 supply two lower 2 KiB regions and R2–R5 supply four upper 1 KiB regions. Bit 6 set means PRG mode 1; it is not the CHR mode bit.

See the NESdev MMC3 reference: https://www.nesdev.org/wiki/MMC3 . R0/R1 ignore bit 0, so their source 2 KiB banks are even-aligned.

## Byte-accurate PPU-to-ROM reconstruction

| PPU 1 KiB slot | StartFrame CHR 1 KiB bank | EndFrame CHR 1 KiB bank |
|---|---|---|
| $0000–$03FF | 0x08 | 0x5C |
| $0400–$07FF | 0x09 | 0x5D |
| $0800–$0BFF | 0x66 | 0x5E |
| $0C00–$0FFF | 0x67 | 0x5F |
| $1000–$13FF | 0x53 | 0x7E |
| $1400–$17FF | 0x04 | 0x7E |
| $1800–$1BFF | 0x22 | 0x7E |
| $1C00–$1FFF | 0x32 | 0x7E |

CHR bank 0x7E is entirely zero-filled in the verified ROM. Mapping it into all four upper 1 KiB regions causes the endFrame upper pattern space to be blank.

| Measurement | MesenCE observed | Rebuilt from ROM |
|---|---:|---:|
| Start lower 4 KiB nonzero | 3211 | 3211 |
| Start upper 4 KiB nonzero | 2991 | 2991 |
| End lower 4 KiB nonzero | 3735 | 3735 |
| End upper 4 KiB nonzero | 0 | 0 |

The rebuilt **entire 8192-byte endFrame PPU pattern image** matches each captured PPU image from older frames 29276 and 29277 **byte for byte**:

- Rebuilt and captured endFrame PPU SHA-256: 0596b1b2055a68f9bf2af5c6aad9954f32821ad85deb6294eedeefba44346918.
- Rebuilt startFrame PPU SHA-256: ff1fed9ebea0ff45c17ae1ddb93bf3205ee591438cc8d45af83167a80d4f69b5. This startFrame hash has not yet been compared with a captured full startFrame PPU image.

This establishes the physical ROM source banks underlying the observed **boundary states**, not the rendered visibility of every sprite on every scanline.

## Reproducible read-only analysis

Use research/mesence/decode_mmc3_trace.py on the research branch. It models 8 PPU slots from timestamped mapper writes, reports source CHR and absolute ROM offsets, nonzero counts, and a reconstructed PPU hash. It neither exports graphics nor modifies the ROM. It rejects mismatched SMB3 SHA-1/SHA-256.

PowerShell, with paths adjusted to the actual local ROM and latest captured trace:

~~~powershell
Set-Location -Path "F:\Dev\ROMMAGE\TOOLS\SpriteMine-research"
git pull --ff-only origin research/smb3-emulator-feasibility

$trace = Get-ChildItem -Path "F:\Dev\ROMMAGE\FIXTURE\SMB3\MesenCE" -Filter "mmc3_trace_*.json" |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName

$rom = "F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip"   # Update if your ROM is in a different FIXTURE subfolder.
py -3.12 ".\research\mesence\decode_mmc3_trace.py" $trace --rom $rom
~~~

To compare against a private capture archive without extracting or emitting game graphics, append --capture-zip with the actual full archive path. The utility compares SHA-256 hashes only.

## Remaining acceptance criteria

1. Capture a **full 8 KiB startFrame PPU image** and check its SHA-256 against the predicted hash. Count agreement alone is not byte-level verification.
2. Determine graphics/OAM sampling coherence at the actual rendering scanline. StartFrame does not automatically prove all visible sprite pixels were derived from that mapping.
3. Reconstruct Mario's relevant hardware sprite components using CHR source mapping, accurate palettes, flips, transparency and priority, and compare against observed screen pixels.
4. Record emulator build/version, savestate and input replay identifiers.

**Verified:** phase-dependent PPU mapping, ROM-backed physical bank assignments at sampled boundaries, and exact endFrame PPU bytes. **Not verified:** pixel-perfect Mario rendering, same-frame reconstruction, or full game asset coverage.

## Controlled next validation (2026-11-10)

The integrated research recorder spritemine_phase_capture.lua and verifier verify_phase_capture.py now permit the predicted *full* startFrame 8 KiB PPU SHA-256 to be tested using registers and PPU snapshots from one emulator session. Unlike previous cross-session evidence, the second startFrame can be mapped from the observed intervening MMC3 register writes; the first startFrame may have unknown pre-existing state.

This integrated experiment is **not yet validated in MesenCE on Windows**. If the second pre-render snapshot hash matches, it strengthens the physical-bank reconstruction evidence but still does not prove the sprite render phase, palette fidelity or screen-pixel correspondence.
