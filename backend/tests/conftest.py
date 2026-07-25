import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.models import Dish
from app.services import recommender as recommender_service


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    # Never let real keys from .env leak into tests — external calls must be
    # mocked, and tests opt in by setting these explicitly.
    app.config["SPOONACULAR_API_KEY"] = ""
    app.config["GOOGLE_PLACES_API_KEY"] = ""
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def auth_headers(client):
    """Sign up a user and return Authorization headers for them."""
    resp = client.post(
        "/auth/signup",
        json={"username": "ishita", "email": "ishita@example.com", "password": "hunter2"},
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


class FakeEngine:
    """Stands in for the PyTorch RecommendationEngine: returns the first
    seeded dish not in excluded_dishes, mirroring the real interface."""

    def __init__(self, dishes):
        self.dishes = dishes
        self.last_call = None

    def recommend(
        self, user_profile, available_ingredients=None, excluded_dishes=None, user_id=None, **kwargs
    ):
        self.last_call = {
            "user_profile": user_profile,
            "available_ingredients": available_ingredients,
            "excluded_dishes": list(excluded_dishes or []),
            "preferred_dishes": list(kwargs.get("preferred_dishes") or []),
            "user_id": user_id,
        }
        excluded = set(excluded_dishes or [])
        for dish in self.dishes:
            if dish["dish_name"] not in excluded:
                return {
                    "dish_name": dish["dish_name"],
                    "cuisine": dish["cuisine"],
                    "ingredients": dish["ingredients"].split("|"),
                    "score": 4.2,
                }
        raise RuntimeError("No dishes left to recommend")

    def get_ingredients(self, dish_name):
        for dish in self.dishes:
            if dish["dish_name"].lower() == dish_name.lower():
                return dish["ingredients"].split("|")
        return []


FAKE_DISHES = [
    {"dish_name": "Chicken Tikka Masala", "cuisine": "Indian", "ingredients": "chicken|yogurt|tomato|garam masala"},
    {"dish_name": "Pad Thai", "cuisine": "Thai", "ingredients": "rice noodles|egg|peanuts|tamarind"},
    {"dish_name": "Margherita Pizza", "cuisine": "Italian", "ingredients": "flour|tomato|mozzarella|basil"},
]


@pytest.fixture()
def fake_engine(db, monkeypatch):
    """Seed the dish catalog and swap the ML engine for a deterministic fake."""
    for i, dish in enumerate(FAKE_DISHES, start=1):
        db.session.add(Dish(id=i, **dish))
    db.session.commit()

    engine = FakeEngine(FAKE_DISHES)
    monkeypatch.setattr(recommender_service, "_engine", engine)
    return engine
