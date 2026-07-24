"""Tests for the Google Places search service mapping and the cooking recipe payload."""
import app.services.places as places_service
from app.models import Dish, Recipe
from app.services.places import BUDGET_PRICE_LEVELS, search_restaurants

PLACES_RESULT = {
    "places": [
        {
            "displayName": {"text": "Maharaja Curry House"},
            "formattedAddress": "812 Regent St, Madison, WI 53715",
            "rating": 4.4,
            "userRatingCount": 208,
            "priceLevel": "PRICE_LEVEL_MODERATE",
            "currentOpeningHours": {"openNow": True},
            "nationalPhoneNumber": "(608) 555-0182",
            "googleMapsUri": "https://maps.google.com/?cid=1",
            "websiteUri": "https://maharaja.example",
            "photos": [{"name": "places/abc123/photos/xyz789"}],
        },
        {
            "displayName": {"text": "No Frills Curry"},
            "formattedAddress": "1 Main St",
        },
    ]
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise places_service.requests.HTTPError(f"{self.status_code}")


def test_maps_places_fields_to_cards(app, monkeypatch):
    app.config["GOOGLE_PLACES_API_KEY"] = "test-key"
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(body=json, headers=headers)
        return FakeResponse(PLACES_RESULT)

    monkeypatch.setattr(places_service.requests, "post", fake_post)

    with app.test_request_context():
        cards = search_restaurants("Chicken Tikka Masala", "Madison, WI", "<$50")

    assert captured["body"]["textQuery"] == "Chicken Tikka Masala restaurant in Madison, WI"
    assert captured["body"]["priceLevels"] == BUDGET_PRICE_LEVELS["<$50"]
    assert captured["headers"]["X-Goog-Api-Key"] == "test-key"

    first = cards[0]
    assert first["name"] == "Maharaja Curry House"
    assert first["price"] == "$$"
    assert first["open_now"] is True
    assert first["review_count"] == 208
    assert first["order_url"] == "https://maharaja.example"
    assert first["photo_url"] == "/api/takeout/photo?name=places/abc123/photos/xyz789"

    # sparse places degrade to empty fields, not KeyErrors
    second = cards[1]
    assert second["name"] == "No Frills Curry"
    assert second["price"] == "" and second["photo_url"] == ""
    assert second["open_now"] is None


def test_unknown_budget_sends_no_price_filter(app, monkeypatch):
    app.config["GOOGLE_PLACES_API_KEY"] = "test-key"
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(body=json)
        return FakeResponse({"places": []})

    monkeypatch.setattr(places_service.requests, "post", fake_post)

    with app.test_request_context():
        assert search_restaurants("Pad Thai", "Madison, WI", None) == []
    assert "priceLevels" not in captured["body"]


def test_photo_proxy_rejects_bad_names(client):
    resp = client.get("/api/takeout/photo?name=../../etc/passwd")
    assert resp.status_code == 400
    resp = client.get("/api/takeout/photo?name=places/abc/photos/def/extra")
    assert resp.status_code == 400


def test_cooking_includes_cached_recipe(client, auth_headers, fake_engine, db):
    profile = {
        "cuisines": ["Indian"],
        "available_ingredients": ["chicken", "tomato"],
        "skill_level": "beginner",
        "weight_goal": "maintain",
        "budget": "<$50",
        "location": "Madison, WI",
    }
    assert client.put("/api/profile", json=profile, headers=auth_headers).status_code == 201
    client.get("/api/recommend", headers=auth_headers)

    dish = Dish.query.filter_by(dish_name="Chicken Tikka Masala").one()
    db.session.add(
        Recipe(
            dish_id=dish.id,
            title="Best Chicken Tikka Masala",
            servings=4,
            ready_minutes=45,
            source_name="A Food Blog",
            source_url="https://afoodblog.example/tikka",
            ingredients=[
                {"name": "chicken thighs", "amount": "1.5 lb chicken thighs"},
                {"name": "greek yogurt", "amount": "1 cup Greek yogurt"},
            ],
            steps=["Marinate the chicken.", "Sear and simmer in sauce."],
        )
    )
    db.session.commit()

    resp = client.post("/api/cooking", headers=auth_headers)
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["recipe"]["steps"] == ["Marinate the chicken.", "Sear and simmer in sauce."]
    assert body["recipe"]["servings"] == 4
    # checklist now carries quantities, and pantry "chicken" matches "chicken thighs"
    by_name = {i["name"]: i for i in body["ingredients"]}
    assert by_name["chicken thighs"]["available"] is True
    assert by_name["chicken thighs"]["amount"] == "1.5 lb chicken thighs"
    assert by_name["greek yogurt"]["available"] is False
