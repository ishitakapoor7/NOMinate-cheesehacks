"""Spoonacular-backed recipes, fetched once per dish and cached in the DB.

The dish catalog is finite, so every dish costs at most one API call ever.
A cached row with no steps is a recorded miss (Spoonacular doesn't know the
dish) and is never re-fetched automatically.
"""
import requests
from flask import current_app

from app.extensions import db
from app.models import Dish, Recipe

SEARCH_URL = "https://api.spoonacular.com/recipes/complexSearch"
TIMEOUT = 10


def _parse_result(result: dict) -> dict:
    ingredients = [
        {
            "name": (ing.get("nameClean") or ing.get("name") or "").strip(),
            "amount": (ing.get("original") or "").strip(),
        }
        for ing in result.get("extendedIngredients", [])
        if (ing.get("nameClean") or ing.get("name") or "").strip()
    ]
    steps = []
    for block in result.get("analyzedInstructions") or []:
        for step in block.get("steps", []):
            text = (step.get("step") or "").strip()
            if text:
                steps.append(text)
    return {
        "title": result.get("title") or "",
        "image_url": result.get("image") or "",
        "servings": result.get("servings"),
        "ready_minutes": result.get("readyInMinutes"),
        "prep_minutes": result.get("preparationMinutes"),
        "cook_minutes": result.get("cookingMinutes"),
        "source_name": result.get("sourceName") or "",
        "source_url": result.get("sourceUrl") or "",
        "ingredients": ingredients,
        "steps": steps,
    }


def get_recipe_for_dish(dish: Dish) -> Recipe | None:
    """The dish's cached recipe, fetching from Spoonacular on first ask.

    Returns None when no recipe is available (no API key, API failure, or
    Spoonacular has never heard of the dish). Never raises.
    """
    cached = Recipe.query.filter_by(dish_id=dish.id).first()
    if cached:
        return cached if cached.found else None

    api_key = current_app.config["SPOONACULAR_API_KEY"]
    if not api_key:
        return None

    try:
        response = requests.get(
            SEARCH_URL,
            params={
                "query": dish.dish_name,
                "number": 1,
                "instructionsRequired": "true",
                "addRecipeInformation": "true",
                "fillIngredients": "true",
                "apiKey": api_key,
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:  # 402 = quota exhausted; retry another day
        return None

    results = (response.json() or {}).get("results") or []
    parsed = _parse_result(results[0]) if results else None

    if parsed and parsed["steps"]:
        recipe = Recipe(dish_id=dish.id, **parsed)
    else:
        # Definitive "not found" — cache the miss so quota isn't spent again.
        recipe = Recipe(dish_id=dish.id)
    db.session.add(recipe)
    db.session.commit()
    return recipe if recipe.found else None


def recipe_payload(recipe: Recipe) -> dict:
    return {
        "title": recipe.title,
        "image_url": recipe.image_url,
        "servings": recipe.servings,
        "ready_minutes": recipe.ready_minutes,
        "prep_minutes": recipe.prep_minutes,
        "cook_minutes": recipe.cook_minutes,
        "source_name": recipe.source_name,
        "source_url": recipe.source_url,
        "steps": recipe.steps,
    }
