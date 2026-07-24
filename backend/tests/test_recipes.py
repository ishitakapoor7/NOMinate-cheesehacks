"""Tests for the Spoonacular recipe service and its cache behavior."""
import requests

import app.services.recipes as recipes_service
from app.models import Dish, Recipe
from app.services.recipes import get_recipe_for_dish

SPOONACULAR_RESULT = {
    "results": [
        {
            "title": "Best Chicken Tikka Masala",
            "image": "https://img.spoonacular.com/recipes/1-556x370.jpg",
            "servings": 4,
            "readyInMinutes": 45,
            "preparationMinutes": 25,
            "cookingMinutes": 20,
            "sourceName": "A Food Blog",
            "sourceUrl": "https://afoodblog.example/tikka",
            "extendedIngredients": [
                {"nameClean": "chicken thighs", "original": "1.5 lb chicken thighs"},
                {"name": "greek yogurt", "original": "1 cup Greek yogurt"},
            ],
            "analyzedInstructions": [
                {
                    "steps": [
                        {"number": 1, "step": "Marinate the chicken."},
                        {"number": 2, "step": "Sear and simmer in sauce."},
                    ]
                }
            ],
        }
    ]
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


def _dish(db, name="Chicken Tikka Masala"):
    dish = Dish(id=7001, dish_name=name, cuisine="Indian", ingredients="chicken|yogurt")
    db.session.add(dish)
    db.session.commit()
    return dish


def test_fetches_parses_and_caches(app, db, monkeypatch):
    dish = _dish(db)
    app.config["SPOONACULAR_API_KEY"] = "test-key"
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params["query"])
        return FakeResponse(SPOONACULAR_RESULT)

    monkeypatch.setattr(recipes_service.requests, "get", fake_get)

    with app.test_request_context():
        recipe = get_recipe_for_dish(dish)

    assert recipe.title == "Best Chicken Tikka Masala"
    assert recipe.servings == 4
    assert recipe.prep_minutes == 25
    assert recipe.steps == ["Marinate the chicken.", "Sear and simmer in sauce."]
    assert recipe.ingredients[0] == {
        "name": "chicken thighs",
        "amount": "1.5 lb chicken thighs",
    }
    assert calls == ["Chicken Tikka Masala"]

    # second ask is served from the DB — no HTTP
    with app.test_request_context():
        again = get_recipe_for_dish(dish)
    assert again.id == recipe.id
    assert calls == ["Chicken Tikka Masala"]


def test_zero_results_caches_a_miss(app, db, monkeypatch):
    dish = _dish(db, name="Extremely Obscure Dish")
    app.config["SPOONACULAR_API_KEY"] = "test-key"
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(1)
        return FakeResponse({"results": []})

    monkeypatch.setattr(recipes_service.requests, "get", fake_get)

    with app.test_request_context():
        assert get_recipe_for_dish(dish) is None
        assert get_recipe_for_dish(dish) is None  # miss is cached, no second call

    assert len(calls) == 1
    assert Recipe.query.filter_by(dish_id=dish.id).one().found is False


def test_no_api_key_returns_none_without_caching(app, db):
    dish = _dish(db)
    app.config["SPOONACULAR_API_KEY"] = ""

    with app.test_request_context():
        assert get_recipe_for_dish(dish) is None
    # nothing cached — once a key exists the dish can still be fetched
    assert Recipe.query.count() == 0


def test_http_error_returns_none_without_caching(app, db, monkeypatch):
    dish = _dish(db)
    app.config["SPOONACULAR_API_KEY"] = "test-key"

    def fake_get(url, params=None, timeout=None):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(recipes_service.requests, "get", fake_get)

    with app.test_request_context():
        assert get_recipe_for_dish(dish) is None
    assert Recipe.query.count() == 0


def test_quota_exhausted_returns_none_without_caching(app, db, monkeypatch):
    dish = _dish(db)
    app.config["SPOONACULAR_API_KEY"] = "test-key"

    monkeypatch.setattr(
        recipes_service.requests,
        "get",
        lambda url, params=None, timeout=None: FakeResponse({}, status_code=402),
    )

    with app.test_request_context():
        assert get_recipe_for_dish(dish) is None
    assert Recipe.query.count() == 0  # retryable another day
