# M1 — First compiled World 1-1 creative stage GIF

**2026-11-22:** A genuinely playable GIF has been produced from the owner's original Super Mario Bros. 3 US PRG1 ROM and existing MesenCE private capture. The editable headless compositor is implemented. **Owner Windows F: regeneration and subjective wallpaper approval are pending.**

## Actual private deliverables

- `World11_Stage_Loop.gif`: **48 frames**, **1024×576** pixel-perfect 2× output, **80ms/frame** (3.84 seconds), **infinite loop**. SHA-256 `5657ebb5952c6ae27a9bbe258f02a79cae8bf6d06ff545cc7c9fc1c43c228efa`.
- `World11_Source_Metatiles.png`: **browsable contact sheet of all 256 original Plains graphics**, identified by hexadecimal tile ID.
- `World11_Stage_Recipe.json`: editable canvas, layer, position and per-object timing recipe, labelled **composed/edited**.
- `World11_Stage_Preview.png`, `World11_Stage_Frames.png`, `World11_Stage_QA.json`: inspection previews and evidence.

The actual exported GIF was decoded as 48 frames with loop=0 and stable timing. A second rebuild produced the identical SHA-256. On the 1024×576 full GIF, the 47→0 loop seam changed **2,096 pixels**, versus **2,100** at the largest other adjacent frame transition: no unusual frame-wide reset. The rendered preview and 12-frame contact sheet were inspected for composition, stable camera, palette, layering and animated elements. This is a **creative prototype**, not final owner aesthetic acceptance or a Windows native re-run.

## What makes the scene

- Exact original SMB3 PRG1 image SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`.
- Original Plains 256×4 quadrant table at ROM offset `0x1E010`, SHA-256 `c19dfefb08bfdebaa2be3bce01abc590865da46f804ccd36f4b9d96db1bf9362`.
- Real ROM CHR pages **8, 9, 100, 101**, independently matched to the private frame 450840 PPU debug snapshot. The renderer decodes graphics from the **original ROM**, not copied screenshot tiles.
- MesenCE captured pipe at frame **450840**, Raccoon Mario poses at **450778 and 450786**, bonus-room coin at **450881**; palette RAM captured at 450840 and default pinned MesenCE 2C02 RGB profile supplied locally.
- Artist-composed stage section: fixed sky, greenery, original tiles for blocks and terrain, two green pipes and composed clouds. Independently animated objects: **two question blocks**, **three spinning/bobbing coins**, **Mario bobbing and changing poses**.

The layout, decorative clouds, coin spins and Mario motion are **creative composition**, not original World 1-1 game-object positions/timing or full level decoding. No emulator run, input replay or ROM modification was required for this prototype.

## Windows PowerShell 5.1 — regenerate from the existing private evidence

Use the owner's original ROM and established local replay directory. The palette source file was downloaded during the preceding native background RGB verification; do not copy the GPL source into the GitHub repository.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $root = 'F:\Dev\ROMMAGE\SOURCE\SpriteMine-Background-Validation'
    $python = Join-Path $root '.venv\Scripts\python.exe'
    $rom = 'F:\Dev\ROMMAGE\FIXTURE\Super Mario Bros. 3.zip'
    $capture = 'F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-xbhs6ijw'
    $palette = 'F:\Dev\ROMMAGE\TOOLS\MesenCE-Source\NesDefaultVideoFilter-20ba206c.cpp'
    $output = 'F:\Dev\ROMMAGE\OUTPUT\SMB3\World11StageM1'

    foreach ($path in @($root, $python, $rom, $capture, $palette)) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Missing: $path" }
    }
    Set-Location -LiteralPath $root
    if (git status --porcelain) { throw 'Worktree has uncommitted changes.' }
    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw 'Fetch failed.' }
    git switch --detach origin/feat/m1-world11-creative-stage-gif
    if ($LASTEXITCODE -ne 0) { throw 'Checkout failed.' }

    $env:PYTHONPATH = Join-Path $root 'src'
    $env:SPRITEMINE_TEST_ROM = $rom
    & $python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Regression tests failed.' }

    New-Item -ItemType Directory -Force -Path $output | Out-Null
    & $python -m spritemine.stage_gif --rom $rom --capture $capture `
        --rgb-profile $palette --output $output
    if ($LASTEXITCODE -ne 0) { throw 'GIF build failed.' }
    $gif = Join-Path $output 'World11_Stage_Loop.gif'
    if (-not (Test-Path -LiteralPath $gif)) { throw 'Output GIF missing.' }
    Get-FileHash -LiteralPath $gif -Algorithm SHA256
    Invoke-Item -LiteralPath $gif
}
```

Expected: one real 1024×576, 48-frame looping GIF, a 256-tile contact sheet, 12-frame contact preview, edited recipe and private QA report under `F:\Dev\ROMMAGE\OUTPUT\SMB3\World11StageM1`.

To edit the stage, change `World11_Stage_Recipe.json` positions or tile IDs and rerun with `--recipe F:\Dev\ROMMAGE\OUTPUT\SMB3\World11StageM1\World11_Stage_Recipe.json`. Animation periods must divide the total 48 frames to wrap cleanly. This is a deliberately bounded creative stage section, not a generic timeline framework.

## Acceptance status

- [x] **Playable GIF actually produced**, visually checked preview, 48 decoded frames, seamless cyclic schedules and reproducible same-environment SHA-256.
- [x] Original-ROM graphics and captured character/coin assets used; editable creative composition recipe; visible multiple independent animation layers.
- [x] Fixture-free local Python tests passed (8).
- [ ] Hosted Windows CI and owner F: native regeneration.
- [ ] Owner reviews GIF playback and approves the aesthetics or requests revisions.

**Do not start M2 audio or claim complete M1 until the owner has reviewed this actual GIF.** Retain old research evidence but do not dive deeper into ROM mechanics for minor visual edits. No game data, rendered GIF, raw capture or GPL third-party C++ is committed to public GitHub.