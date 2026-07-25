"""Cache full recipes for the Spoonacular-seeded dishes into a committed JSON.

The complexSearch response used to seed the catalog already contains full recipe
data (steps, ingredient amounts, times). This script re-runs those per-cuisine
searches, matches results back to catalog dish ids, and writes the recipes to
ml/data/recipes_seed.json. seed.py loads that into the recipes table on deploy,
so the app can show real recipes for these dishes without spending live API
quota at cook time.

Usage (from backend/):
    ../venv/bin/python -m ml.seed_recipes
"""
import csv
import json
import os

import requests
from dotenv import load_dotenv

from app.services.recipes import _parse_result
from ml.expand_catalog import BASE, DISHES_CSV, SEARCH_URL, TARGET_CUISINES, clean_title

RECIPES_JSON = os.path.join(BASE, "ml", "data", "recipes_seed.json")


def main() -> int:
    load_dotenv(os.path.join(BASE, ".env"))
    api_key = os.getenv("SPOONACULAR_API_KEY")
    if not api_key:
        raise SystemExit("SPOONACULAR_API_KEY not set in backend/.env")

    with open(DISHES_CSV, newline="") as f:
        name_to_id = {
            row["dish_name"].strip().lower(): int(row["dish_id"])
            for row in csv.DictReader(f)
        }

    recipes = []
    seen_ids = set()
    for cuisine, number in TARGET_CUISINES.items():
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
        left = resp.headers.get("X-API-Quota-Left", "?")
        got = 0
        for result in resp.json().get("results", []):
            dish_id = name_to_id.get(clean_title(result.get("title", "")).lower())
            if dish_id is None or dish_id in seen_ids:
                continue
            parsed = _parse_result(result)
            if not parsed["steps"]:
                continue
            recipes.append({"dish_id": dish_id, **parsed})
            seen_ids.add(dish_id)
            got += 1
        print(f"  {cuisine}: {got} recipes ({left} quota left)")

    with open(RECIPES_JSON, "w") as f:
        json.dump(recipes, f, indent=2)
    print(f"Wrote {len(recipes)} recipes to {RECIPES_JSON}")
    return len(recipes)


if __name__ == "__main__":
    main()
