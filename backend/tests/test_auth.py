import app.auth.routes as auth_routes
from app.auth.google import GoogleAuthError
from app.models import User

SIGNUP = {"username": "ishita", "email": "ishita@example.com", "password": "hunter2"}


def test_signup_creates_user_and_returns_tokens(client, db):
    resp = client.post("/auth/signup", json=SIGNUP)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["user"]["email"] == "ishita@example.com"
    assert body["user"]["has_profile"] is False
    assert body["access_token"] and body["refresh_token"]
    assert User.query.count() == 1


def test_signup_missing_fields(client):
    resp = client.post("/auth/signup", json={"email": "x@y.com"})
    assert resp.status_code == 400


def test_signup_duplicate_email(client):
    client.post("/auth/signup", json=SIGNUP)
    resp = client.post("/auth/signup", json={**SIGNUP, "username": "other"})
    assert resp.status_code == 409


def test_login_ok(client):
    client.post("/auth/signup", json=SIGNUP)
    resp = client.post(
        "/auth/login", json={"email": "Ishita@Example.com", "password": "hunter2"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["user"]["username"] == "ishita"


def test_login_wrong_password(client):
    client.post("/auth/signup", json=SIGNUP)
    resp = client.post(
        "/auth/login", json={"email": "ishita@example.com", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_returns_current_user(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "ishita@example.com"


def test_refresh_issues_new_access_token(client):
    refresh_token = client.post("/auth/signup", json=SIGNUP).get_json()["refresh_token"]
    resp = client.post(
        "/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["access_token"]


def test_access_token_rejected_for_refresh(client):
    access_token = client.post("/auth/signup", json=SIGNUP).get_json()["access_token"]
    resp = client.post(
        "/auth/refresh", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert resp.status_code == 422


def _configure_google(app, monkeypatch, claims):
    app.config["GOOGLE_CLIENT_ID"] = "test-client-id"

    def fake_verify(credential, client_id):
        if isinstance(claims, Exception):
            raise claims
        return claims

    monkeypatch.setattr(auth_routes, "verify_google_id_token", fake_verify)


def test_google_creates_new_user(client, app, db, monkeypatch):
    _configure_google(
        app, monkeypatch, {"sub": "g-123", "email": "new@gmail.com", "name": "New Person"}
    )
    resp = client.post("/auth/google", json={"credential": "fake"})
    assert resp.status_code == 200
    user = User.query.filter_by(google_sub="g-123").first()
    assert user.email == "new@gmail.com"
    assert user.password_hash is None


def test_google_links_existing_email_account(client, app, db, monkeypatch):
    client.post("/auth/signup", json=SIGNUP)
    _configure_google(
        app, monkeypatch, {"sub": "g-456", "email": "ishita@example.com", "name": "Ishita"}
    )
    resp = client.post("/auth/google", json={"credential": "fake"})
    assert resp.status_code == 200
    assert User.query.count() == 1
    assert User.query.first().google_sub == "g-456"


def test_google_invalid_credential(client, app, monkeypatch):
    _configure_google(app, monkeypatch, GoogleAuthError("bad token"))
    resp = client.post("/auth/google", json={"credential": "fake"})
    assert resp.status_code == 401


def test_google_unconfigured_returns_503(client, app):
    app.config["GOOGLE_CLIENT_ID"] = ""
    resp = client.post("/auth/google", json={"credential": "fake"})
    assert resp.status_code == 503
