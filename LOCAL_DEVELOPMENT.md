# Fixed Local Development Entry

Use `http://127.0.0.1:8128/candidates.html` throughout frontend development.
Candidate IDs refer to the same existing test backend, including previously
uploaded resumes. Do not start the synthetic preview server on this port again.

## Start

Keep the existing SSH tunnel at `127.0.0.1:18000` running, then run:

```powershell
.\venv\Scripts\python.exe dev_server.py
```

`dev_server.py` serves HTML, JavaScript, CSS, and icons directly from this
checkout with caching disabled. Refresh the same browser tab after editing.
It forwards `/api/*` and `/healthz` through the existing SSH tunnel. Log in with
the existing test backend account if prompted.

## Data Ownership

- This is a local frontend with the existing server-side test data, not an
  offline local database. Creating, editing, or deleting records updates that
  test backend. Uploaded files remain on the test server.
- The launcher does not import `main.py`, seed demo records, reset databases,
  or copy, merge, or migrate candidate IDs.
- Keep the SSH tunnel alive. A failed tunnel does not mean data was deleted;
  restore the tunnel and refresh.
- Local backend Python changes are not used in this frontend-only mode.
  A fully offline backend requires a separate verified database and uploads
  backup. Do not substitute the old local `aura_db.db` or the synthetic preview
  database for the existing test data.
- The gateway binds only to `127.0.0.1`. Only loopback upstream origins are
  accepted. Credentials, databases, and uploaded resumes must not enter Git.

## Verify

```powershell
.\venv\Scripts\python.exe run_tests.py
```

The gateway tests use a mocked backend. They do not write to the existing
test server.

`candidate-resume-check.cjs` uses mocked API responses by default. Its optional
`AURA_SYNTHETIC_PREVIEW_URL` must point to a separate synthetic-only QA server,
never the fixed `8128` development entry with existing candidate data.
