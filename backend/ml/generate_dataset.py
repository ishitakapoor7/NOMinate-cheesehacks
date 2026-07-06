import requests
import csv
import string
import time
import random
import numpy as np

CUISINES = [
    "American", "British", "Canadian", "Chinese", "Croatian", "Dutch",
    "Egyptian", "Filipino", "French", "Greek", "Indian", "Irish",
    "Italian", "Jamaican", "Japanese", "Kenyan", "Malaysian", "Mexican",
    "Moroccan", "Polish", "Portuguese", "Russian", "Spanish", "Thai",
    "Tunisian", "Turkish", "Ukrainian", "Vietnamese"
]

SKILLS = ["beginner", "intermediate", "advanced"]
HEALTH_GOALS = ["weight_loss", "maintain", "weight_gain"]
BUDGETS = ["<$50", "$50-$100", "$100-$200", "$200+"]
DIETARY_OPTIONS = ["vegetarian", "vegan", "dairy-free", "pescatarian"]


def fetch_all_dishes():
    """
    Hit TheMealDB API for each letter a-z to get their full dish catalog.
    Returns a list of raw meal objects.
    """
    all_meals = []
    base_url = "https://www.themealdb.com/api/json/v1/1/search.php?f="

    for letter in string.ascii_lowercase:
        response = requests.get(base_url + letter)
        data = response.json()

        if data["meals"]: 
            all_meals.extend(data["meals"])

        time.sleep(0.5)

    print(f"Fetched {len(all_meals)} dishes total")
    return all_meals

def extract_ingredients(meal):
    """
    TheMealDB stores ingredients in strIngredient1 through strIngredient20.
    Collect all non-empty ones into a list.
    """
    ingredients = []
    for i in range(1, 21):
        ing = meal.get(f"strIngredient{i}")
        if ing and ing.strip():  # skip None and empty strings
            ingredients.append(ing.strip().lower())
    return ingredients


def classify_difficulty(ingredients, instructions):
    """
    Simple heuristic: fewer ingredients + shorter instructions = easier.
    """
    num_ingredients = len(ingredients)
    num_steps = len([s for s in instructions.split("\n") if s.strip()])

    if num_ingredients <= 5 and num_steps <= 4:
        return "beginner"
    elif num_ingredients <= 10 or num_steps <= 8:
        return "intermediate"
    else:
        return "advanced"


def classify_calorie_tier(category, ingredients):
    """
    Rough heuristic based on meal category and ingredient types.
    """
    low_cal_categories = {"vegan", "vegetarian", "side"}
    high_cal_categories = {"dessert", "pasta"}

    cat_lower = category.lower()
    if cat_lower in low_cal_categories:
        return "low"
    elif cat_lower in high_cal_categories:
        return "high"
    else:
        return "medium"


def classify_cost_tier(ingredients):
    """
    Check for expensive vs cheap ingredients.
    """
    expensive_keywords = [
        "salmon", "prawn", "shrimp", "lobster", "crab", "steak",
        "lamb", "duck", "saffron", "truffle", "fillet"
    ]
    cheap_keywords = [
        "rice", "beans", "lentils", "potato", "bread", "egg",
        "pasta", "flour", "oats", "cabbage", "onion"
    ]

    ing_text = " ".join(ingredients)
    has_expensive = any(kw in ing_text for kw in expensive_keywords)
    has_cheap = any(kw in ing_text for kw in cheap_keywords)

    if has_expensive:
        return "expensive"
    elif has_cheap and not has_expensive:
        return "cheap"
    else:
        return "moderate"


def classify_dietary_tags(category, ingredients):
    """
    Infer dietary tags from the category and ingredient list.
    """
    tags = []
    ing_text = " ".join(ingredients)
    cat_lower = category.lower()

    meat_keywords = [
        "chicken", "beef", "pork", "lamb", "duck", "turkey",
        "bacon", "sausage", "mince", "steak"
    ]
    seafood_keywords = [
        "salmon", "tuna", "cod", "prawn", "shrimp", "fish",
        "lobster", "crab", "anchov"
    ]
    dairy_keywords = [
        "milk", "cheese", "cream", "butter", "yogurt", "yoghurt"
    ]

    has_meat = any(kw in ing_text for kw in meat_keywords)
    has_fish = any(kw in ing_text for kw in seafood_keywords)
    has_dairy = any(kw in ing_text for kw in dairy_keywords)

    if cat_lower == "vegan" or (not has_meat and not has_fish and not has_dairy):
        tags.append("vegan")
    if cat_lower == "vegetarian" or (not has_meat and not has_fish):
        tags.append("vegetarian")
    if not has_dairy:
        tags.append("dairy-free")
    if not has_fish and not has_meat:
        tags.append("pescatarian")
    elif has_fish and not has_meat:
        tags.append("pescatarian")

    return tags

def build_dish_catalog():
    """
    Fetch all dishes, classify them, write to ml/data/dishes.csv
    """
    meals = fetch_all_dishes()

    rows = []
    for i, meal in enumerate(meals):
        ingredients = extract_ingredients(meal)
        instructions = meal.get("strInstructions", "")
        category = meal.get("strCategory", "")
        cuisine = meal.get("strArea", "Unknown")

        row = {
            "dish_id": i,
            "dish_name": meal["strMeal"],
            "cuisine": cuisine,
            "category": category,
            "dietary_tags": "|".join(classify_dietary_tags(category, ingredients)),
            "difficulty": classify_difficulty(ingredients, instructions),
            "calorie_tier": classify_calorie_tier(category, ingredients),
            "cost_tier": classify_cost_tier(ingredients),
            "ingredients": "|".join(ingredients),
        }
        rows.append(row)

    fieldnames = [
        "dish_id", "dish_name", "cuisine", "category",
        "dietary_tags", "difficulty", "calorie_tier",
        "cost_tier", "ingredients"
    ]
    with open("ml/data/dishes.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} dishes to ml/data/dishes.csv")
    return rows

