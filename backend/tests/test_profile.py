from app.models import Profile

PROFILE = {
    "cuisines": ["Indian", "Thai"],
    "dietary_restrictions": ["vegetarian"],
    "allergies": ["peanuts"],
    "available_ingredients": ["rice", "tomato"],
    "skill_level": "intermediate",
    "weight_goal": "maintain",
    "budget": "<$50",
    "location": "Madison, WI",
}


def test_profile_requires_auth(client):
    assert client.get("/api/profile").status_code == 401
    assert client.put("/api/profile", json=PROFILE).status_code == 401


def test_get_profile_before_setup_is_404(client, auth_headers):
    resp = client.get("/api/profile", headers=auth_headers)
    assert resp.status_code == 404


def test_put_creates_profile(client, auth_headers, db):
    resp = client.put("/api/profile", json=PROFILE, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.get_json()["profile"]
    assert body["cuisines"] == ["Indian", "Thai"]
    assert body["location"] == "Madison, WI"
    assert Profile.query.count() == 1


def test_put_updates_existing_profile(client, auth_headers, db):
    client.put("/api/profile", json=PROFILE, headers=auth_headers)
    resp = client.put(
        "/api/profile", json={"budget": "$50-$100"}, headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.get_json()["profile"]
    assert body["budget"] == "$50-$100"
    # untouched fields survive a partial update
    assert body["cuisines"] == ["Indian", "Thai"]
    assert Profile.query.count() == 1


def test_get_returns_saved_profile(client, auth_headers):
    client.put("/api/profile", json=PROFILE, headers=auth_headers)
    resp = client.get("/api/profile", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["profile"]["allergies"] == ["peanuts"]


def test_comma_separated_strings_become_lists(client, auth_headers):
    resp = client.put(
        "/api/profile",
        json={**PROFILE, "allergies": "peanuts, shellfish"},
        headers=auth_headers,
    )
    assert resp.get_json()["profile"]["allergies"] == ["peanuts", "shellfish"]


def test_profile_persists_after_signup_flag(client, auth_headers):
    client.put("/api/profile", json=PROFILE, headers=auth_headers)
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.get_json()["user"]["has_profile"] is True
