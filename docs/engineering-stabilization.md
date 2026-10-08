# Aura Engineering Stabilization Plan

## Current Priority

Aura is moving from demo-quality iteration to a productized ATS baseline. The immediate goal is to keep every release testable, secret-safe, and easy to review.

## Release Gate

Run this before every deployment:

```powershell
$env:AURA_TEST_DATABASE_URL="sqlite:///C:/path/to/aura-test.db"
.\venv\Scripts\python.exe run_tests.py
```

The test runner refuses non-SQLite databases so local and CI runs cannot accidentally reset a shared MySQL/PostgreSQL database.

## Repository Hygiene

Do not delete historical artifacts blindly. The repo currently contains many generated snapshots, duplicate timestamped files, screenshots, and old reports. Recommended cleanup flow:

1. Move historical screenshots and duplicate generated files into an archive folder outside the active app root.
2. Keep canonical runtime files only: `main.py`, `models.py`, `schemas.py`, `database.py`, `services.py`, primary HTML pages, tests, docs, and deployment config.
3. Keep `.env` local-only. Commit `.env.example` instead.
4. Keep uploaded resumes and generated SQLite databases out of Git.

## Current Automated Coverage

- Auth/security gate for internal APIs.
- Public job detail access without login.
- Candidate transition and terminal-stage protection.
- Offer fields route conflict regression.
- Offer pending and my-launches serialization.
- Settings CRUD smoke tests.
- Role permission checks for settings and job creation boundaries.
- Candidate detail RBAC, including interviewer assignment and hiring-manager department isolation.
- Candidate sensitive fields masked by default and explicit reveal limited to authorized HR/admin roles.
- Offer approval detail/action ownership checks.
- Public resume upload rejects non-PDF files and oversized PDFs.
- Deployment health check verifies app/database readiness via `/healthz`.
- Frontend static checks for fake controls and stray interview drawer mounts.

## Next Coverage Targets

- Public application submission: duplicate applicant and closed job behavior.
- Browser-based online acceptance after the hosted Zeabur service is reachable.
- Interview scheduling and feedback submission.
- Candidate detail sensitive-field access audit trail.
