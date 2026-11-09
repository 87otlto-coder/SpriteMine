# Contributing to SpriteMine

Read [AGENTS.md](AGENTS.md) and [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) before starting. Work is SMB3 PRG1-only until the first milestone is validated.

1. Start from `main`; use `feature/<topic>` for reviewable production changes or `research/<question>` for experiments.
2. Avoid bundling ROMs, game assets, save states or copyrighted extraction output; `.gitignore` is a safety net, not permission to commit.
3. Add deterministic synthetic fixtures for general algorithms; keep actual SMB3 integration tests opt-in via a local path.
4. Run `python -m pytest -q`; test real Windows/emulator behavior separately and report results as observed or pending.
5. Document assumptions and mark `raw`, `captured`, `decoded` data clearly. Update status, roadmap and research log as needed.
6. Open a PR into `main`, include evidence and remaining risks. Do not merge until review/acceptance.

Third-party source must undergo license review before reuse; linking to disassembly research is not license permission.
