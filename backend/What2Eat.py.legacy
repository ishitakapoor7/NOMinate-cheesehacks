from flask import Flask, request, jsonify, session
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json
import sys
from dotenv import load_dotenv

load_dotenv()

# Add the ml/ directory to the path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ml"))
from recommender import RecommendationEngine
from yelp_scraper import scrape_yelp_restaurants

# ── App setup ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-me")
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}}, supports_credentials=True)

# ── Load the ML model (once at startup, not on every request) ─────────────────

BASE = os.path.dirname(__file__)
engine = RecommendationEngine(
    model_path    = os.path.join(BASE, "ml", "checkpoints", "model.pt"),
    encoders_path = os.path.join(BASE, "ml", "checkpoints", "encoders.pkl"),
    dishes_path   = os.path.join(BASE, "ml", "checkpoints", "dishes.pkl"),
    users_path    = os.path.join(BASE, "ml", "checkpoints", "users.pkl"),
)

# ── In-memory stores ──────────────────────────────────────────────────────────
# These reset on server restart — good enough for a demo/portfolio project.

users    = {}   # email -> {username, password}
profiles = {}   # email -> profile dict (for feedback persistence)


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "NOMinate API is running."}), 200


@app.route("/signup", methods=["POST"])
def register():
    data     = request.json
    username = data.get("username")
    email    = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if email in users:
        return jsonify({"error": "User already exists"}), 409

    users[email] = {
        "username": username,
        "password": generate_password_hash(password, method="pbkdf2:sha256"),
    }
    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data     = request.json
    email    = data.get("email")
    password = data.get("password")

    user = users.get(email)
    if user and check_password_hash(user["password"], password):
        session["user"] = email
        return jsonify({"message": "Login successful", "username": user["username"]}), 200
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# ── Profile setup ─────────────────────────────────────────────────────────────

@app.route("/profilesetup", methods=["POST"])
def create_or_update_profile():
    data = request.json

    profile = {
        "cuisines":              data.get("cuisines", []),
        "dietary_restrictions":  data.get("dietaryRestrictions", []),
        "allergies":             data.get("allergies", ""),
        "skill_level":           data.get("cookingSkill", "beginner"),
        "weight_goal":           data.get("healthGoal", "maintain"),
        "budget":                data.get("budget", "<$50"),
        "location":              data.get("location", ""),
        "available_ingredients": data.get("availableIngredients", []),
    }

    session["profile"] = profile

    # Also persist in the profiles dict so feedback endpoint can access it
    email = session.get("user")
    if email:
        profiles[email] = profile

    return jsonify({"message": "Profile created/updated successfully"}), 201


# ── Recommendation ────────────────────────────────────────────────────────────

@app.route("/generatedresponse", methods=["GET"])
def handle_generated_response():
    user_profile = session.get("profile")
    if not user_profile:
        return jsonify({"error": "No profile found. Please complete profile setup."}), 404

    # Dishes the user has already seen/disliked this session
    excluded = list(session.get("excluded_dishes", []))

    try:
        result = engine.recommend(
            user_profile          = user_profile,
            available_ingredients = user_profile.get("available_ingredients", []),
            excluded_dishes       = excluded,
        )
    except Exception as e:
        return jsonify({"error": f"Recommendation failed: {str(e)}"}), 500

    session["last_recommendation"] = result["dish_name"]
    return jsonify({
        "recommendation": result["dish_name"],
        "cuisine":        result["cuisine"],
        "score":          result["score"],
    }), 200


# ── Cooking route ─────────────────────────────────────────────────────────────

@app.route("/cooking", methods=["POST"])
def cooking():
    recommendation = session.get("last_recommendation")
    if not recommendation:
        return jsonify({"error": "No recommendation found"}), 404

    ingredients      = engine.get_ingredients(recommendation)
    user_ingredients = {
        ing.strip().lower()
        for ing in session.get("profile", {}).get("available_ingredients", [])
    }

    # Mark each ingredient as available or not based on what the user has at home
    ingredient_list = [
        {
            "name":      ing,
            "available": ing.lower() in user_ingredients,
        }
        for ing in ingredients
    ]

    return jsonify({"ingredients": ingredient_list}), 200


# ── Takeout route ─────────────────────────────────────────────────────────────

@app.route("/takeout", methods=["POST"])
def takeout():
    recommendation = session.get("last_recommendation")
    user_profile   = session.get("profile")

    if not recommendation:
        return jsonify({"error": "No recommendation found"}), 404
    if not user_profile:
        return jsonify({"error": "No profile found"}), 404

    location = user_profile.get("location", "")
    if not location:
        return jsonify({"error": "No location set. Please update your profile."}), 400

    budget      = user_profile.get("budget", "")
    restaurants = scrape_yelp_restaurants(recommendation, location, budget)

    return jsonify({"restaurants": restaurants}), 200


# ── Feedback ──────────────────────────────────────────────────────────────────

@app.route("/feedback", methods=["POST"])
def handle_feedback():
    data            = request.json
    feedback_reason = data.get("feedback_reason", "")
    recommendation  = session.get("last_recommendation")

    if not recommendation:
        return jsonify({"error": "No active recommendation"}), 404

    # Keep a session-level excluded list so the model won't re-recommend
    # dishes the user has flagged this session
    excluded = list(session.get("excluded_dishes", []))

    if feedback_reason == "Recently Eaten":
        if recommendation not in excluded:
            excluded.append(recommendation)

    elif feedback_reason == "I just don't like it":
        if recommendation not in excluded:
            excluded.append(recommendation)

    session["excluded_dishes"] = excluded

    # Persist feedback to a file for potential future retraining
    email = session.get("user", "anonymous")
    feedback_entry = {
        "user":           email,
        "dish":           recommendation,
        "reason":         feedback_reason,
        "timestamp":      datetime.now().isoformat(),
    }

    feedback_path = os.path.join(BASE, "ml", "data", "feedback_log.jsonl")
    with open(feedback_path, "a") as f:
        f.write(json.dumps(feedback_entry) + "\n")

    return jsonify({"message": "Feedback recorded"}), 200


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5001)
