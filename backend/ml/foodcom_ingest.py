"""Build NOMinate's catalog, recipes, ratings, and user profiles from the
Food.com dataset (Kaggle: shuyangli94/food-com-recipes-and-user-interactions).

Replaces the old synthetic ratings + TheMealDB/Spoonacular catalog with real
recipes and real user ratings. Produces, in ml/data/:
  - dishes.csv          the dish catalog (dinner mains only, curated per cuisine)
  - recipes_seed.json   real steps/ingredients for the cook screen (no live API)
  - ratings.csv         real user_id, dish_id, rating rows for training
  - users.csv           per-user preferred_cuisines derived from rating history

Design choices (per project decisions):
  - Keep only `main-dish` recipes with a recognizable cuisine tag, decent length,
    and enough real ratings — quality over the full 267K dump.
  - Dietary tags are derived from INGREDIENTS (not the source tags, which were
    unreliable), so they stay consistent with the recommender's diet filter.
  - Difficulty comes from the recipe's step count; budget/goal are handled
    elsewhere (takeout price / calorie tier), not as fake user attributes.

Usage (from backend/, with training extras installed):
    ../venv/bin/python -m ml.foodcom_ingest
"""
import ast
import csv
import json
import os
from collections import Counter, defaultdict

from ml.recommender import _DAIRY, _EGG, _FISH, _MEAT

csv.field_size_limit(10 ** 7)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "ml", "data", "foodcom")
RECIPES_CSV = os.path.join(SRC, "RAW_recipes.csv")
INTERACTIONS_CSV = os.path.join(SRC, "RAW_interactions.csv")

OUT = os.path.join(BASE, "ml", "data")
DISHES_OUT = os.path.join(OUT, "dishes.csv")
RECIPES_OUT = os.path.join(OUT, "recipes_seed.json")
RATINGS_OUT = os.path.join(OUT, "ratings.csv")
USERS_OUT = os.path.join(OUT, "users.csv")

# Dataset cuisine tag -> catalog cuisine name. Ordered by priority so a recipe
# tagged with several picks the most specific national cuisine first.
CUISINE_PRIORITY = [
    ("indian", "Indian"), ("thai", "Thai"), ("chinese", "Chinese"),
    ("japanese", "Japanese"), ("korean", "Korean"), ("vietnamese", "Vietnamese"),
    ("filipino", "Filipino"), ("malaysian", "Malaysian"), ("indonesian", "Indonesian"),
    ("mexican", "Mexican"), ("jamaican", "Jamaican"), ("cuban", "Caribbean"),
    ("italian", "Italian"), ("french", "French"), ("spanish", "Spanish"),
    ("greek", "Greek"), ("portuguese", "Portuguese"), ("turkish", "Turkish"),
    ("moroccan", "Moroccan"), ("lebanese", "Middle Eastern"),
    ("ethiopian", "Ethiopian"), ("german", "German"), ("irish", "Irish"),
    ("english", "British"), ("scottish", "British"), ("caribbean", "Caribbean"),
    ("middle-eastern", "Middle Eastern"), ("american", "American"),
]

# Curation thresholds
MIN_RATINGS_PER_DISH = 4    # a dish must have this many real ratings to qualify
MIN_AVG_RATING = 4.0        # ...and be well-liked on average
PER_CUISINE_CAP = 400       # cap per cuisine so no one cuisine dominates
MIN_INGREDIENTS, MAX_INGREDIENTS = 4, 20
MIN_STEPS = 3
MAX_MINUTES = 240
PER_DISH_RATING_CAP = 400   # bound ratings.csv size / popularity skew
MIN_USER_RATINGS = 4        # only train user embeddings for engaged users


def _cuisine_for(tags: set) -> str | None:
    for tag, name in CUISINE_PRIORITY:
        if tag in tags:
            return name
    return None


def _difficulty(n_steps: int) -> str:
    if n_steps <= 6:
        return "beginner"
    if n_steps <= 12:
        return "intermediate"
    return "advanced"


def _calorie_tier(nutrition: list) -> str:
    kcal = nutrition[0] if nutrition else 0
    if kcal < 300:
        return "low"
    if kcal <= 600:
        return "medium"
    return "high"


def _diet_tags(ingredient_words: set) -> str:
    """Derive dietary tags from ingredients — the reliable inverse of the
    recommender's diet filter."""
    tags = []
    has_meat = bool(_MEAT & ingredient_words)
    has_fish = bool(_FISH & ingredient_words)
    has_dairy = bool(_DAIRY & ingredient_words)
    has_egg = bool(_EGG & ingredient_words)
    if not has_meat and not has_fish:
        tags.append("vegetarian")
        if not has_dairy and not has_egg:
            tags.append("vegan")
    if not has_meat:  # fish allowed
        tags.append("pescatarian")
    if not has_dairy:
        tags.append("dairy-free")
    return "|".join(tags)


def _title(name: str) -> str:
    return " ".join(w for w in (name or "").split()).strip().title()


def aggregate_ratings() -> dict:
    """First pass over interactions: rating count + sum per recipe."""
    stats = defaultdict(lambda: [0, 0.0])  # recipe_id -> [count, sum]
    with open(INTERACTIONS_CSV) as f:
        for row in csv.DictReader(f):
            try:
                rid = int(row["recipe_id"])
                rating = float(row["rating"])
            except (ValueError, KeyError):
                continue
            s = stats[rid]
            s[0] += 1
            s[1] += rating
    return stats


