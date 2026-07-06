from app.models import Dish
from seed import seed_dishes


def test_seed_is_idempotent(db):
    count_first = seed_dishes()
    assert count_first > 0
    assert Dish.query.count() == count_first

    # Running again must not create duplicates.
    seed_dishes()
    assert Dish.query.count() == count_first

    # Spot-check a known dish loaded with its fields.
    dish = db.session.get(Dish, 0)
    assert dish is not None
    assert dish.dish_name
