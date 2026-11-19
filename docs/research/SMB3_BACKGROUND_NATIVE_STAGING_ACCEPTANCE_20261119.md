# SMB3 PRG1 — Native bonus-room CPU background staging acceptance (2026-11-19)

**Result: PASS — limited to first-entry World 1-1 bonus-room CPU staging buffers.**

This is a checkpoint of the owner's **Windows PowerShell output**, reviewed on 2026-11-19. The primary binary captures and ROM were **not independently accessed or rerun** in this GitHub documentation update. The original evidence remains private under:

`F:\Dev\ROMMAGE\FIXTURE\SMB3\RuntimeInvestigation\pipe-replay-hb6hmzft`

The original failed native run `pipe-replay-ih9zjv6r` also remains private; after the signature fix, its common A/B/A evidence was checked offline and had **zero genuine differences** for B and A2. The first failure arose because the comparator included B-only `bg-*-tiles.bin` diagnostic files in otherwise common evidence. This was corrected and regression-tested in [PR #23](https://github.com/87otlto-coder/SpriteMine/pull/23) at commit `58fe97aca8f7a99771e98dc0e2bbc53acc71c033` (this is the checkout used for the successful Windows run).

## Windows acceptance results

| Check | Observed |
| --- | --- |
| Git checkout | `58fe97a`, clean detached worktree `SpriteMine-Background-Validation` |
| Private-ROM full pytest | **40 passed**, 0 failures, 0 skips, 1.10 seconds |
| Controller replay | 2,590 polls, verified SHA-256 below |
| Replayed emulator frames | 450778–450881 inclusive |
| Normal A/B/A common evidence | `neutral: true` |
| Detailed B-only staging events | **66 recorded** |
| Pattern events accepted | **32 × 54 = 1,728 bytes** |
| Attribute events accepted | **32 × 14 = 448 bytes** |
| All source-modeled CPU bytes compared | **2,176 of 2,176 matched**, zero mismatches |
| Destination metadata mismatches | **0** |
| Events excluded for non-bonus / modified logical map | **2** (not counted as matches) |
| Native verifier result | `passed: true`, `missing_evidence: []` |
| Renderer acceptance | `native_final_ppu_or_rgb_verified: false` |

The native verifier's declared scope is `first-entry bonus logical map -> CPU PPU staging buffers`. This meets the narrowly defined PR #23 acceptance gate: at least one eligible native pattern and attribute producer, matching source-model bytes, consistent event metadata and a neutral A/B/A replay. It does **not** validate PPU commits, hardware nametable bytes, CHR mapping during visible fetches, palette/RGB, or arbitrary level/scroll paths.

## Evidence fingerprint inventory (SHA-256)

The replay report records the following six source hashes; these are identifiers and **not** copies of private assets:

| Source | SHA-256 |
| --- | --- |
| Verified USA PRG1 ROM image | `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579` |
| MesenCE executable | `8ef403d6b9af32075416193914d7993ce8480b347fe1f20a0cfd9815374933e7` |
| Starting private slot copy | `31f5f5ae97d9f8c5d8aa3fded0c6a2d64f2c19c9fedad1d7237d81d264d759f2` |
| 2,590-poll controller input | `f780c7ba7e5002f9a62161486ad29e978106588571f6bf8eb268bd909681d082` |
| MesenCE settings | `a76dbd831587ce0430faf626aa994c916696deac6d2d322b457c78a0a6586c1d` |
| Base replay Lua | `08f7ebcb3e2a366a5e0d5a6e081b25dd8781a8d291979ab5aa323fe2946e67ca` |
| Background producer Lua observer | `7f4c75f8219d041d35560c9f17decffcb0657b8a8a310f81eadf5d3da43636d9` |
| Private `background-staging.tsv` | `a3805eb9e64efc3d328d25380846be53661f944db3b6d605702753ec0cf4030a` |

The replay report also records per-frame `trace.tsv`, `controller.tsv`, Tile_Mem and RGB hashes; these remain inside the private capture's report and were not exhaustively copied into this public research note.

## Provenance and limitations

- The owner executed the unmodified controller-only replay with sprites enabled and captured detailed producer data in the B leg. The runner compared common controller/timing/Tile_Mem/RGB evidence for A, B and A2 before reporting `neutral: true`.
- The detector collected the 54-byte `Scroll_PatStrip` and 14-byte `Scroll_AttrStrip` **after producer completion**. The verifier only counted events with the accepted bonus logical-map fingerprint, and handled PRG030 scroll-direction-dependent attribute source columns.
- The standalone verifier reported `capture_metadata_consistent: true`, **32 pattern checks, 32 attribute checks, 2 skipped events, zero byte or metadata discrepancies**.
- The owner-provided shell output, rather than independently mounted raw captured buffers, is the evidence for this checkpoint. Do not describe this as a second independent MesenCE verification.
- Hosted Windows CI for the preceding implementation at [run 44483355680](https://github.com/87otlto-coder/SpriteMine/actions/runs/44483355680) passed Python 3.11 and 3.12 with **36 passed, 4 private-fixture skips** each; it is not a native capture.
- No ROM, savestate, graphics or private buffers are committed. Follow the reproduction procedure in [SMB3_BACKGROUND_NATIVE_STAGING.md](SMB3_BACKGROUND_NATIVE_STAGING.md).

**Next gates:** independently validate the staged-buffer-to-PPU write sequence and CIRAM alias state; record fetch-time MMC3 CHR mapping and background palette across gameplay/HUD transitions; compare indexed/rendered background pixels with a synchronized MesenCE reference. Do not promote the current staging gate to full visual World 1-1 reconstruction.
