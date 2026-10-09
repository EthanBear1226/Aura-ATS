# Aura Online Acceptance Checklist

Use this checklist after each deployment to verify that the hosted site matches the local release.

## 1. Authentication And Security

- Open `/api/candidates` without a token. Expected: `401`.
- Open `/api/jobs` without a token. Expected: `401`.
- Open `/api/approvals/pending` without a token. Expected: `401`.
- Open `/portal.html?job_id=1` without login. Expected: public job page loads.
- Open `/api/public/jobs/1` without login. Expected: `200` and complete job data.

## 2. Candidate Management

- Log in as `hr@example.com / 123456`.
- Open `candidates.html`. Expected: candidate list renders without blank page.
- Confirm there is no fake `按分组查看`, fake `排序规则更新`, or toast-only view switch.
- Collapse and expand the job sidebar. Expected: actual layout width changes and state persists after refresh.
- Select a candidate and advance stage. Expected: card/list state changes and detail log records the action.
- Try advancing a terminal candidate. Expected: blocked with clear message unless using re-enter flow.

## 3. Candidate Detail

- Open several different candidate IDs from the list. Expected: name, resume, logs, and fallback data do not cross over between candidates.
- Verify resume preview states: successful PDF, missing file fallback, and unsupported/missing state copy.
- Toggle sensitive fields as an authorized user. Expected: masked by default, clear only after explicit toggle.
- Add a note. Expected: new timeline/log entry appears after saving.

## 4. Offer Approval

- Open settings and fetch Offer field configuration. Expected: `200`, no `422`.
- Launch an Offer approval from a candidate. Expected: pending approval instance is created.
- Open `/api/approvals/pending` as current approver. Expected: `200`, array response, no serialization error.
- Open `/api/approvals/my-launches` as launcher. Expected: launched approval is listed.

## 5. Public Portal

- Open `/portal.html?job_id=1`. Expected: job responsibilities, requirements, location, salary, and application instructions are present.
- Try non-PDF upload. Expected: rejected.
- Try a PDF over configured size limit. Expected: rejected.
- Submit to a closed or deleted job. Expected: rejected before resume parsing.
- Submit the same active applicant to the same open job twice. Expected: second submission returns a clear duplicate-application error.
- Submit a valid PDF. Expected: success state and a candidate/application record in the admin side.

## 6. Settings And Permissions

- Log in as an admin. Expected: settings CRUD is available.
- Log in as non-admin/recruiter. Expected: settings mutation returns `403`.
- Log in as interviewer. Expected: job creation returns `403`.

## 7. Visual Sanity

- Check `1280px`, `1440px`, and wide desktop layouts.
- Candidate cards should not overflow action buttons.
- Job cards should keep button text inside stable dimensions.
- Unrelated pages must not show the interview scheduling drawer by default.

## Release Decision

Only ship when:

- Local `run_tests.py` passes.
- The online checks above pass against the deployed URL.
- No browser console errors appear during login, candidate list, candidate detail, settings, and portal flows.

## Latest Online Check - 2026-10-08

Target: `https://aura-ats.zeabur.app/`

Result: blocked by deployment availability. The following paths all returned Zeabur `502: SERVICE_UNAVAILABLE`:

- `/`
- `/api/candidates`
- `/api/jobs`
- `/api/approvals/pending`
- `/api/public/jobs/1`
- `/portal.html?job_id=1`
- `/login.html`

Observed message: the service is not responding, likely because the app is not listening on the expected port or the service crashed.

Follow-up:

- Check Zeabur runtime logs for startup exceptions.
- Confirm `PORT` is passed to `main.py` and the app binds `0.0.0.0`.
- Re-run this checklist after the deployment becomes reachable.

## Deployment Hardening - 2026-10-08

Local follow-up completed:

- Added `.dockerignore` so Zeabur/Docker builds do not package local virtual environments, SQLite databases, uploads, logs, screenshots, or historical tool artifacts.
- Added `/healthz` to expose app/database readiness.
- Wrapped initial `create_all` startup work so a temporary remote database problem is printed and diagnosable instead of hiding behind an import-time crash.

After GitHub deployment finishes, verify:

- `GET /healthz` returns `{"status":"ok","database":"ok"}`.
- `GET /login.html` loads the login page instead of Zeabur 502.
- If `/healthz` returns `503`, inspect `detail` and Zeabur database environment variables first.
- If Zeabur does not use the Dockerfile path, `zbpack.json` pins Python `3.11`, `main.py`, and `pip` as the fallback Python build configuration.
- Running `python main.py` now disables uvicorn reload by default; set `AURA_RELOAD=true` only for local development.

Recheck after commits `351072c` and `a924c72`: `/healthz`, `/login.html`, and `/api/public/jobs/1` still return Zeabur `502: SERVICE_UNAVAILABLE`. The request does not reach the FastAPI app, so the next required artifact is Zeabur build/runtime logs.

Runtime log root cause found: `database.py` imported `sqlalchemy_utils`, which crashed on Zeabur with `AttributeError: module 'sqlalchemy.orm.attributes' has no attribute 'ScalarAttributeImpl'`. The dependency was removed and MySQL database bootstrap now uses native `pymysql`.
