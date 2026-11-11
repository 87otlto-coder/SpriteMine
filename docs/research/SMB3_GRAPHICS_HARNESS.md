# SMB3 PRG1 graphics validation on Windows

The harness starts three fresh MesenCE processes for each input plan. A and A2 show sprites. B hides them. The default plan keeps both controllers neutral. The target is the 16×16 region formed by the observed 8×16 OAM entries 10 and 11 for this slot. Other states may use different entries.

## One-time setup

The original ROM ZIP belongs in F:\Dev\ROMMAGE\FIXTURE. Mesen.exe belongs in F:\Dev\ROMMAGE\TOOLS\Mesence. Keep a research checkout alongside the main checkout in SOURCE. In MesenCE's Script Window, allow script I/O and OS access so the trusted local probe can read the copied state and write captures. Network access is unnecessary. Use the unfiltered native NES display and default 2C02 palette.

~~~powershell
Set-Location F:\Dev\ROMMAGE\SOURCE
git clone --branch research/smb3-graphics-harness https://github.com/87otlto-coder/SpriteMine.git SpriteMine-graphics
Set-Location F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics
py -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
~~~

## Slot and display semantics

The owner confirmed SMB3 in slot 1. Selecting a slot only changes the current index. Loading restores the selected state. Saving to a named file serializes the machine at the time of saving, which can be later than the original slot. For a byte-exact copy, locate the existing slot backing file in the configured SaveStates folder and let the runner copy it. Portable installations and directory overrides can change its location. Never use Save State to slot 1 as a setup step.

The installed executable reported version 2.2.1+20ba206cef5ba207c21203176d02cb9f43dda9fb. Its slot filename uses the ROM basename followed by the slot number. On this machine the actual slot backing file and a separate named export were both present. Only the slot backing file was used. The loader restores console state, can stop active movie playback, and can show a saved framebuffer when paused. A screenshot taken immediately after loading cannot establish the replayed display setting. [SaveStateManager.cpp](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Shared/SaveStateManager.cpp)

Settings > NES > Video > Disable sprites binds to NesConfig.DisableSprites. The CLI option sets the same configuration property. The renderer receives the inverse SpritesEnabled flag. The harness launches with the option set before loading the copied state, captures after advancing, then repeats with sprites enabled. Slot bytes remained identical throughout the experiment. The observed B screen changed while the enabled full screens repeated. The GUI itself was not clicked during this test. [NES settings view](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Views/NesConfigView.axaml) · [NES configuration](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Config/NesConfig.cs)

## Reproduce from the observed slot

~~~powershell
Set-Location F:\Dev\ROMMAGE\SOURCE\SpriteMine-graphics
$slot = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'MesenCE\SaveStates\Super Mario Bros. 3_1.mss'
if (!(Test-Path -LiteralPath $slot -PathType Leaf)) { throw 'Locate slot 1 in the configured MesenCE SaveStates folder.' }
foreach ($plan in 'neutral','right','jump') {
    .\.venv\Scripts\python -m research.mesence.graphics_harness --slot $slot --plan $plan
    if ($LASTEXITCODE) { throw "Inspect the private report and emulator log for $plan." }
}
~~~

Each invocation prints a new private directory below FIXTURE\SMB3\GraphicsValidation. Open report.html there. It shows enabled / disabled / enabled and the absolute per-channel RGB difference between A and B. report.json provides ROM, state, executable, capture-script and rendered-frame identities, palette comparisons, physical CHR tile offsets, controller evidence, and all four boundary records. To recheck an existing run, pass its printed directory to python -m research.mesence.graphics_report. Keep the entire directory private.

The headless runner loads the script before resuming. Lua restores the exact private slot bytes at the first main-CPU exec callback, requires a successful return, and records the restored frame and clock. Two complete frames are captured after a common 60-poll neutral settling period and an eight-frame delay. Right is held after poll 60. Jump holds A on polls 61–66. An optional diagnostic Start pulse changes the plan and is excluded from the results below. This build exports emu.stop for test-run completion. [TestRunner.cs](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Utilities/TestRunner.cs) · [Lua bindings](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/Core/Debugger/LuaApi.cpp)

**Input discovery.** Overrides applied only at inputPolled passed Lua readback but delivered neutral CPU-bus data in the movement trials. Applying the same pad state again at the game's controller strobe produced the intended serial input at $4016, repeatable movement, and unchanged neutral $4017 reads. The probe observes the actual reads without replacing their values. The verifier checks the first and last complete eight-bit reports at each poll and compares the full bus history across legs.

## Observed proof gates, 2026-11-10

All three experiments restored frame 448316 at reported master clock 466140497. Their target was frame 448385. For each plan, both enabled frame buffers repeated at both measured endFrame boundaries. The three legs agreed on ROM-backed MMC3/CHR, OAM, palette, nametable data, sampled PPU scalar fields, timing, controller and register-write histories. Each 8-pixel control ring matched at 768/768 positions.

| Captured input and observation | Target origin | Opaque RGB | Transparent equals B | Status |
|---|---|---:|---:|---|
| Neutral, stationary on block | (127,98) | 138/138 | 118/118 | verified |
| Right, horizontal movement and tile change | (128,98) | 138/138 | 118/118 | verified |
| A, upward movement and jump tiles | (127,73) | 194/194 | 62/62 | verified |

For neutral, visible tile bytes begin at whole-ROM offsets 347216, 347232, 347248 and 347264. Walking uses the same two tile pairs in the opposite OAM order with horizontal flipping. Jumping uses 347536, 347552, 347568 and 347584. The phase verifier independently reconstructs the physical CHR mapping and verifies the mapped 8192 bytes at the target start. The independent default-2C02 reference maps captured palette RAM entries for indices 1–3 to RGB. The three supported NES codes are 0x16 (#B53120), 0x36 (#FECCC5) and 0x0F (#000000). [Palette source](https://github.com/nesdev-org/MesenCE/blob/4b8a196e299b3de297b204fd1208d2981562c89b/Core/NES/NesDefaultVideoFilter.cpp)

- Slot SHA-256: 31f5f5ae97d9f8c5d8aa3fded0c6a2d64f2c19c9fedad1d7237d81d264d759f2.
- Executable SHA-256: 8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7.
- Neutral A/A2 SHA-256: 3dfa94b2cfdaee31b7df9a390000b367dc8f4fe2eb6437f857035a5b9e10cd29. B: 1f7e88184df0d4d1dd645042a1adc41f6cccba2e2e239ecc49af428ec17c4cbc.
- Neutral timing SHA-256: 36472fc5d32a110798760eb4b83135559488a7ce6ba44ad45c5b2218a1929105.

Verified covers these sampled frames. Failed means an observed mismatch or required evidence check failed. Unsupported includes behind-background priority and unsupported render modes. Not tested includes sprite-limit contention, other characters, full animation cycles, per-scanline fetch equivalence, and audio. The first boundary can have unknown MMC3 registers until the trace observes their initialization. Preserve that distinction when reviewing the four snapshots. MesenCE remains a locally installed external GPL emulator; this repository distributes original probes and analysis only.
