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


def test_recommend_prefers_dishes_with_a_recipe(client, auth_headers, fake_engine, db):
    from app.models import Dish, Recipe

    _setup(client, auth_headers)
    pad_thai = Dish.query.filter_by(dish_name="Pad Thai").one()
    db.session.add(Recipe(dish_id=pad_thai.id, title="Pad Thai", steps=["Boil noodles."]))
    # a lookup miss (no steps) must NOT count as having a recipe
    pizza = Dish.query.filter_by(dish_name="Margherita Pizza").one()
    db.session.add(Recipe(dish_id=pizza.id, title="", steps=[]))
    db.session.commit()

    client.get("/api/recommend", headers=auth_headers)
    preferred = fake_engine.last_call["preferred_dishes"]
    assert "Pad Thai" in preferred
    assert "Margherita Pizza" not in preferred


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


def test_takeout_returns_restaurants(app, client, auth_headers, fake_engine, db, monkeypatch):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)

    seen = {}

    def fake_search(dish, location, budget, cuisine=None):
        seen.update(dish=dish, location=location, budget=budget, cuisine=cuisine)
        return [{"name": "Curry House", "rating": 4.5, "price": "$$", "address": "123 State St"}]

    app.config["GOOGLE_PLACES_API_KEY"] = "test-key"
    monkeypatch.setattr(takeout_module, "search_restaurants", fake_search)

    resp = client.post("/api/takeout", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["restaurants"][0]["name"] == "Curry House"
    # the dish's cuisine is what steers the search, not the quirky dish name
    assert seen == {
        "dish": "Chicken Tikka Masala",
        "location": "Madison, WI",
        "budget": "<$50",
        "cuisine": "Indian",
    }
    assert Recommendation.query.one().action == "takeout"
    assert Rating.query.one().source == "takeout"


def test_takeout_without_places_key_is_503(app, client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)

    app.config["GOOGLE_PLACES_API_KEY"] = ""
    resp = client.post("/api/takeout", headers=auth_headers)
    assert resp.status_code == 503
    # an unconfigured search must not record a takeout signal
    assert Rating.query.count() == 0
    assert Recommendation.query.one().action is None


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


def test_show_me_something_else_is_neutral_not_a_dislike(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)

    # Asking for variety must not train the model against the skipped dish.
    client.post(
        "/api/feedback",
        json={"feedback_reason": "Show me something else"},
        headers=auth_headers,
    )
    rating = Rating.query.one()
    assert rating.source == "explicit_feedback" and rating.value == 3.0


def test_feedback_without_recommendation_is_404(client, auth_headers, fake_engine):
    _setup(client, auth_headers)
    resp = client.post(
        "/api/feedback", json={"feedback_reason": "Recently Eaten"}, headers=auth_headers
    )
    assert resp.status_code == 404


def test_latest_returns_current_dish_without_generating(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    assert client.get("/api/recommend/latest", headers=auth_headers).status_code == 404

    client.get("/api/recommend", headers=auth_headers)
    resp = client.get("/api/recommend/latest", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.get_json()["recommendation"] == "Chicken Tikka Masala"
    # reading the latest dish must not log a new recommendation
    assert Recommendation.query.count() == 1


def test_comment_card_loved_it_is_strong_positive(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)

    client.post("/api/feedback", json={"feedback_reason": "Loved it"}, headers=auth_headers)
    rating = Rating.query.one()
    assert rating.source == "explicit_feedback" and rating.value == 5.0


def test_only_dinner_mains_are_nominatable():
    from ml.recommender import is_main_dish

    assert is_main_dish("Beef") is True
    assert is_main_dish("Vegetarian") is True
    assert is_main_dish(float("nan")) is True  # unknown category isn't excluded
    for junk in ("Dessert", "antipasti", "Side", "side dish", "Beverage", "Breakfast"):
        assert is_main_dish(junk) is False


def test_diet_conflict_catches_mislabeled_ingredients():
    from ml.recommender import diet_conflict

    # a "vegetarian" dish whose ingredients include fish must be rejected
    assert diet_conflict({"rice", "noodles", "fish", "sauce"}, ["vegetarian"]) is True
    assert diet_conflict({"tofu", "rice", "soy"}, ["vegetarian"]) is False
    # pescatarians can have fish but not meat
    assert diet_conflict({"salmon", "rice"}, ["pescatarian"]) is False
    assert diet_conflict({"chicken", "rice"}, ["pescatarian"]) is True
    # vegans exclude dairy and egg too
    assert diet_conflict({"flour", "butter", "sugar"}, ["vegan"]) is True
    assert diet_conflict({"lentils", "tomato"}, ["vegan"]) is False
    assert diet_conflict({"anything"}, []) is False


def test_pantry_match_is_whole_word_not_substring():
    from app.api.cooking import _is_available

    pantry = {"egg", "rice", "olive oil"}
    assert _is_available("egg", pantry) is True
    assert _is_available("chicken breast", {"chicken"}) is True
    assert _is_available("olive oil", pantry) is True
    # substrings of a longer word must not count as on-hand
    assert _is_available("eggplant", pantry) is False
    assert _is_available("brown rice noodles", {"noodle"}) is False


def test_feedback_after_cooking_keeps_cooked_action(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    client.get("/api/recommend", headers=auth_headers)
    client.post("/api/cooking", headers=auth_headers)

    client.post("/api/feedback", json={"feedback_reason": "Loved it"}, headers=auth_headers)
    assert Recommendation.query.one().action == "cooked"


def test_normalize_allergens_fixes_typos():
    from ml.recommender import matches_allergen, normalize_allergens

    # typos snap to the canonical allergen so the eager filter still fires
    assert normalize_allergens(["penut"]) == ["peanut"]
    assert normalize_allergens(["Shellfsh", "glutn"]) == ["shellfish", "gluten"]
    # already-clean and unknown-custom entries pass through, deduped/lowered
    assert normalize_allergens(["Peanut", "peanut", "durian"]) == ["peanut", "durian"]
    # the corrected value actually matches a real ingredient
    corrected = normalize_allergens(["penut"])[0]
    assert matches_allergen("peanut butter", corrected) is True


def test_profile_save_normalizes_allergy_typos(client, auth_headers, db):
    profile = {**PROFILE, "allergies": ["penut", "shellfsh"]}
    resp = client.put("/api/profile", json=profile, headers=auth_headers)
    assert resp.status_code == 201
    # what's stored (and echoed back to the chips) is the corrected spelling
    stored = client.get("/api/profile", headers=auth_headers).get_json()["profile"]
    assert stored["allergies"] == ["peanut", "shellfish"]


def test_learned_affinity_reflects_rating_history(client, auth_headers, fake_engine, db):
    from app.models import Dish, User
    from app.services.personalization import learned_affinity

    user = User.query.first()
    tikka = Dish.query.filter_by(dish_name="Chicken Tikka Masala").one()  # Indian
    pizza = Dish.query.filter_by(dish_name="Margherita Pizza").one()  # Italian
    db.session.add_all(
        [
            Rating(user_id=user.id, dish_id=tikka.id, value=5.0, source="cooked"),
            Rating(user_id=user.id, dish_id=pizza.id, value=1.0, source="disliked"),
        ]
    )
    db.session.commit()

    aff = learned_affinity(user.id)
    assert aff["cuisines"]["indian"] > 0  # cooked → liked
    assert aff["cuisines"]["italian"] < 0  # disliked
    assert aff["ingredients"]["chicken"] > 0  # ingredient-level signal too
    # a user with no ratings behaves exactly as before (pure cold start)
    assert learned_affinity(999999) == {"cuisines": {}, "ingredients": {}}


def test_recommend_passes_learned_affinity_from_history(client, auth_headers, fake_engine, db):
    _setup(client, auth_headers)
    # first recommendation: no history yet, so nothing learned
    client.get("/api/recommend", headers=auth_headers)
    assert not fake_engine.last_call["learned_affinity"]["cuisines"]

    # cooking writes an implicit 5.0 rating for the Indian dish...
    client.post("/api/cooking", headers=auth_headers)
    # ...which the next recommendation feeds back into the engine as learned taste
    client.get("/api/recommend", headers=auth_headers)
    assert fake_engine.last_call["learned_affinity"]["cuisines"]["indian"] > 0
