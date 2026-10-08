# Aura Archive Cleanup - 2026-10-08

## Scope

This cleanup moves historical artifacts out of the active Aura project root while keeping them recoverable outside the repository.

## Archive Locations

- `C:\AI Project\Codex\Aura_archive_20261008_untracked`
- `C:\AI Project\Codex\Aura_archive_20261008_tracked_and_ignored`

Each archive folder contains a `MANIFEST.txt` with the original relative paths.

## What Was Archived

- Hash-suffixed duplicate snapshots.
- One-off debug and repair scripts.
- Generated screenshots and visual test captures.
- Old Superpowers brainstorm/spec artifacts.
- Legacy JavaScript browser smoke scripts that are not part of the current release gate.
- Ignored historical outputs such as old hashed logs, screenshots, and database copies.

## What Was Preserved In The Active Root

- Runtime backend files: `main.py`, `models.py`, `schemas.py`, `database.py`, `services.py`.
- Current HTML pages and primary static assets.
- Current automated regression suite run by `run_tests.py`.
- Deployment and CI files.
- Product and engineering documentation.
- Local-only runtime data such as `.env`, current `aura_db.db`, `uploads`, and virtual environments.

## Verification

After cleanup, run:

```powershell
$env:AURA_TEST_DATABASE_URL="sqlite:///C:/Users/caoyixiong/Documents/test/aura_pytest_archive_cleanup.db"
.\venv\Scripts\python.exe run_tests.py
```

Expected result: all release-gate tests pass.