def select_recipes(stats: dict) -> dict:
    """Filter + curate recipes; returns {recipe_id: dish_meta} with new dish_ids."""
    by_cuisine = defaultdict(list)
    with open(RECIPES_CSV) as f:
        for row in csv.DictReader(f):
            try:
                rid = int(row["id"])
                tags = set(ast.literal_eval(row["tags"]))
                ingredients = [i.strip().lower() for i in ast.literal_eval(row["ingredients"])]
                steps = ast.literal_eval(row["steps"])
                nutrition = ast.literal_eval(row["nutrition"])
                minutes = int(row["minutes"])
                n_steps = int(row["n_steps"])
            except (ValueError, SyntaxError, KeyError):
                continue

            if "main-dish" not in tags:
                continue
            cuisine = _cuisine_for(tags)
            if cuisine is None:
                continue
            if not (MIN_INGREDIENTS <= len(ingredients) <= MAX_INGREDIENTS):
                continue
            if n_steps < MIN_STEPS or not (0 < minutes <= MAX_MINUTES):
                continue
            count, total = stats.get(rid, (0, 0.0))
            if count < MIN_RATINGS_PER_DISH:
                continue
            avg = total / count
            if avg < MIN_AVG_RATING:
                continue

            words = {w for ing in ingredients for w in ing.split()}
            by_cuisine[cuisine].append({
                "recipe_id": rid,
                "dish_name": _title(row["name"]),
                "cuisine": cuisine,
                "category": "main-dish",
                "dietary_tags": _diet_tags(words),
                "difficulty": _difficulty(n_steps),
                "calorie_tier": _calorie_tier(nutrition),
                "cost_tier": "moderate",
                "ingredients": "|".join(ingredients),
                "steps": [s for s in steps if s and s.strip()],
                "minutes": minutes,
                "rating_count": count,
                "avg_rating": round(avg, 3),
            })

    kept = {}
    dish_id = 1
    for cuisine, dishes in sorted(by_cuisine.items()):
        dishes.sort(key=lambda d: d["rating_count"], reverse=True)
        for d in dishes[:PER_CUISINE_CAP]:
            d["dish_id"] = dish_id
            kept[d["recipe_id"]] = d
            dish_id += 1
    return kept


def write_catalog(kept: dict) -> None:
    cols = ["dish_id", "dish_name", "cuisine", "category", "dietary_tags",
            "difficulty", "calorie_tier", "cost_tier", "ingredients"]
    with open(DISHES_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for d in sorted(kept.values(), key=lambda d: d["dish_id"]):
            w.writerow({c: d[c] for c in cols})

    recipes = []
    for d in sorted(kept.values(), key=lambda d: d["dish_id"]):
        recipes.append({
            "dish_id": d["dish_id"],
            "title": d["dish_name"],
            "image_url": "",
            "servings": None,
            "ready_minutes": d["minutes"],
            "prep_minutes": None,
            "cook_minutes": None,
            "source_name": "Food.com",
            "source_url": f"https://www.food.com/recipe/{d['recipe_id']}",
            "ingredients": [{"name": ing, "amount": ""} for ing in d["ingredients"].split("|")],
            "steps": d["steps"],
        })
    with open(RECIPES_OUT, "w") as f:
        json.dump(recipes, f)


def write_ratings_and_users(kept: dict) -> tuple[int, int]:
    """Second pass over interactions: emit real ratings for kept dishes (for
    engaged users) and derive each user's preferred cuisines from what they
    rated highly."""
    id_map = {rid: d["dish_id"] for rid, d in kept.items()}
    cuisine_of = {d["dish_id"]: d["cuisine"] for d in kept.values()}

    user_rows = defaultdict(list)     # user_id -> [(dish_id, rating), ...]
    user_cuisine_votes = defaultdict(Counter)
    per_dish = Counter()

    with open(INTERACTIONS_CSV) as f:
        for row in csv.DictReader(f):
            try:
                rid = int(row["recipe_id"])
                if rid not in id_map:
                    continue
                uid = int(row["user_id"])
                rating = float(row["rating"])
            except (ValueError, KeyError):
                continue
            dish_id = id_map[rid]
            if per_dish[dish_id] >= PER_DISH_RATING_CAP:
                continue
            per_dish[dish_id] += 1
            user_rows[uid].append((dish_id, rating))
            if rating >= 4.0:
                user_cuisine_votes[uid][cuisine_of[dish_id]] += 1

    # Keep only engaged users so embeddings are meaningful.
    users = {u: rows for u, rows in user_rows.items() if len(rows) >= MIN_USER_RATINGS}

    with open(RATINGS_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "dish_id", "rating"])
        n = 0
        for uid, rows in users.items():
            for dish_id, rating in rows:
                w.writerow([uid, dish_id, rating])
                n += 1

    with open(USERS_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "preferred_cuisines"])
        for uid in users:
            ranked = [c for c, _ in user_cuisine_votes[uid].most_common(5)]
            w.writerow([uid, "|".join(ranked)])

    return len(users), n


def main() -> None:
    print("Pass 1/2: aggregating ratings…")
    stats = aggregate_ratings()
    print(f"  {len(stats):,} recipes have ratings")

    print("Selecting + curating recipes…")
    kept = select_recipes(stats)
    by_c = Counter(d["cuisine"] for d in kept.values())
    print(f"  kept {len(kept):,} dishes across {len(by_c)} cuisines:")
    for c, n in by_c.most_common():
        print(f"    {c:16}{n}")
    write_catalog(kept)

    print("Pass 2/2: emitting ratings + user profiles…")
    n_users, n_ratings = write_ratings_and_users(kept)
    print(f"  {n_users:,} users, {n_ratings:,} ratings")
    print(f"\nWrote:\n  {DISHES_OUT}\n  {RECIPES_OUT}\n  {RATINGS_OUT}\n  {USERS_OUT}")


if __name__ == "__main__":
    main()
