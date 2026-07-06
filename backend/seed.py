"""Seed the dish catalog into Postgres from ml/data/dishes.csv.

Idempotent: dishes are upserted by their CSV dish_id, so running it twice
won't create duplicates. Run with:

    flask --app wsgi shell  # (not needed)
    python seed.py
"""
import csv
import os

from app import create_app
from app.extensions import db
from app.models import Dish

BASE = os.path.dirname(__file__)
DISHES_CSV = os.path.join(BASE, "ml", "data", "dishes.csv")


def seed_dishes(csv_path: str = DISHES_CSV) -> int:
    """Load/refresh dishes from the CSV. Returns the number of rows processed."""
    with open(csv_path, newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        dish_id = int(row["dish_id"])
        dish = db.session.get(Dish, dish_id)
        if dish is None:
            dish = Dish(id=dish_id)
            db.session.add(dish)

        dish.dish_name = row.get("dish_name", "")
        dish.cuisine = row.get("cuisine", "") or ""
        dish.category = row.get("category", "") or ""
        dish.dietary_tags = row.get("dietary_tags", "") or ""
        dish.difficulty = row.get("difficulty", "") or "beginner"
        dish.calorie_tier = row.get("calorie_tier", "") or "medium"
        dish.cost_tier = row.get("cost_tier", "") or "moderate"
        dish.ingredients = row.get("ingredients", "") or ""

    db.session.commit()
    return len(rows)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        count = seed_dishes()
        print(f"Seeded {count} dishes into the database.")
