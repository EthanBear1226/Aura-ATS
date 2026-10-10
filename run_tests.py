import importlib
import inspect
import os
import sys
import traceback
from pathlib import Path


TEST_DATABASE_URL = os.environ.get(
    "AURA_TEST_DATABASE_URL",
    "sqlite:///./.pytest_aura.db",
)
if not TEST_DATABASE_URL.startswith("sqlite:///"):
    raise RuntimeError("Automated tests may only run against an isolated SQLite test database.")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


TEST_MODULES = [
    "test_auth_security",
    "test_candidate_lifecycle_api",
    "test_offer_approvals_api",
    "test_frontend_practicality_static",
    "test_interview_detail",
    "test_interview_detail_static",
    "test_role_permissions",
    "test_security_boundaries",
    "test_settings_api",
]


class ASGITestClient:
    def request(self, method, url, **kwargs):
        async def _send():
            import httpx2
            from main import app

            transport = httpx2.ASGITransport(app=app)
            async with httpx2.AsyncClient(
                transport=transport,
                base_url="http://testserver",
                follow_redirects=True,
            ) as async_client:
                return await async_client.request(method, url, **kwargs)

        import anyio

        return anyio.run(_send)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def patch(self, url, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)


def reset_database():
    from database import Base, SQLALCHEMY_DATABASE_URL, engine

    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        raise RuntimeError("Refusing to reset a non-SQLite database during tests.")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_db_session():
    from database import SessionLocal

    return SessionLocal()


def make_user(db, email, role="SuperAdmin", name="Test User", password="123456"):
    import models
    from main import hash_password

    user = models.User(
        company="Aura Test",
        email=email,
        hashed_password=hash_password(password),
        name=name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_admin_headers(client, db):
    make_user(db, "admin@test.local", role="SuperAdmin", name="Admin")
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "123456"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def get_make_auth_headers(client, db):
    def _make(email, role="Recruiter", name="Test User"):
        make_user(db, email, role=role, name=name)
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "123456"},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _make


def build_args(fn):
    client = ASGITestClient()
    db = get_db_session()
    args = {}
    for name in inspect.signature(fn).parameters:
        if name == "client":
            args[name] = client
        elif name == "db_session":
            args[name] = db
        elif name == "admin_headers":
            args[name] = get_admin_headers(client, db)
        elif name == "make_auth_headers":
            args[name] = get_make_auth_headers(client, db)
        else:
            raise RuntimeError(f"Unsupported test fixture: {name}")
    return args, db


def run():
    failures = []
    total = 0
    root = Path(__file__).parent
    sys.path.insert(0, str(root))

    for module_name in TEST_MODULES:
        module = importlib.import_module(module_name)
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            total += 1
            db = None
            try:
                if module_name not in {
                    "test_frontend_practicality_static",
                    "test_interview_detail_static",
                }:
                    reset_database()
                args, db = build_args(fn)
                fn(**args)
                print(f"PASS {module_name}.{name}")
            except Exception:
                failures.append(f"{module_name}.{name}\n{traceback.format_exc()}")
                print(f"FAIL {module_name}.{name}")
            finally:
                if db is not None:
                    db.close()

    if failures:
        print("\n".join(failures))
        print(f"\n{len(failures)}/{total} tests failed.")
        return 1
    print(f"\n{total} tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
