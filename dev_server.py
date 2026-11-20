"""Serve local frontend files with the existing test backend over an SSH tunnel."""
import argparse
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx2
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask


ROOT = Path(__file__).resolve().parent
PAGES = frozenset({
    "index.html", "interviewer-workbench.html", "candidates.html",
    "talent-pool.html", "candidate-detail.html", "interviews.html",
    "interview-detail.html", "jobs.html", "add-candidate.html",
    "add-job.html", "login.html", "register.html", "settings.html",
    "portal.html",
})
HOP_HEADERS = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
})


def validate_upstream(value, local_port=8128):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username or parsed.password
        or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
        or not parsed.port or parsed.port == local_port
    ):
        raise ValueError("Upstream must be a loopback HTTP origin on a different port.")
    return value.rstrip("/")


def forwarded_headers(headers, request=False):
    blocked = set(HOP_HEADERS)
    blocked.update(part.strip().lower() for part in headers.get("connection", "").split(","))
    if request:
        blocked.update({"host", "content-length"})
    return [(key.lower(), value) for key, value in headers.raw if key.decode().lower() not in blocked]


def create_app(upstream="http://127.0.0.1:18000", *, transport=None, local_port=8128):
    upstream = validate_upstream(upstream, local_port=local_port)

    @asynccontextmanager
    async def lifespan(app):
        async with httpx2.AsyncClient(
            transport=transport, trust_env=False, follow_redirects=False,
            timeout=httpx2.Timeout(120, connect=5),
        ) as client:
            app.state.backend = client
            yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def development_headers(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Aura-Frontend"] = "local"
        response.headers["X-Aura-Data-Source"] = "existing-test-backend"
        return response

    async def proxy(request: Request):
        query = request.scope.get("query_string", b"")
        target = upstream + request.url.path
        if query:
            target += "?" + query.decode("ascii")
        client = request.app.state.backend
        outgoing = client.build_request(
            request.method, target, headers=forwarded_headers(request.headers, request=True),
            content=request.stream(),
        )
        try:
            response = await client.send(outgoing, stream=True)
        except httpx2.RequestError:
            return JSONResponse(
                status_code=503,
                content={"detail": "测试数据服务无法连接。请确认 18000 SSH 隧道仍在运行；数据未被清空。"},
            )
        result = StreamingResponse(
            response.aiter_raw(), status_code=response.status_code,
            background=BackgroundTask(response.aclose),
        )
        result.raw_headers = forwarded_headers(response.headers)
        location = response.headers.get("location", "")
        if location == upstream or location.startswith(upstream + "/"):
            result.headers["location"] = str(request.base_url).rstrip("/") + location[len(upstream):]
        return result

    app.add_api_route("/api/{path:path}", proxy, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
    app.add_api_route("/healthz", proxy, methods=["GET"])
    app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(ROOT / "index.html")

    @app.get("/{page}")
    async def page_file(page: str):
        if page not in PAGES:
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        return FileResponse(ROOT / page)

    return app


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8128)
    parser.add_argument("--upstream", default="http://127.0.0.1:18000")
    args = parser.parse_args()
    target = validate_upstream(args.upstream, local_port=args.port)
    print(f"Local frontend: http://127.0.0.1:{args.port}/candidates.html", flush=True)
    print(f"DATA: existing test backend at {target}; edits write to that backend.", flush=True)
    print("No local database is created, reset, seeded, or migrated.", flush=True)
    uvicorn.run(create_app(target, local_port=args.port), host="127.0.0.1", port=args.port)
