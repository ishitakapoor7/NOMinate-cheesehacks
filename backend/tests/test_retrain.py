"""Tests for the retraining data assembly (no actual torch training)."""
from app.models import Dish, Profile, Rating, User
from app.services.retrain import build_training_frames, real_user_key


def _seed_real_activity(db):
    user = User(email="ishita@example.com", username="ishita", password_hash="x")
    db.session.add(user)
    db.session.flush()
    db.session.add(
        Profile(
            user_id=user.id,
            cuisines=["Indian", "Thai"],
            dietary_restrictions=["vegetarian"],
            allergies=["peanuts"],
            available_ingredients=[],
            skill_level="intermediate",
            weight_goal="maintain",
            budget="<$50",
            location="Madison, WI",
        )
    )
    db.session.add(Dish(id=9001, dish_name="Test Curry", cuisine="Indian", ingredients="rice|lentils"))
    db.session.add(Rating(user_id=user.id, dish_id=9001, value=5.0, source="cooked"))
    db.session.commit()
    return user


def test_frames_without_real_ratings_are_synthetic_only(app, db):
    db.session.add(Dish(id=9001, dish_name="Test Curry", cuisine="Indian", ingredients="rice"))
    db.session.commit()

    ratings, dishes, users = build_training_frames()
    assert not ratings["user_id"].astype(str).str.startswith("real_").any()
    assert not users["user_id"].astype(str).str.startswith("real_").any()
    assert len(dishes) == 1  # dishes come from the DB, not the CSV


def test_real_ratings_blend_in_weighted(app, db):
    user = _seed_real_activity(db)
    ratings, dishes, users = build_training_frames(real_rating_weight=10)

    real_rows = ratings[ratings["user_id"] == real_user_key(user.id)]
    assert len(real_rows) == 10  # one real rating, duplicated by the weight
    assert (real_rows["rating"] == 5.0).all()
    assert (real_rows["dish_id"] == 9001).all()


def test_real_user_profile_features_are_included(app, db):
    user = _seed_real_activity(db)
    _, _, users = build_training_frames()

    row = users[users["user_id"] == real_user_key(user.id)].iloc[0]
    assert row["preferred_cuisines"] == "Indian|Thai"
    assert row["skill"] == "intermediate"
    assert row["health_goal"] == "maintain"
    assert row["dietary_restrictions"] == "vegetarian"


def test_synthetic_ids_cannot_collide_with_real_ids(app, db):
    _seed_real_activity(db)
    ratings, _, users = build_training_frames()

    synthetic = set(ratings["user_id"].astype(str)) - {
        u for u in ratings["user_id"].astype(str) if u.startswith("real_")
    }
    assert all(not u.startswith("real_") for u in synthetic)
    assert users["user_id"].is_unique
