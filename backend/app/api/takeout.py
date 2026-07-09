"""Takeout endpoint: restaurants serving the last recommended dish.

Still backed by the legacy Yelp scraper; Phase 5 swaps the internals for the
Google Places client behind services/places.py without changing this route's
contract. Ordering out is an implicit positive signal, so it's rated too.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from ml.yelp_scraper import scrape_yelp_restaurants

from app.api.recommend import latest_recommendation
from app.extensions import db
from app.models import Profile, Rating

bp = Blueprint("takeout", __name__, url_prefix="/api")

TAKEOUT_RATING = 4.0


@bp.route("/takeout", methods=["POST"])
@jwt_required()
def takeout():
    user_id = int(get_jwt_identity())
    rec = latest_recommendation(user_id)
    if not rec:
        return jsonify({"error": "No recommendation found"}), 404

    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"error": "No profile found"}), 404
    if not profile.location:
        return jsonify({"error": "No location set. Please update your profile."}), 400

    try:
        restaurants = scrape_yelp_restaurants(
            rec.dish.dish_name, profile.location, profile.budget
        )
    except Exception:
        restaurants = []

    rec.action = "takeout"
    db.session.add(
        Rating(user_id=user_id, dish_id=rec.dish_id, value=TAKEOUT_RATING, source="takeout")
    )
    db.session.commit()

    return jsonify({"restaurants": restaurants}), 200
