from app.models import Profile, Rating, Recommendation, User


def test_user_profile_roundtrip(db):
    user = User(email="a@b.com", username="alice")
    user.profile = Profile(
        cuisines=["Italian", "Thai"],
        dietary_restrictions=["vegetarian"],
        allergies=["peanuts"],
        available_ingredients=["rice", "egg"],
        skill_level="intermediate",
        weight_goal="weight_loss",
        budget="$50-$100",
        location="Madison, WI",
    )
    db.session.add(user)
    db.session.commit()

    fetched = User.query.filter_by(email="a@b.com").one()
    assert fetched.username == "alice"
    # Array columns survive the round-trip.
    assert fetched.profile.cuisines == ["Italian", "Thai"]
    assert fetched.profile.allergies == ["peanuts"]
    assert fetched.profile.skill_level == "intermediate"


def test_rating_and_recommendation_link_to_user(db):
    from app.models import Dish

    user = User(email="c@d.com", username="bob")
    dish = Dish(id=1, dish_name="Pad Thai", cuisine="Thai")
    db.session.add_all([user, dish])
    db.session.commit()

    db.session.add(Rating(user_id=user.id, dish_id=dish.id, value=4.5, source="cooked"))
    db.session.add(
        Recommendation(user_id=user.id, dish_id=dish.id, score=0.9, action=None)
    )
    db.session.commit()

    assert len(user.ratings) == 1
    assert user.ratings[0].value == 4.5
    assert len(user.recommendations) == 1
