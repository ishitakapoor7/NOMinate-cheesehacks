from app.models import Dish
from seed import seed_dishes


def test_seed_is_idempotent(db):
    count_first = seed_dishes()
    assert count_first > 0
    assert Dish.query.count() == count_first

    # Running again must not create duplicates.
    seed_dishes()
    assert Dish.query.count() == count_first

    # Spot-check that dishes load with their fields (ids are assigned by the
    # catalog build, so don't assume a specific one).
    dish = Dish.query.order_by(Dish.id).first()
    assert dish is not None
    assert dish.dish_name
    assert dish.cuisine
