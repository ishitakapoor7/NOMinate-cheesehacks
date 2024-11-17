from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests from React frontend

# Ollama API configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"  # Ensure this model is available in your Ollama setup

# Mock database for user profiles and history
users = {}
recommendations = {
    "dishes": ["Pasta", "Salad", "Burger", "Sushi", "Pizza", "Tacos"],
}

# Endpoint to create or update user profiles
@app.route('/profile', methods=['POST'])
def create_or_update_profile():
    data = request.json
    user_id = data['user_id']
    users[user_id] = {
        "dietary_restrictions": data.get('dietary_restrictions', []),
        "preferences": data.get('preferences', []),
        "skill_level": data.get('skill_level', "beginner"),  # beginner, amateur, chef
        "weight_goal": data.get('weight_goal', "maintaining"),  # weight loss, maintaining, weight gain
        "history": [],
        "recently_eaten": {},
        "compatibility_scores": {dish: 1.0 for dish in recommendations["dishes"]}
    }
    return jsonify({"message": "Profile created/updated successfully"}), 201

# Endpoint to get meal recommendations
@app.route('/recommendation', methods=['GET'])
def get_recommendation():
    user_id = request.args.get('user_id')
    user = users.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Filter out recently eaten dishes
    filter_recently_eaten(user)
    eligible_dishes = [
        dish for dish in recommendations["dishes"]
        if dish not in user['recently_eaten']  # Exclude recently eaten
    ]

    # Apply compatibility score filtering
    scored_dishes = {
        dish: user['compatibility_scores'].get(dish, 1.0)
        for dish in eligible_dishes
    }
    # Select dish with the highest compatibility score
    recommended_dish = max(scored_dishes, key=scored_dishes.get, default="No suitable recommendations")

    return jsonify({"recommendation": recommended_dish}), 200

# Endpoint to handle user feedback
@app.route('/feedback', methods=['POST'])
def handle_feedback():
    data = request.json
    user_id = data['user_id']
    recommendation = data['recommendation']
    feedback_type = data['feedback_type']  # 'tick' or 'cross'
    feedback_reason = data.get('feedback_reason', '')

    user = users.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    if feedback_type == 'cross':
        if feedback_reason == "Recently Eaten":
            # Add dish to recently eaten with timestamp
            user['recently_eaten'][recommendation] = datetime.now()
        elif feedback_reason == "I just don't like it":
            # Adjust compatibility score for the dish
            current_score = user['compatibility_scores'].get(recommendation, 1.0)
            user['compatibility_scores'][recommendation] = max(0, current_score - 0.2)  # Reduce score by 0.2 each time
        elif feedback_reason == "Other":
            # Optionally log 'Other' feedback for analysis
            pass

    elif feedback_type == 'tick':
        choice = data.get('choice')  # 'home' or 'takeout'
        if choice == 'home':
            ingredients = get_ingredients(recommendation)
            return jsonify({"ingredients": ingredients}), 200
        elif choice == 'takeout':
            restaurant = get_restaurant_suggestion(recommendation)
            return jsonify({"restaurant": restaurant}), 200

    return jsonify({"message": "Feedback recorded"}), 200

# Function to filter out recently eaten dishes based on a time limit
def filter_recently_eaten(user):
    recent_limit = timedelta(days=3)  # Duration to avoid re-recommending recently eaten dishes
    now = datetime.now()
    user['recently_eaten'] = {
        dish: date for dish, date in user['recently_eaten'].items()
        if now - date <= recent_limit
    }

# Function to retrieve ingredients for a given dish
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

# Function to suggest a restaurant for a given dish near UW Madison
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
