import requests
import csv
import string
import time

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


if __name__ == "__main__":
    build_dish_catalog()