import random
import numpy as np


CUISINES = [
    "American", "British", "Canadian", "Chinese", "Croatian", "Dutch",
    "Egyptian", "Filipino", "French", "Greek", "Indian", "Irish",
    "Italian", "Jamaican", "Japanese", "Kenyan", "Malaysian", "Mexican",
    "Moroccan", "Polish", "Portuguese", "Russian", "Spanish", "Thai",
    "Tunisian", "Turkish", "Ukrainian", "Vietnamese"
]

SKILLS = ["beginner", "intermediate", "advanced"]
HEALTH_GOALS = ["weight_loss", "maintain", "weight_gain"]
BUDGETS = ["<$50", "$50-$100", "$100-$200", "$200+"]
DIETARY_OPTIONS = ["vegetarian", "vegan", "dairy-free", "pescatarian"]


def generate_users(num_users=500):
    """
    Generate synthetic user profiles with random but realistic preferences.
    """
    users = []
    for user_id in range(num_users):
        preferred_cuisines = random.sample(CUISINES, 5)
        skill = random.choice(SKILLS)
        goal = random.choice(HEALTH_GOALS)
        budget = random.choice(BUDGETS)

        if random.random() < 0.6:
            restrictions = []
        else:
            restrictions = random.sample(DIETARY_OPTIONS, k=random.randint(1, 2))

        users.append({
            "user_id": user_id,
            "preferred_cuisines": "|".join(preferred_cuisines),
            "skill": skill,
            "health_goal": goal,
            "budget": budget,
            "dietary_restrictions": "|".join(restrictions),
        })

    fieldnames = [
        "user_id", "preferred_cuisines", "skill",
        "health_goal", "budget", "dietary_restrictions"
    ]
    with open("ml/data/users.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users)

    print(f"Wrote {len(users)} users to ml/data/users.csv")
    return users

def compute_rating(user, dish):
    """
    Compute a synthetic rating (1-5) based on how well a dish
    matches a user's preferences. This formula is what teaches
    the model what "good" recommendations look like.
    """
    score = 2.5  # start neutral

    # Cuisine match: higher bonus for higher-ranked preferences
    user_cuisines = user["preferred_cuisines"].split("|")
    dish_cuisine = dish["cuisine"]
    if dish_cuisine in user_cuisines:
        rank = user_cuisines.index(dish_cuisine)
        # rank 0 (top choice) = +1.5, rank 4 = +0.3
        score += 1.5 - (rank * 0.3)

    # Skill match: penalize dishes too hard for the user
    skill_levels = {"beginner": 0, "intermediate": 1, "advanced": 2}
    user_skill = skill_levels[user["skill"]]
    dish_skill = skill_levels[dish["difficulty"]]
    if dish_skill > user_skill:
        score -= 1.0  # too hard
    elif dish_skill == user_skill:
        score += 0.3  # good match

    # Dietary restriction violations: heavy penalty
    user_restrictions = user["dietary_restrictions"].split("|") if user["dietary_restrictions"] else []
    dish_tags = dish["dietary_tags"].split("|") if dish["dietary_tags"] else []
    for restriction in user_restrictions:
        if restriction and restriction not in dish_tags:
            score -= 2.0 

    goal_calorie_map = {
        "weight_loss": "low",
        "maintain": "medium",
        "weight_gain": "high",
    }
    preferred_calorie = goal_calorie_map[user["health_goal"]]
    if dish["calorie_tier"] == preferred_calorie:
        score += 0.5

    budget_cost_map = {
        "<$50": "cheap",
        "$50-$100": "moderate",
        "$100-$200": "moderate",
        "$200+": "expensive",
    }
    preferred_cost = budget_cost_map[user["budget"]]
    if dish["cost_tier"] == preferred_cost:
        score += 0.5
    elif dish["cost_tier"] == "expensive" and user["budget"] == "<$50":
        score -= 0.5 

    score = np.clip(score, 1.0, 5.0)
    score += np.random.normal(0, 0.3) 
    score = np.clip(score, 1.0, 5.0)

    return round(score, 2)

def generate_ratings(users, dishes, sparsity=0.3):
    """
    For each user, only rate ~30% of dishes (randomly selected).
    The sparsity is what makes collaborative filtering meaningful —
    the model learns to predict the missing ratings.
    """
    ratings = []

    for user in users:
        num_to_rate = int(len(dishes) * sparsity)
        dishes_to_rate = random.sample(dishes, num_to_rate)

        for dish in dishes_to_rate:
            rating = compute_rating(user, dish)
            ratings.append({
                "user_id": user["user_id"],
                "dish_id": dish["dish_id"],
                "rating": rating,
            })

    with open("ml/data/ratings.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "dish_id", "rating"])
        writer.writeheader()
        writer.writerows(ratings)

    print(f"Wrote {len(ratings)} ratings to ml/data/ratings.csv")
    return ratings



if __name__ == "__main__":
    dishes = build_dish_catalog()
    users = generate_users(500)
    ratings = generate_ratings(users, dishes, sparsity=0.3)
