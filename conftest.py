import os

import pytest


os.environ["DATABASE_URL"] = os.environ.get(
    "AURA_TEST_DATABASE_URL",
    "sqlite:///./.pytest_aura.db",
)


@pytest.fixture(autouse=True)
def reset_database(request):
    if "no_db" in request.keywords:
        yield
        return

    from database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


@pytest.fixture
def db_session():
    from database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
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

    return ASGITestClient()


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


@pytest.fixture
def admin_headers(client, db_session):
    make_user(db_session, "admin@test.local", role="SuperAdmin", name="Admin")
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "123456"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_auth_headers(client, db_session):
    def _make(email, role="Recruiter", name="Test User"):
        make_user(db_session, email, role=role, name=name)
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "123456"},
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _make
