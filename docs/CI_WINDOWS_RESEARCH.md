# Windows-only research CI policy integration

Date: 2026-11-12. Source: docs/ACTIONS_INCIDENT_2026-11-11.md.

The main branch already uses only Windows GitHub-hosted runners. This research
branch had retained an Ubuntu-based Lua mock workflow and a four-job
Windows/Ubuntu Python matrix, with repeated branch-push + PR triggers.

Changes to the research CI:
- Python: Windows 3.11 and 3.12 only, on PRs; main branch pushes still run
  on the main branch after integration. No feature/research branch push jobs.
- Lua: Windows 5.4.8 with MSVC and maintained leafo/gh-actions-lua v13,
  deliberately configured with no build cache. No apt, POSIX shell, Bash
  heredocs or /tmp paths. Third-party Actions are installation dependencies,
  not vendored MesenCE source.
- research/mesence/ci_mock_checks.py is a synthetic-only Python runner:
  it checks the syntax of existing Lua probes, executes all five emulator
  stand-ins, regenerates the same synthetic MMC3 bank fixture, checks the
  same 8KiB mapping/frame/cycle/ROM assertions, validates the rendered RGB
  source index agreement and runs the original diagnostic CLIs.
- No game ROMs, capture graphics or save states are uploaded or committed.
- The Python tests job owns pytest; Lua checks don't re-run the full pytest
  suite in a second hosted job. Jobs have read-only GitHub contents permission.
- Workflow concurrency cancels superseded PR runs on the same branch.

Implementation is not a claim that the emulator integration works on real
Windows: only the existing private MesenCE captures establish that. Hosted
Windows Actions success is required before merging these CI changes.

Research PR layering:
1. Maintenance PR into research/smb3-emulator-feasibility (this change).
2. Refresh outstanding PR #5 graphics-harness branch with the approved policy
   before any base merge; preserve its complete A/B/A tests.
3. Refresh stacked draft PR #6 animation-timeline branch the same way.
4. Refresh open GUI PR #4 independently before merging into main because its
   feature workflow still includes Ubuntu and branch-push triggers.
5. Update main README and STATUS to reflect the foundation merge and branch
   research evidence, without claiming unmerged code is in main.

Existing research status: docs/PROJECT_STATUS.md keeps detailed SMB3 evidence.
Hosted CI can verify the synthetic tests, not owner-private ROM/state captures.
