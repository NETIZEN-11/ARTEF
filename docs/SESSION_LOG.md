# ARTEF Session Log

Live log of work on this repository (times in IST). Read CURRENT STATE and NEXT STEPS first.

## CURRENT STATE (2026-11-20 IST)

- Branch `fix/remove-placeholder-data` (fork `Harishrs2006/ARTEF`), merged with the latest
  `NETIZEN-11/main` (722306f). PR #4 open: https://github.com/NETIZEN-11/ARTEF/pull/4
- Merged earlier: PR #1 (core pipeline), PR #2 (credits), PR #3 (benchmarks, analytics, runs list).
- Checks on the merged branch: 256 backend tests pass, ruff CI gate passes, frontend
  typecheck/lint/31 tests/build pass.
- Local run: `scripts\start_dev.ps1` starts API :8000, demo agents :9005/:9006, website :3002.
  Login `admin`, password = `SEED_ADMIN_PASSWORD` in `backend\.env` (rotated 2026-10-24).
- Local database has the suite "Seeded Regressions" for the viva demo.
- Viva preparation: `docs/VIVA_GUIDE.md`.

## NEXT STEPS

1. Get PR #4 reviewed and merged by Nitesh (NETIZEN-11).
2. Ask Nitesh for the cloud URLs (Vercel frontend, backend host) and whether the cloud admin
   password that was printed in `scripts/start_dev.ps1` has been changed.
3. Rehearse the demo in `docs/VIVA_GUIDE.md` section 10 once before the viva.
4. Optional: live LLM judge with an API key (`EVAL_MODE=provider`), "any keyword" matcher mode.

## LOG

- 2026-10-12: PR #1 fix/core-pipeline merged (pipeline, gate, tests, CI, Docker, README).
- 2026-10-21: PR #2 credit both authors merged.
- 2026-10-22: PR #3 feat/demo-polish: real benchmarks, analytics from stored data, runs list
  names and gate, Windows start script; merged NETIZEN-11/main without losing PR #1/#2 work.
- 2026-10-24: Rotated leaked local demo passwords, SECRET_KEY and agent token (local SQLite and
  Docker PostgreSQL). Found and fixed fake features: MCP proxy invented replies, custom
  guardrails unused, security events never recorded, Grafana dashboard with no metrics,
  invented figures on the landing page.
- 2026-11-19 14:00 IST: Committed the 2026-10-24 fixes in 4 commits; merged 34 new upstream
  commits (cloud deployment, demo agent ports 9005/9006, contact admin dialog); no conflicts.
- 2026-11-19 14:15 IST: Aligned local demo ports (dev_setup.py, demo agent default, README,
  local .env and database agents) with start_dev.ps1; removed a cloud admin password hint
  from start_dev.ps1. Added "Seeded Regressions" suite to the local database for the demo.
- 2026-11-19 14:25 IST: Added docs/VIVA_GUIDE.md (project summary, architecture, flow, run
  steps in VS Code, demo script, 40 practice questions) and this log.
- 2026-11-20 IST: Opened PR #4 (fix/remove-placeholder-data) into NETIZEN-11/ARTEF:main; asked in the PR to rotate the cloud admin password.
