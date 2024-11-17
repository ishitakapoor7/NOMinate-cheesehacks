from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# Mock databases for users and profiles
users = {}
profiles = {}

# Ollama API configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# Register endpoint
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if email in users:
        return jsonify({"error": "User already exists"}), 409

    users[email] = {
        "username": username,
        "password": generate_password_hash(password),
    }
    return jsonify({"message": "User registered successfully"}), 201

# Login endpoint
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = users.get(email)
    if user and check_password_hash(user["password"], password):
        return jsonify({"message": "Login successful"}), 200
    return jsonify({"error": "Invalid credentials"}), 401

# Profile setup/update endpoint
@app.route('/profile', methods=['POST'])
def create_or_update_profile():
    data = request.json
    user_id = data.get('user_id')
    
    profiles[user_id] = {
        "dietary_restrictions": data.get('dietary_restrictions', []),
        "preferences": data.get('preferences', []),
        "skill_level": data.get('skill_level', "beginner"),
        "weight_goal": data.get('weight_goal', "maintaining"),
        "history": [],
        "recently_eaten": {},
        "compatibility_scores": {dish: 1.0 for dish in ["Pasta", "Salad", "Burger", "Sushi", "Pizza", "Tacos"]}
    }
    return jsonify({"message": "Profile created/updated successfully"}), 201

# Recommendation endpoint
@app.route('/recommendation', methods=['GET'])
def get_recommendation():
    user_id = request.args.get('user_id')
    user_profile = profiles.get(user_id)

    if not user_profile:
        return jsonify({"error": "User not found"}), 404

    filter_recently_eaten(user_profile)
    eligible_dishes = [
        dish for dish in ["Pasta", "Salad", "Burger", "Sushi", "Pizza", "Tacos"]
        if dish not in user_profile['recently_eaten']
    ]

    scored_dishes = {
        dish: user_profile['compatibility_scores'].get(dish, 1.0)
        for dish in eligible_dishes
    }
    recommended_dish = max(scored_dishes, key=scored_dishes.get, default="No suitable recommendations")
    return jsonify({"recommendation": recommended_dish}), 200

# Feedback endpoint
@app.route('/feedback', methods=['POST'])
def handle_feedback():
    data = request.json
    user_id = data['user_id']
    recommendation = data['recommendation']
    feedback_type = data['feedback_type']
    feedback_reason = data.get('feedback_reason', '')

    user_profile = profiles.get(user_id)
    if not user_profile:
        return jsonify({"error": "User not found"}), 404

    if feedback_type == 'cross':
        if feedback_reason == "Recently Eaten":
            user_profile['recently_eaten'][recommendation] = datetime.now()
        elif feedback_reason == "I just don't like it":
            current_score = user_profile['compatibility_scores'].get(recommendation, 1.0)
            user_profile['compatibility_scores'][recommendation] = max(0, current_score - 0.2)
    elif feedback_type == 'tick':
        choice = data.get('choice')
        if choice == 'home':
            ingredients = get_ingredients(recommendation)
            return jsonify({"ingredients": ingredients}), 200
        elif choice == 'takeout':
            restaurant = get_restaurant_suggestion(recommendation)
            return jsonify({"restaurant": restaurant}), 200

    return jsonify({"message": "Feedback recorded"}), 200

def filter_recently_eaten(user_profile):
    recent_limit = timedelta(days=3)
    now = datetime.now()
    user_profile['recently_eaten'] = {
        dish: date for dish, date in user_profile['recently_eaten'].items()
        if now - date <= recent_limit
    }

def get_ingredients(dish):
    prompt = f"List the ingredients required to prepare {dish}."
    response = requests.post(
        OLLAMA_API_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt}
    )
    if response.status_code == 200:
        ingredients = response.json().get('response', '').strip()
        return ingredients.split('\n')
    else:
        return ["Failed to retrieve ingredients"]

def get_restaurant_suggestion(dish):
    prompt = (
        f"Find a highly rated restaurant near University of Wisconsin-Madison that serves {dish}. "
        "Include the restaurant's name, address, rating, and approximate distance from the university."
    )
    response = requests.post(
        OLLAMA_API_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt}
    )
    if response.status_code == 200:
        restaurant_info = response.json().get('response', '').strip()
        return {"details": restaurant_info}
    else:
        return {"error": "Failed to retrieve restaurant suggestion from Ollama"}

if __name__ == '__main__':
    app.run(debug=True)
