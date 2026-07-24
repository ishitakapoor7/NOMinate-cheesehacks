"""Deepen underserved cuisines in the dish catalog using the Spoonacular API.

TheMealDB (the original catalog source) is capped — it only has ~8 Greek, ~6
Mexican dishes and no more. Spoonacular has real per-cuisine depth, so this
script pulls extra dishes for the thin cuisines, normalizes them into the same
dish schema, appends them to ml/data/dishes.csv, then regenerates the synthetic
ratings over the expanded catalog so a retrain can learn embeddings for the new
dishes.

Only cuisines that exist in Spoonacular's own cuisine taxonomy can be seeded
this way; cuisines like Filipino or Portuguese aren't offered there.

Usage (from backend/):
    ../venv/bin/python -m ml.expand_catalog

Idempotent: dishes already present (by normalized name) are skipped, so it can
be re-run — e.g. to resume the next day if the daily API quota runs out.
"""
import csv
import os
import random
import re

import numpy as np
import requests
from dotenv import load_dotenv

from ml.generate_dataset import compute_rating

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISHES_CSV = os.path.join(BASE, "ml", "data", "dishes.csv")
USERS_CSV = os.path.join(BASE, "ml", "data", "users.csv")
RATINGS_CSV = os.path.join(BASE, "ml", "data", "ratings.csv")

SEARCH_URL = "https://api.spoonacular.com/recipes/complexSearch"

# Cuisines that are thin in our catalog AND exist in Spoonacular's taxonomy.
# (cuisine name -> how many dishes to try to add)
TARGET_CUISINES = {
    "Mexican": 25,
    "Indian": 25,
    "Japanese": 25,
    "Greek": 20,
    "Irish": 20,
}

DISH_FIELDS = [
    "dish_id", "dish_name", "cuisine", "category",
    "dietary_tags", "difficulty", "calorie_tier", "cost_tier", "ingredients",
]


def clean_title(title: str) -> str:
    """Spoonacular titles are marketing-y ('Greek Fish: Fresh & Easy'). Keep the
    dish, drop the tagline, so it reads well on the recommendation letterboard."""
    head = re.split(r"[:\-–—(]", title, maxsplit=1)[0]
    head = re.sub(r"\s+", " ", head).strip(" .,")
    return head or title.strip()


def map_dish(result: dict, cuisine: str, dish_id: int) -> dict:
    diets = set(result.get("diets") or [])
    tags = []
    if result.get("vegan"):
        tags.append("vegan")
    if result.get("vegetarian"):
        tags.append("vegetarian")
    if result.get("dairyFree"):
        tags.append("dairy-free")
    if "pescatarian" in diets:
        tags.append("pescatarian")

    ingredients = []
    seen = set()
    for ing in result.get("extendedIngredients") or []:
        name = (ing.get("nameClean") or ing.get("name") or "").strip().lower()
        if name and name not in seen:
            seen.add(name)
            ingredients.append(name)

    n_ing = len(ingredients)
    ready = result.get("readyInMinutes") or 30
    if n_ing <= 6 and ready <= 30:
        difficulty = "beginner"
    elif n_ing <= 12 or ready <= 60:
        difficulty = "intermediate"
    else:
        difficulty = "advanced"

    dish_types = set(result.get("dishTypes") or [])
    if "dessert" in dish_types:
        calorie_tier = "high"
    elif result.get("vegan") or result.get("vegetarian") or "salad" in dish_types:
        calorie_tier = "low"
    else:
        calorie_tier = "medium"

    pps = result.get("pricePerServing") or 0  # cents per serving
    if result.get("cheap") or (pps and pps < 180):
        cost_tier = "cheap"
    elif pps and pps > 400:
        cost_tier = "expensive"
    else:
        cost_tier = "moderate"

    category = next(iter(result.get("dishTypes") or []), "")

    return {
        "dish_id": dish_id,
        "dish_name": clean_title(result.get("title", "")),
        "cuisine": cuisine,
        "category": category,
        "dietary_tags": "|".join(tags),
        "difficulty": difficulty,
        "calorie_tier": calorie_tier,
        "cost_tier": cost_tier,
        "ingredients": "|".join(ingredients),
    }


def fetch_cuisine(cuisine: str, number: int, api_key: str) -> list[dict]:
    resp = requests.get(
        SEARCH_URL,
        params={
            "cuisine": cuisine,
            "number": number,
            "addRecipeInformation": "true",
            "fillIngredients": "true",
            "instructionsRequired": "true",
            "sort": "popularity",
            "apiKey": api_key,
        },
        timeout=20,
    )
    resp.raise_for_status()
    cost = resp.headers.get("X-API-Quota-Request", "?")
    left = resp.headers.get("X-API-Quota-Left", "?")
    results = resp.json().get("results", [])
    print(f"  {cuisine}: fetched {len(results)} (cost {cost} pts, {left} left)")
    return results


def expand_catalog() -> int:
    load_dotenv(os.path.join(BASE, ".env"))
    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key:
        raise SystemExit("SPOONACULAR_API_KEY not set in backend/.env")

    with open(DISHES_CSV, newline="") as f:
        dishes = list(csv.DictReader(f))
    existing_names = {d["dish_name"].strip().lower() for d in dishes}
    next_id = max(int(d["dish_id"]) for d in dishes) + 1

    added = 0
    for cuisine, want in TARGET_CUISINES.items():
        try:
            results = fetch_cuisine(cuisine, want, api_key)
        except requests.RequestException as exc:
            print(f"  {cuisine}: request failed ({exc}); stopping so quota isn't wasted")
            break
        for result in results:
            name = clean_title(result.get("title", "")).lower()
            if not name or name in existing_names:
                continue
            row = map_dish(result, cuisine, next_id)
            if not row["ingredients"]:
                continue  # a dish with no ingredients is useless to the model
            dishes.append(row)
            existing_names.add(name)
            next_id += 1
            added += 1

    with open(DISHES_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DISH_FIELDS)
        writer.writeheader()
        writer.writerows(dishes)
    print(f"Catalog now {len(dishes)} dishes ({added} new).")
    return added


def regenerate_ratings(sparsity: float = 0.3, seed: int = 42) -> int:
    """Rebuild ratings.csv over the (expanded) catalog with the same synthetic
    users, so every dish — new and old — has training signal. Deterministic."""
    random.seed(seed)
    np.random.seed(seed)

    with open(DISHES_CSV, newline="") as f:
        dishes = list(csv.DictReader(f))
    with open(USERS_CSV, newline="") as f:
        users = list(csv.DictReader(f))

    num_to_rate = int(len(dishes) * sparsity)
    ratings = []
    for user in users:
        for dish in random.sample(dishes, num_to_rate):
            ratings.append(
                {
                    "user_id": user["user_id"],
                    "dish_id": dish["dish_id"],
                    "rating": compute_rating(user, dish),
                }
            )

    with open(RATINGS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "dish_id", "rating"])
        writer.writeheader()
        writer.writerows(ratings)
    print(f"Wrote {len(ratings)} ratings over {len(dishes)} dishes.")
    return len(ratings)


if __name__ == "__main__":
    added = expand_catalog()
    if added:
        regenerate_ratings()
    else:
        print("No new dishes added; leaving ratings.csv untouched.")
