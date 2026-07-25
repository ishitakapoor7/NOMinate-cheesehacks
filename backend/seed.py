"""Seed the dish catalog into Postgres from ml/data/dishes.csv.

Idempotent: dishes are upserted by their CSV dish_id, so running it twice
won't create duplicates. Run with:

    flask --app wsgi shell  # (not needed)
    python seed.py
"""
import csv
import json
import os

from app import create_app
from app.extensions import db
from app.models import Dish, Recipe

BASE = os.path.dirname(__file__)
DISHES_CSV = os.path.join(BASE, "ml", "data", "dishes.csv")
RECIPES_JSON = os.path.join(BASE, "ml", "data", "recipes_seed.json")


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


def seed_recipes(json_path: str = RECIPES_JSON) -> int:
    """Upsert the pre-fetched recipes so the app can show them without hitting
    the recipe API at runtime. Idempotent by dish_id; skips dishes not loaded."""
    if not os.path.exists(json_path):
        return 0
    with open(json_path) as f:
        entries = json.load(f)

    count = 0
    for entry in entries:
        dish_id = entry["dish_id"]
        if db.session.get(Dish, dish_id) is None:
            continue
        recipe = Recipe.query.filter_by(dish_id=dish_id).first()
        if recipe is None:
            recipe = Recipe(dish_id=dish_id)
            db.session.add(recipe)
        recipe.title = entry.get("title", "")
        recipe.image_url = entry.get("image_url", "")
        recipe.servings = entry.get("servings")
        recipe.ready_minutes = entry.get("ready_minutes")
        recipe.prep_minutes = entry.get("prep_minutes")
        recipe.cook_minutes = entry.get("cook_minutes")
        recipe.source_name = entry.get("source_name", "")
        recipe.source_url = entry.get("source_url", "")
        recipe.ingredients = entry.get("ingredients", [])
        recipe.steps = entry.get("steps", [])
        count += 1

    db.session.commit()
    return count


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        dishes = seed_dishes()
        recipes = seed_recipes()
        print(f"Seeded {dishes} dishes and {recipes} recipes into the database.")
