import json

import anyio
import httpx2
import pytest

from dev_server import create_app, validate_upstream


pytestmark = pytest.mark.no_db


def backend_response(status=200, *, content=b"", json_data=None, headers=None):
    headers = dict(headers or {})
    if json_data is not None:
        content = json.dumps(json_data).encode()
        headers["Content-Type"] = "application/json"
    return httpx2.Response(status, stream=httpx2.ByteStream(content), headers=headers)


def run_check(check, handler):
    async def run():
        app = create_app(transport=httpx2.MockTransport(handler))
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app), base_url="http://local",
            ) as client:
                await check(client)
    anyio.run(run)


def test_dev_server_serves_local_code_and_blocks_private_files():
    def backend(request):
        raise AssertionError("Local pages must not be requested from the backend")

    async def check(client):
        response = await client.get("/candidate-detail.html?id=2")
        assert response.status_code == 200
        assert "#tab-pane-0.active {" in response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-aura-frontend"] == "local"
        icon = await client.get("/assets/vendor/lucide-0.468.0/lucide.min.js")
        assert icon.status_code == 200
        for path in ("/.env", "/aura_db.db", "/main.py", "/uploads/private.pdf", "/.git/config"):
            assert (await client.get(path)).status_code == 404
    run_check(check, backend)


def test_dev_server_forwards_auth_query_pdf_and_write_body_without_retry():
    requests = []

    async def backend(request):
        body = await request.aread()
        requests.append((request.method, str(request.url), body))
        assert request.headers["authorization"] == "Bearer test"
        assert "x-local-hop" not in request.headers
        if request.url.path.endswith("/resume"):
            return backend_response(200, content=b"%PDF-synthetic",
                                   headers={"Content-Type": "application/pdf", "Content-Disposition": 'inline; filename="resume.pdf"'})
        return backend_response(409, json_data={"detail": "Existing record"})

    async def check(client):
        headers = {"Authorization": "Bearer test", "Connection": "x-local-hop", "X-Local-Hop": "remove"}
        response = await client.patch("/api/candidates/2?source=a%20b", headers=headers, content=b'{"stage":"test"}')
        assert response.status_code == 409
        assert response.json()["detail"] == "Existing record"
        pdf = await client.get("/api/candidates/2/resume", headers=headers)
        assert pdf.content == b"%PDF-synthetic"
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.headers["content-disposition"] == 'inline; filename="resume.pdf"'
        assert len(requests) == 2
        assert requests[0] == ("PATCH", "http://127.0.0.1:18000/api/candidates/2?source=a%20b", b'{"stage":"test"}')
    run_check(check, backend)


def test_dev_server_preserves_unauthorized_and_reports_tunnel_failure():
    def backend(request):
        if request.url.path == "/healthz":
            raise httpx2.ConnectError("Tunnel unavailable", request=request)
        return backend_response(401, json_data={"detail": "Not authenticated"})

    async def check(client):
        response = await client.get("/api/candidates")
        assert response.status_code == 401
        unavailable = await client.get("/healthz")
        assert unavailable.status_code == 503
        assert "数据未被清空" in unavailable.json()["detail"]
    run_check(check, backend)


def test_dev_server_upstream_cannot_be_remote_or_point_to_itself():
    for url in ("https://example.com", "http://example.com:80", "http://127.0.0.1:8128",
                "http://user:pass@localhost:18000", "http://localhost:18000/api", "http://localhost:18000?x=1"):
        try:
            validate_upstream(url)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Unsafe upstream accepted: {url}")
    assert validate_upstream("http://127.0.0.1:18000/") == "http://127.0.0.1:18000"
    assert create_app("http://127.0.0.1:8128", local_port=8129)


def test_dev_server_redirects_stay_on_the_local_origin_without_retry():
    requests = []

    def backend(request):
        requests.append(request.url)
        return backend_response(307, headers={"Location": "http://127.0.0.1:18000/api/jobs/"})

    async def check(client):
        response = await client.post("/api/jobs")
        assert response.status_code == 307
        assert response.headers["location"] == "http://local/api/jobs/"
        assert len(requests) == 1
    run_check(check, backend)
