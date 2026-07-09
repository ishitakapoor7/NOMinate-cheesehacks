"""End-to-end flow over the DB-backed endpoints: profile -> recommend ->
cooking / takeout / feedback, with the ML engine faked out."""
import app.api.takeout as takeout_module
from app.models import Rating, Recommendation

PROFILE = {
    "cuisines": ["Indian"],
    "dietary_restrictions": [],
    "allergies": [],
    "available_ingredients": ["chicken", "tomato"],
    "skill_level": "beginner",
    "weight_goal": "maintain",
    "budget": "<$50",
    "location": "Madison, WI",
}


def _setup(client, auth_headers):
    assert client.put("/api/profile", json=PROFILE, headers=auth_headers).status_code == 201


def test_recommend_requires_profile(client, auth_headers, fake_engine):
    resp = client.get("/api/recommend", headers=auth_headers)
    assert resp.status_code == 404


def test_recommend_returns_and_logs_dish(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    resp = client.get("/api/recommend", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["recommendation"] == "Chicken Tikka Masala"
    assert body["cuisine"] == "Indian"

    rec = Recommendation.query.one()
    assert rec.dish.dish_name == "Chicken Tikka Masala"
    assert rec.action is None
    # the engine received the profile, the user's pantry, and their identity
    # (so retrained embeddings can be used for returning users)
    assert fake_engine.last_call["available_ingredients"] == ["chicken", "tomato"]
    assert fake_engine.last_call["user_id"] is not None


def test_consecutive_recommends_vary(client, auth_headers, fake_engine):
    _setup(client, auth_headers)
    first = client.get("/api/recommend", headers=auth_headers).get_json()
    second = client.get("/api/recommend", headers=auth_headers).get_json()
    # the first dish was just shown, so it's excluded from the second request
    assert first["recommendation"] != second["recommendation"]


def test_cooking_marks_action_and_rates(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)

    resp = client.post("/api/cooking", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["dish"] == "Chicken Tikka Masala"
    by_name = {i["name"]: i["available"] for i in body["ingredients"]}
    assert by_name["chicken"] is True
    assert by_name["yogurt"] is False

    assert Recommendation.query.one().action == "cooked"
    rating = Rating.query.one()
    assert rating.source == "cooked" and rating.value == 5.0


def test_cooking_without_recommendation_is_404(client, auth_headers, fake_engine):
    _setup(client, auth_headers)
    assert client.post("/api/cooking", headers=auth_headers).status_code == 404


def test_takeout_returns_restaurants(client, auth_headers, fake_engine, db, monkeypatch):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)

    seen = {}

    def fake_scrape(dish, location, budget):
        seen.update(dish=dish, location=location, budget=budget)
        return [{"name": "Curry House", "rating": "4.5", "price": "$$", "address": "123 State St"}]

    monkeypatch.setattr(takeout_module, "scrape_yelp_restaurants", fake_scrape)

    resp = client.post("/api/takeout", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["restaurants"][0]["name"] == "Curry House"
    assert seen == {
        "dish": "Chicken Tikka Masala",
        "location": "Madison, WI",
        "budget": "<$50",
    }
    assert Recommendation.query.one().action == "takeout"
    assert Rating.query.one().source == "takeout"


def test_takeout_requires_location(client, auth_headers, fake_engine):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)
    client.put("/api/profile", json={"location": ""}, headers=auth_headers)

    resp = client.post("/api/takeout", headers=auth_headers)
    assert resp.status_code == 400


def test_dislike_feedback_excludes_dish_permanently(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    first = client.get("/api/recommend", headers=auth_headers).get_json()

    resp = client.post(
        "/api/feedback",
        json={"feedback_reason": "I just don't like it"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    rating = Rating.query.one()
    assert rating.source == "disliked" and rating.value == 1.0
    assert Recommendation.query.first().action == "rejected"

    # the disliked dish never comes back
    second = client.get("/api/recommend", headers=auth_headers).get_json()
    assert second["recommendation"] != first["recommendation"]
    assert first["recommendation"] in fake_engine.last_call["excluded_dishes"]


def test_recently_eaten_feedback_is_neutral_signal(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)

    client.post(
        "/api/feedback", json={"feedback_reason": "Recently Eaten"}, headers=auth_headers
    )
    rating = Rating.query.one()
    assert rating.source == "explicit_feedback" and rating.value == 3.0


def test_feedback_without_recommendation_is_404(client, auth_headers, fake_engine):
    _setup(client, auth_headers)
    resp = client.post(
        "/api/feedback", json={"feedback_reason": "Recently Eaten"}, headers=auth_headers
    )
    assert resp.status_code == 404
