# Fixed Local Development Entry

Use `http://127.0.0.1:18000/candidates.html` throughout frontend development.
The existing detail URL `http://127.0.0.1:18000/candidate-detail.html?id=2`
now shows the local frontend with the same existing candidate data.
Candidate IDs refer to the same existing test backend, including previously
uploaded resumes. Do not start the synthetic preview server on this port again.

## Start

Keep the data-only SSH tunnel at `127.0.0.1:18001` running:

```powershell
ssh -i "$HOME\.ssh\aura_server" -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes -N -L 127.0.0.1:18001:127.0.0.1:8000 admin@182.92.89.154
```

Enter any SSH key passphrase only in the local terminal, never in chat or Git.
Keep this terminal open. In a second terminal at the project root, run:

```powershell
.\venv\Scripts\python.exe dev_server.py
```

Port `18000` belongs to this local frontend, not to an SSH tunnel. Do not
restart the old SSH command forwarding `18000` directly to the server: it
would occupy the frontend port and show the old server-side HTML.
Port `18001` is data-only and is not the browser entry.
The earlier `8128` entry is no longer the canonical development URL.

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
never the fixed `18000` development entry with existing candidate data.

`candidate-contact-check.cjs` uses synthetic API responses only. It verifies
direct contact display, missing values, role restrictions, refresh and request
failure states, and long email wrapping on desktop/mobile. Both browser checks
use the existing Playwright installation (set `NODE_PATH` to its `node_modules`
directory when it is not installed at the project root).

The contact UI requests `reveal_sensitive=true` for compatibility with the
current test backend; that backend still enforces its existing role scope.
The updated backend defaults to clear contacts for SuperAdmin/Admin/Recruiter
and removes the separate national-ID model/schema field and auto-migration.
These Python changes require a later backend deployment. Existing legacy
database columns and original resume files/text are not deleted or rewritten.
